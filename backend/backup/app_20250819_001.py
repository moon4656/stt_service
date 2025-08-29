import os
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv
import uvicorn
import time
import traceback
import sys
import json
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from auth import (
    TokenManager, 
    create_user, 
    get_user, 
    verify_token, 
    verify_api_key_dependency,
    create_access_token,
    authenticate_user
)
from database import get_db, create_tables, test_connection, TranscriptionRequest, TranscriptionResponse, APIUsageLog, LoginLog, APIToken
from db_service import TranscriptionService, APIUsageService
from openai_service import OpenAIService
from stt_manager import STTManager
from audio_utils import get_audio_duration, format_duration
from file_storage import save_uploaded_file, get_stored_file_path, file_storage_manager

# 환경 변수 로드
load_dotenv()

# 로깅 설정
def setup_logging():
    """로깅 설정을 구성합니다."""
    # logs 디렉토리 생성
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        print(f"Created logs directory: {log_dir}")
    
    # 로거 생성
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 크기와 시간 기반 회전 핸들러 클래스 정의
    class SizeAndTimeRotatingHandler(TimedRotatingFileHandler):
        def __init__(self, *args, maxBytes=0, **kwargs):
            super().__init__(*args, **kwargs)
            self.maxBytes = maxBytes
            
        def shouldRollover(self, record):
            # 시간 기반 회전 체크
            if super().shouldRollover(record):
                return True
            # 크기 기반 회전 체크
            if self.maxBytes > 0:
                msg = "%s\n" % self.format(record)
                if hasattr(self.stream, 'tell'):
                    self.stream.seek(0, 2)  # 파일 끝으로 이동
                    if self.stream.tell() + len(msg.encode('utf-8')) >= self.maxBytes:
                        return True
            return False
    
    # 크기와 시간 기반 회전 핸들러 사용
    file_handler = SizeAndTimeRotatingHandler(
        filename=os.path.join(log_dir, "stt_service.log"),
        when='midnight',  # 자정마다 회전
        interval=1,       # 1일 간격
        backupCount=30,   # 30일치 보관
        maxBytes=10*1024*1024,  # 10MB
        encoding='utf-8'
    )
    file_handler.suffix = "%Y%m%d"  # 백업 파일명 형식: stt_service.log.20241210
    file_handler.setLevel(logging.INFO)
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # 테스트 로그 메시지 생성
    logger.info("🔧 로깅 시스템 초기화 완료 - 일단위/10MB 회전 설정")
    
    return logger

# 로깅 초기화
logger = setup_logging()

# OpenAI 서비스 초기화
openai_service = OpenAIService()

# STT 매니저 초기화 (여러 STT 서비스 관리)
stt_manager = STTManager()

# 애플리케이션 생명주기 관리
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작 및 종료 시 실행할 코드"""
    # 시작 시 실행
    try:
        logger.info("🚀 STT Service 시작 중...")
        # 데이터베이스 연결 테스트
        if test_connection():
            logger.info("✅ Database connection successful")
            print("✅ Database connection successful")
            # 테이블 생성
            create_tables()
            logger.info("✅ Database tables created/verified")
            print("✅ Database tables created/verified")
        else:
            logger.error("❌ Database connection failed - running without database logging")
            print("❌ Database connection failed - running without database logging")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
        print(f"❌ Database initialization error: {e}")
        print("⚠️  Running without database logging")
    
    yield  # 애플리케이션 실행
    
    # 종료 시 실행 (필요시)
    logger.info("🔄 Application shutting down")
    print("🔄 Application shutting down")

# FastAPI 앱 초기화
app = FastAPI(
    title="Speech-to-Text Service", 
    description="다중 STT 서비스(AssemblyAI, Daglo)를 지원하는 음성-텍스트 변환 서비스",
    lifespan=lifespan
)

# Pydantic 모델들
class UserCreate(BaseModel):
    user_id: str
    email: str
    name: str
    user_type: str  # "개인" 또는 "조직"
    phone_number: Optional[str] = None  # 전화번호 (선택사항)
    password: str  # 패스워드 (필수)

class TokenCreate(BaseModel):
    token_id: str
    description: Optional[str] = ""

class TokenRevoke(BaseModel):
    api_key_hash: str

class LoginRequest(BaseModel):
    user_id: str
    password: str

# 전역 예외 핸들러
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_msg = f"Request validation error: {str(exc)}"
    logger.error(error_msg)
    logger.error(f"Request URL: {request.url}")
    logger.error(f"Request method: {request.method}")
    print(f"Request validation error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={"detail": f"Request validation error: {str(exc)}"}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = f"Global exception handler caught: {type(exc).__name__}: {str(exc)}"
    logger.error(error_msg)
    logger.error(f"Traceback: {traceback.format_exc()}")
    print(f"Global exception handler caught: {type(exc).__name__}: {str(exc)}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_msg = f"Validation error on {request.method} {request.url}: {exc}"
    logger.warning(error_msg)
    print(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

@app.post("/transcribe/", summary="음성 파일을 텍스트로 변환")
async def transcribe_audio(
    request: Request, 
    file: UploadFile = File(...), 
    service: Optional[str] = None,
    fallback: bool = True,
    summarization: bool = False,
    # summary_model: str = "informative",
    # summary_type: str = "bullets",
    db: Session = Depends(get_db)
):
    """
    음성 파일을 업로드하여 텍스트로 변환합니다.
    다중 STT 서비스(AssemblyAI, Daglo)를 지원하며 폴백 기능을 제공합니다.
    요청과 응답 내역이 PostgreSQL에 저장됩니다.
    
    - **file**: 변환할 음성 파일
    - **service**: 사용할 STT 서비스 (assemblyai, daglo). 미지정시 기본 서비스 사용
    - **fallback**: 실패시 다른 서비스로 폴백 여부 (기본값: True)
    - **summarization**: ChatGPT API 요약 기능 사용 여부 (기본값: False, 모든 서비스에서 지원)
    - **summary_model**: 사용되지 않음 (ChatGPT API 사용)
    - **summary_type**: 사용되지 않음 (ChatGPT API 사용)
    """
    
    start_time = time.time()
    request_record = None
    
    try:
        logger.info(f"📁 음성 변환 요청 시작 - 파일: {file.filename}")
        print(f"Received file: {file.filename}")
        
        # 파일 확장자 확인
        file_extension = file.filename.split('.')[-1].lower()
        supported_formats = stt_manager.get_all_supported_formats()
        
        logger.info(f"📄 파일 확장자: {file_extension}")
        print(f"File extension: {file_extension}")
        
        if file_extension not in supported_formats:
            logger.warning(f"❌ 지원하지 않는 파일 형식: {file_extension}")
            # API 사용 로그 기록 (실패)
            try:
                logger.info("📊 API 사용 로그 기록 중 (실패)...")
                print(f"Attempting to log API usage (failure)...")
                APIUsageService.log_api_usage(
                    db=db,
                    user_uuid=None,
                    api_key_hash=None,
                    endpoint="/transcribe/",
                    method="POST",
                    status_code=400,
                    processing_time=time.time() - start_time,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent")
                )
                print(f"✅ API usage logged (failure)")
            except Exception as log_error:
                print(f"❌ Failed to log API usage: {log_error}")
                import traceback
                traceback.print_exc()
            
            raise HTTPException(
                status_code=400, 
                detail=f"지원되지 않는 파일 형식입니다. 지원 형식: {', '.join(supported_formats)}"
            )
        
        # 파일 내용 읽기
        file_content = await file.read()
        file_size = len(file_content)
        
        logger.info(f"📊 파일 크기: {file_size:,} bytes")
        
        # 음성파일 재생 시간 계산
        duration = get_audio_duration(file_content, file.filename)
        if duration and duration > 0:
            logger.info(f"🎵 음성파일 재생 시간: {format_duration(duration)}")
            print(f"Audio duration: {format_duration(duration)}")
        else:
            logger.warning(f"⚠️ 음성파일 재생 시간을 계산할 수 없습니다")
            print(f"Warning: Could not calculate audio duration")
            duration = None  # 체크 제약 조건을 위해 None으로 설정
        
        # 음성 파일을 지정된 경로에 저장 (데이터베이스 기록 전에 수행)
        stored_file_path = None
        try:
            logger.info(f"💾 음성 파일 저장 시작")
            stored_file_path = save_uploaded_file(
                user_uuid="anonymous",
                request_id="temp",
                filename=file.filename,
                file_content=file_content
            )
            logger.info(f"✅ 음성 파일 저장 완료 - 경로: {stored_file_path}")
            print(f"✅ Audio file saved to: {stored_file_path}")
            
            # 파일 경로를 /stt_storage/부터의 상대 경로로 변환
            from pathlib import Path
            relative_path = stored_file_path.replace(str(Path.cwd()), "/").replace("\\", "/")
            # if relative_path.startswith("/"):
            #    relative_path = relative_path[1:]  # 맨 앞의 / 제거
                
        except Exception as storage_error:
            logger.error(f"❌ 음성 파일 저장 실패: {storage_error}")
            print(f"❌ Failed to save audio file: {storage_error}")
            relative_path = file.filename  # 저장 실패 시 원본 파일명 사용
        
        # 데이터베이스에 요청 기록 (파일 경로 포함)
        try:
            logger.info("💾 데이터베이스에 요청 기록 생성 중...")
            print(f"Attempting to create request record...")
            print(f"DB session: {db}")
            transcription_service = TranscriptionService(db)
            request_record = transcription_service.create_request(
                filename=relative_path,  # 전체 경로로 변경
                file_size=file_size,
                service_requested=service,
                fallback_enabled=fallback,
                duration=duration
            )
            logger.info(f"✅ 요청 기록 생성 완료 - ID: {request_record.request_id}")
            print(f"✅ Created request record with ID: {request_record.request_id}")
                
        except Exception as db_error:
            logger.error(f"❌ 요청 기록 생성 실패: {db_error}")
            print(f"❌ Failed to create request record: {db_error}")
            print(f"Error type: {type(db_error)}")
            import traceback
            traceback.print_exc()
        
        # STT 서비스를 사용하여 음성 변환 수행
        logger.info(f"🚀 STT 변환 시작 - 서비스: {service or '기본값'}, 폴백: {fallback}")
        print(f"Starting STT transcription - Service: {service or 'default'}, Fallback: {fallback}")
        
        # 요약 기능 파라미터 준비 (ChatGPT API 사용을 위해 제거)
        extra_params = {}
        if summarization:
            logger.info(f"📝 요약 기능 활성화 - ChatGPT API 사용")
        
        # STT 매니저를 통해 음성 변환 수행
        if service:
            # 특정 서비스 지정
            if fallback:
                transcription_result = stt_manager.transcribe_with_fallback(file_content, file.filename, language_code="ko", preferred_service=service, **extra_params)
            else:
                transcription_result = stt_manager.transcribe_with_service(service, file_content, file.filename, **extra_params)
        else:
            # 기본 서비스 사용
            if fallback:
                transcription_result = stt_manager.transcribe_with_fallback(file_content, file.filename, **extra_params)
            else:
                transcription_result = stt_manager.transcribe_with_default(file_content, file.filename, **extra_params)
        
        logger.info(f"📡 STT 변환 완료 - 서비스: {transcription_result.get('service_name', 'unknown')}")
        print(f"STT transcription completed - Service: {transcription_result.get('service_name', 'unknown')}")
        
        # 변환 실패 확인
        if transcription_result.get('error'):
            error_detail = transcription_result.get('error', 'Unknown error')
            logger.error(f"❌ STT 변환 실패: {error_detail}")
            
            # 요청 실패로 업데이트
            if request_record:
                try:
                    logger.info(f"💾 요청 기록 업데이트 중 (실패) - ID: {request_record.request_id}")
                    TranscriptionService.complete_request(
                        db=db,
                        request_id=request_record.request_id,
                        status="failed",
                        error_message=f"STT error: {error_detail}"
                    )
                except Exception as db_error:
                    logger.error(f"❌ 요청 기록 업데이트 실패: {db_error}")
                    print(f"Failed to update request record: {db_error}")
            
            # API 사용 로그 기록 (실패)
            try:
                logger.info("📊 API 사용 로그 기록 중 (실패)...")
                APIUsageService.log_api_usage(
                    db=db,
                    user_uuid=None,
                    api_key_hash=None,
                    endpoint="/transcribe/",
                    method="POST",
                    status_code=500,
                    request_size=file_size,
                    processing_time=time.time() - start_time,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent")
                )
            except Exception as log_error:
                logger.error(f"❌ API 사용 로그 기록 실패: {log_error}")
                print(f"Failed to log API usage: {log_error}")
            
            raise HTTPException(status_code=500, detail=f"음성 변환 실패: {error_detail}")
        
        # 변환된 텍스트 추출
        transcribed_text = transcription_result.get('text', '')
        
        logger.info(f"✅ transcription_result ============================== {transcription_result}")

        
        # 빈 텍스트 처리 (테스트를 위해 정상 처리로 변경)
        if not transcribed_text:
            logger.warning("⚠️ 변환된 텍스트가 비어있음 - 빈 텍스트로 처리 계속")
            transcribed_text = ""  # 빈 문자열로 설정
        
        # 변환 완료
        processing_time = time.time() - start_time
        logger.info(f"✅ 변환 완료! 처리 시간: {processing_time:.2f}초")
        logger.info(f"📝 변환된 텍스트 길이: {len(transcribed_text)}자")
        
        # OpenAI 요약 생성 (모든 서비스에서 요약 활성화 시 사용)
        summary_text = None
        summary_time = 0.0
        used_service = transcription_result.get('service_name', '').lower()
        if transcribed_text and openai_service.is_configured() and summarization:
            try:
                summary_start_time = time.time()
                logger.info(f"🤖 OpenAI 요약 생성 시작 ({used_service} 서비스)")
                summary_text = await openai_service.summarize_text(transcribed_text)
                summary_time = time.time() - summary_start_time
                logger.info(f"✅ 요약 생성 완료: {len(summary_text) if summary_text else 0}자, 소요시간: {summary_time:.2f}초")
                print(f"Summary generated successfully: {len(summary_text) if summary_text else 0} characters, time: {summary_time:.2f}s")
            except Exception as summary_error:
                logger.error(f"❌ 요약 생성 실패: {summary_error}")
                print(f"Failed to generate summary: {summary_error}")
        
        # 요청 완료로 업데이트
        if request_record:
            try:
                logger.info(f"💾 요청 완료 처리 중 - ID: {request_record.request_id}")
                TranscriptionService.complete_request(
                    db=db,
                    request_id=request_record.request_id,
                    status="completed"
                )
                logger.info("✅ 요청 완료 처리 성공")
                
                # 응답 데이터 저장 (요약 포함)
                transcription_service = TranscriptionService(db)

                # transcript_id(response_rid) 저장
                transcript_id = transcription_result.get('transcript_id')
                if transcript_id:
                    try:
                        logger.info(f"💾 response_rid 업데이트 중 - ID: {request_record.request_id}, RID: {transcript_id}")
                        TranscriptionService.update_request_with_rid(db, request_record.request_id, transcript_id)
                        logger.info(f"✅ response_rid 업데이트 완료")
                    except Exception as rid_error:
                        logger.error(f"❌ response_rid 업데이트 실패: {rid_error}")

                # 오디오 길이 계산 (분 단위) - STT 시간 + 요약 시간
                duration_seconds = transcription_result.get('audio_duration', 0)
                # stt_processing_time = transcription_result.get('processing_time', 0)
                # stt_processing_time = transcription_result.get('processing_time', 0)
                total_processing_time = processing_time + summary_time
                
                logger.info(f"✅ audio_duration ============================== {duration_seconds}")
                logger.info(f"✅ summary_time ============================== {summary_time}")
                logger.info(f"✅ total_processing_time ============================== {total_processing_time}")

                # STT 시간 + 요약 시간을 분 단위로 계산
                audio_duration_minutes = round(total_processing_time / 60, 2)
                logger.info(f"✅ audio_duration_minutes ============================== {audio_duration_minutes}")
                
                # 토큰 사용량 계산 (1분당 1점)
                tokens_used = round(audio_duration_minutes * 1.0, 2)
                logger.info(f"✅ tokens_used ============================== {tokens_used}")
                
                # 서비스 제공업체 정보
                service_provider = transcription_result.get('service_name', 'unknown')
                
                logger.info(f"✅ service_provider ============================== {service_provider}")
                
                try:
                    # STT 결과에서 confidence와 language_code 추출
                    confidence_score = transcription_result.get('confidence')
                    language_detected = transcription_result.get('language_code')
                    
                    transcription_service.create_response(
                        request_id=request_record.request_id,
                        transcription_text=transcribed_text,
                        summary_text=summary_text,
                        service_used=service_provider,
                        processing_time=processing_time,
                        duration=processing_time,
                        success=True,
                        error_message=None,
                        service_provider=service_provider,
                        audio_duration_minutes=audio_duration_minutes,
                        tokens_used=tokens_used,
                        response_data=json.dumps(transcription_result, ensure_ascii=False) if transcription_result else None,
                        confidence_score=confidence_score,
                        language_detected=language_detected
                    )
                    logger.info(f"✅ 응답 저장 완료 - 요청 ID: {request_record.request_id}")
                except Exception as e:
                    logger.error(f"❌ 응답 저장 실패 - 요청 ID: {request_record.request_id}, 오류: {str(e)}")
                    # 응답 저장 실패 시에도 요청 완료 처리
                    transcription_service.complete_request(
                        db=db,
                        request_id=request_record.request_id,
                        status="completed_with_save_error",
                        error_message=f"Response save failed: {str(e)}"
                    )
                
                logger.info(f"✅ log ============================== 001")
                
            except Exception as db_error:
                print(f"Failed to save response: {db_error}")
        
        # 응답 데이터 구성 (사용자 정보 포함)
        response_data = {
            "user_id": None,  # 현재 인증되지 않은 사용자
            "email": None,    # 현재 인증되지 않은 사용자
            "request_id": request_record.request_id,
            "status": "completed",
            "stt_message": transcribed_text,
            "stt_summary": summary_text,
            "service_name": transcription_result.get('service_name', 'unknown'),
            "processing_time": transcription_result.get('processing_time', processing_time),
            "original_response": transcription_result
        }
        
        logger.info(f"✅ log ============================== 002")
        
        # AssemblyAI 요약이 있는 경우 추가
        if transcription_result.get('summary'):
            response_data["assemblyai_summary"] = transcription_result.get('summary')
            logger.info(f"📝 AssemblyAI 요약 포함됨: {len(transcription_result.get('summary', ''))}자")
        
        logger.info(f"✅ log ============================== 003")
        
        # API 사용 로그 기록 (성공)
        try:
            response_size = len(json.dumps(response_data).encode('utf-8'))
            APIUsageService.log_api_usage(
                db=db,
                user_uuid=None,
                api_key_hash=None,
                endpoint="/transcribe/",
                method="POST",
                status_code=200,
                request_size=file_size,
                response_size=response_size,
                processing_time=processing_time,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
        except Exception as log_error:
            print(f"Failed to log API usage: {log_error}")
    
        logger.info(f"✅ log ============================== 004")
        
        return JSONResponse(content=response_data)
    
    except HTTPException as he:
        logger.warning(f"⚠️ HTTP 예외 발생 - 상태 코드: {he.status_code}, 메시지: {he.detail}")
        # API 사용 로그 기록 (HTTPException)
        try:
            logger.info("📊 API 사용 로그 기록 중 (HTTPException)")
            APIUsageService.log_api_usage(
                db=db,
                user_uuid=None,
                api_key_hash=None,
                endpoint="/transcribe/",
                method="POST",
                status_code=he.status_code,
                processing_time=time.time() - start_time,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
        except Exception as log_error:
            logger.error(f"❌ API 사용 로그 기록 실패: {log_error}")
            print(f"Failed to log API usage: {log_error}")
        
        raise he
    except Exception as e:
        import traceback as tb
        logger.error(f"💥 예상치 못한 오류 발생: {type(e).__name__}: {str(e)}")
        logger.error(f"📍 오류 추적:\n{tb.format_exc()}")
        print(f"Exception occurred: {type(e).__name__}: {str(e)}")
        tb.print_exc()
        
        # 요청 실패로 업데이트
        if request_record:
            try:
                logger.info(f"💾 예외 상황 요청 기록 업데이트 중 - ID: {request_record.request_id}")
                TranscriptionService.complete_request(
                    db=db,
                    request_id=request_record.request_id,
                    status="failed",
                    error_message=str(e)
                )
            except Exception as db_error:
                logger.error(f"❌ 예외 상황 요청 기록 업데이트 실패: {db_error}")
                print(f"Failed to update request record: {db_error}")
        
        # API 사용 로그 기록 (서버 오류)
        try:
            logger.info("📊 API 사용 로그 기록 중 (서버 오류)")
            APIUsageService.log_api_usage(
                db=db,
                user_uuid=None,
                api_key_hash=None,
                endpoint="/transcribe/",
                method="POST",
                status_code=500,
                processing_time=time.time() - start_time,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
        except Exception as log_error:
            logger.error(f"❌ 서버 오류 API 사용 로그 기록 실패: {log_error}")
            print(f"Failed to log API usage: {log_error}")
        
        logger.error("🔄 HTTP 예외로 변환하여 응답")
        raise HTTPException(status_code=500, detail="음성 변환 중 예상치 못한 오류가 발생했습니다.")

@app.get("/", summary="서비스 상태 확인")
def read_root():
    return {"status": "online", "message": "Speech-to-Text 서비스가 실행 중입니다."}

@app.get("/test")
def test_endpoint():
    print("Test endpoint called")
    return {"status": "ok", "message": "Test endpoint working"}

# 사용자 관리 API
@app.post("/users/", summary="사용자 생성")
def create_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):
    """
    새로운 사용자를 생성합니다.
    - user_type: "개인" 또는 "조직"
    - phone_number: 전화번호 (선택사항)
    - password: 패스워드 (필수)
    """
    try:
        logger.info(f"사용자 생성 요청 - user_id: {user.user_id}, email: {user.email}, user_type: {user.user_type}")
        
        user_info = create_user(
            user_id=user.user_id, 
            email=user.email, 
            name=user.name,
            user_type=user.user_type,
            password=user.password,
            phone_number=user.phone_number,
            db=db
        )
        
        logger.info(f"사용자 생성 성공 - user_id: {user.user_id}, user_uuid: {user_info.get('user_uuid')}")
        return {"status": "success", "user": user_info}
    except HTTPException as e:
        logger.error(f"사용자 생성 실패 (HTTPException) - user_id: {user.user_id}, error: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"사용자 생성 실패 (Exception) - user_id: {user.user_id}, error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/login", summary="사용자 로그인")
def login(login_request: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    사용자 로그인 후 JWT 토큰을 발급합니다.
    """
    # 클라이언트 정보 수집
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    try:
        # 사용자 인증 (패스워드 검증 포함)
        user = authenticate_user(login_request.user_id, login_request.password, db)
        if not user:
            # 로그인 실패 기록
            login_log = LoginLog(
                user_uuid=login_request.user_id,
                ip_address=client_ip,
                user_agent=user_agent,
                success=False,
                failure_reason="Invalid credentials"
            )
            db.add(login_log)
            db.commit()
            logger.warning(f"로그인 실패 - 사용자: {login_request.user_id}, IP: {client_ip}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # JWT 토큰 생성
        access_token = create_access_token(data={"sub": login_request.user_id})
        
        # 로그인 성공 기록
        login_log = LoginLog(
            user_uuid=user['user_uuid'],
            ip_address=client_ip,
            user_agent=user_agent,
            success=True
        )
        db.add(login_log)
        db.commit()
        
        logger.info(f"로그인 성공 - 사용자: {login_request.user_id}, IP: {client_ip}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # 예외 발생시 로그인 실패 기록
        login_log = LoginLog(
            user_uuid=login_request.user_id,
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
            failure_reason=f"System error: {str(e)}"
        )
        db.add(login_log)
        db.commit()
        logger.error(f"로그인 시스템 오류 - 사용자: {login_request.user_id}, IP: {client_ip}, 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# 토큰 관리 API
@app.post("/tokens/{token_id}", summary="API 키 발행")
def create_token(token_id: str, description: Optional[str] = "", current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    사용자별 API 키를 발행합니다.
    JWT 토큰이 필요합니다.
    토큰명은 URL 파라미터로 입력합니다.
    토큰 정보는 데이터베이스에 저장됩니다.
    """
    try:
        # current_user는 user_id이므로 user_uuid를 조회해야 함
        user_info = get_user(current_user, db=db)
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        
        token_info = TokenManager.generate_api_key(
            user_uuid=user_info["user_uuid"],
            token_id=token_id,
            description=description,
            db=db
        )
        return {"status": "success", "token": token_info}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tokens/verify", summary="API 키 검증")
def verify_token_endpoint(current_user: str = Depends(verify_api_key_dependency), db: Session = Depends(get_db)):
    """
    API 키를 검증합니다.
    Authorization 헤더에 Bearer {api_key} 형식으로 전달해야 합니다.
    """
    user = get_user(current_user, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "status": "valid",
        "user_uuid": user["user_uuid"],
        "user": user
    }

@app.get("/tokens/", summary="사용자 토큰 목록 조회")
def get_user_tokens(current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    현재 사용자의 모든 토큰을 조회합니다.
    JWT 토큰이 필요합니다.
    데이터베이스에서 토큰 정보를 조회합니다.
    """
    try:
        # current_user는 user_id이므로 user_uuid를 조회해야 함
        user_info = get_user(current_user, db=db)
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        
        tokens = TokenManager.get_user_tokens(user_info["user_uuid"], db=db)
        return {"status": "success", "tokens": tokens}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tokens/revoke", summary="API 키 비활성화")
def revoke_token(revoke_request: TokenRevoke, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    API 키를 비활성화합니다.
    JWT 토큰이 필요합니다.
    """
    try:
        # current_user는 user_id이므로 user_uuid를 조회해야 함
        user_info = get_user(current_user, db=db)
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        
        success = TokenManager.revoke_api_key(revoke_request.api_key_hash, user_info["user_uuid"])
        if not success:
            raise HTTPException(status_code=404, detail="Token not found or not owned by user")
        
        return {"status": "success", "message": "Token revoked successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tokens/history", summary="토큰 사용 내역 조회")
def get_token_history(limit: int = 50, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    현재 사용자의 토큰 사용 내역을 조회합니다.
    JWT 토큰이 필요합니다.
    """
    try:
        # current_user는 user_id이므로 user_uuid를 조회해야 함
        user_info = get_user(current_user, db=db)
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        
        history = TokenManager.get_token_history(user_info["user_uuid"], limit)
        return {"status": "success", "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 음성 변환 내역 조회 API
@app.get("/transcriptions/", summary="음성 변환 요청 내역 조회")
def get_transcription_history(limit: int = 50, db: Session = Depends(get_db)):
    """
    음성 변환 요청 내역을 조회합니다.
    """
    try:
        from sqlalchemy import desc
        requests = db.query(TranscriptionRequest).order_by(
            desc(TranscriptionRequest.created_at)
        ).limit(limit).all()
        
        result = []
        for req in requests:
            result.append({
                "id": req.request_id,
                "filename": req.filename,
                "file_size": req.file_size,
                "file_extension": req.file_extension,
                "status": req.status,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "completed_at": req.completed_at.isoformat() if req.completed_at else None,
                "processing_time": req.processing_time,
                "error_message": req.error_message
            })
        
        return {"status": "success", "requests": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/transcriptions/{request_id}", summary="특정 음성 변환 요청 상세 조회")
def get_transcription_detail(request_id: str, db: Session = Depends(get_db)):
    """
    특정 음성 변환 요청의 상세 정보를 조회합니다.
    """
    try:
        result = TranscriptionService.get_request_with_response(db, request_id)
        if not result:
            raise HTTPException(status_code=404, detail="Request not found")
        
        request_data = result["request"]
        response_data = result["response"]
        
        return {
            "status": "success",
            "request": {
                "id": request_data.request_id,
                "filename": request_data.filename,
                "file_size": request_data.file_size,
                "file_extension": request_data.file_extension,
                "response_rid": request_data.response_rid,
                "status": request_data.status,
                "created_at": request_data.created_at.isoformat() if request_data.created_at else None,
                "completed_at": request_data.completed_at.isoformat() if request_data.completed_at else None,
                "processing_time": request_data.processing_time,
                "error_message": request_data.error_message
            },
            "response": {
                "id": response_data.id,
                "transcribed_text": response_data.transcribed_text,
                "confidence_score": response_data.confidence_score,
                "language_detected": response_data.language_detected,
                "duration": response_data.duration,
                "word_count": response_data.word_count,
                "created_at": response_data.created_at.isoformat() if response_data.created_at else None
            } if response_data else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api-usage/stats", summary="API 사용 통계 조회")
def get_api_usage_stats(days: int = 30, db: Session = Depends(get_db)):
    """
    전체 API 사용 통계를 조회합니다.
    """
    try:
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 총 요청 수
        total_requests = db.query(func.count(APIUsageLog.id)).filter(
            APIUsageLog.created_at >= start_date
        ).scalar()
        
        # 성공 요청 수
        successful_requests = db.query(func.count(APIUsageLog.id)).filter(
            APIUsageLog.created_at >= start_date,
            APIUsageLog.status_code >= 200,
            APIUsageLog.status_code < 300
        ).scalar()
        
        # 엔드포인트별 통계
        endpoint_stats = db.query(
            APIUsageLog.endpoint,
            func.count(APIUsageLog.id).label('count'),
            func.avg(APIUsageLog.processing_time).label('avg_time')
        ).filter(
            APIUsageLog.created_at >= start_date
        ).group_by(APIUsageLog.endpoint).all()
        
        return {
            "status": "success",
            "period_days": days,
            "total_requests": total_requests or 0,
            "successful_requests": successful_requests or 0,
            "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            "endpoint_stats": [
                {
                    "endpoint": stat.endpoint,
                    "request_count": stat.count,
                    "avg_processing_time": float(stat.avg_time) if stat.avg_time else 0
                }
                for stat in endpoint_stats
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api-usage/logs", summary="API 사용 로그 조회")
def get_api_usage_logs(limit: int = 100, db: Session = Depends(get_db)):
    """
    최근 API 사용 로그를 조회합니다.
    """
    try:
        from sqlalchemy import desc
        logs = db.query(APIUsageLog).order_by(
            desc(APIUsageLog.created_at)
        ).limit(limit).all()
        
        result = []
        for log in logs:
            result.append({
                "id": log.id,
                "endpoint": log.endpoint,
                "method": log.method,
                "status_code": log.status_code,
                "request_size": log.request_size,
                "response_size": log.response_size,
                "processing_time": log.processing_time,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at.isoformat() if log.created_at else None
            })
        
        return {"status": "success", "logs": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/login-logs", summary="로그인 기록 조회")
def get_login_logs(limit: int = 100, user_uuid: Optional[str] = None, db: Session = Depends(get_db)):
    """
    사용자 로그인 기록을 조회합니다.
    """
    try:
        # 기본 쿼리
        query = db.query(LoginLog)
        
        # 특정 사용자 필터링
        if user_uuid:
            query = query.filter(LoginLog.user_uuid == user_uuid)
        
        # 최신순으로 정렬하고 제한
        logs = query.order_by(LoginLog.created_at.desc()).limit(limit).all()
        
        log_list = []
        for log in logs:
            log_list.append({
                "id": log.id,
                "user_uuid": log.user_uuid,
                "login_time": log.login_time.isoformat() if log.login_time else None,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "success": log.success,
                "failure_reason": log.failure_reason,
                "created_at": log.created_at.isoformat() if log.created_at else None
            })
        
        return {
            "status": "success",
            "total_logs": len(log_list),
            "logs": log_list
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/login-stats", summary="로그인 통계 조회")
def get_login_stats(days: int = 30, db: Session = Depends(get_db)):
    """
    로그인 통계를 조회합니다.
    """
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func, and_
        
        # 기간 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 전체 로그인 시도 수
        total_attempts = db.query(LoginLog).filter(
            LoginLog.created_at >= start_date
        ).count()
        
        # 성공한 로그인 수
        successful_logins = db.query(LoginLog).filter(
            and_(
                LoginLog.created_at >= start_date,
                LoginLog.success == True
            )
        ).count()
        
        # 실패한 로그인 수
        failed_logins = db.query(LoginLog).filter(
            and_(
                LoginLog.created_at >= start_date,
                LoginLog.success == False
            )
        ).count()
        
        # 고유 사용자 수
        unique_users = db.query(LoginLog.user_uuid).filter(
            and_(
                LoginLog.created_at >= start_date,
                LoginLog.success == True
            )
        ).distinct().count()
        
        # 성공률 계산
        success_rate = (successful_logins / total_attempts * 100) if total_attempts > 0 else 0
        
        return {
            "status": "success",
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "statistics": {
                "total_attempts": total_attempts,
                "successful_logins": successful_logins,
                "failed_logins": failed_logins,
                "unique_users": unique_users,
                "success_rate": round(success_rate, 2)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API 키로 보호된 transcribe 엔드포인트
@app.post("/transcribe/protected/", summary="API 키로 보호된 음성 파일 변환")
async def transcribe_audio_protected(
    request: Request,
    file: UploadFile = File(...), 
    service: Optional[str] = None,
    fallback: bool = True,
    summarization: bool = False,
    # summary_model: str = "informative",
    # summary_type: str = "bullets",
    current_user: str = Depends(verify_api_key_dependency),
    db: Session = Depends(get_db)
):
    """
    API 키로 보호된 음성 파일을 텍스트로 변환합니다.
    Authorization 헤더에 Bearer {api_key} 형식으로 API 키를 전달해야 합니다.
    
    Parameters:
    - service: 사용할 STT 서비스 ("assemblyai" 또는 "daglo"). 지정하지 않으면 자동 선택
    - fallback: 첫 번째 서비스 실패 시 다른 서비스로 자동 전환 여부 (기본값: True)
    - summarization: 요약 기능 사용 여부 (ChatGPT API 사용)
    - summary_model: 요약 모델 (사용되지 않음 - ChatGPT API 사용)
    - summary_type: 요약 타입 (사용되지 않음 - ChatGPT API 사용)
    """
    start_time = time.time()
    transcription_service = TranscriptionService(db)
    api_usage_service = APIUsageService(db)
    
    try:
        # 파일 확장자 검증
        allowed_extensions = [".mp3", ".wav", ".m4a", ".flac", ".aac"]
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"지원되지 않는 파일 형식입니다. 지원 형식: {', '.join(allowed_extensions)}"
            )
        
        # 파일 내용 읽기
        file_content = await file.read()
        
        # 음성 파일을 지정된 경로에 저장 (요청 정보 저장 전에 수행)
        stored_file_path = None
        try:
            logger.info(f"💾 음성 파일 저장 시작 - 사용자: {current_user}")
            stored_file_path = save_uploaded_file(
                user_uuid=current_user,
                request_id="temp",
                filename=file.filename,
                file_content=file_content
            )
            logger.info(f"✅ 음성 파일 저장 완료 - 경로: {stored_file_path}")
            
            # 파일 경로를 /stt_storage/부터의 상대 경로로 변환
            from pathlib import Path
            relative_path = stored_file_path.replace(str(Path.cwd()), "").replace("\\", "/")
            if relative_path.startswith("/"):
                relative_path = relative_path[1:]  # 맨 앞의 / 제거
                
        except Exception as storage_error:
            logger.error(f"❌ 음성 파일 저장 실패: {storage_error}")
            relative_path = file.filename  # 저장 실패 시 원본 파일명 사용
        
        # 요청 정보 저장 (파일 경로 포함)
        request_record = transcription_service.create_request(
            filename=relative_path,  # 전체 경로로 변경
            file_size=len(file_content),
            service_requested=service,
            fallback_enabled=fallback,
            client_ip=request.client.host,
            user_agent=request.headers.get("user-agent", ""),
            user_uuid=current_user  # user_uuid 전달 추가
        )
        
        # STT 처리
        result = stt_manager.transcribe_with_fallback(
            file_content=file_content,
            filename=file.filename,
            preferred_service=service
        )
        
        # 요약 처리
        summary_text = None
        summary_time = 0.0
        if summarization and result.get("text"):
            try:
                summary_start_time = time.time()
                summary_result = await openai_service.summarize_text(result["text"])
                summary_time = time.time() - summary_start_time
                summary_text = summary_result if summary_result else ""
                logger.info(f"✅ 요약 생성 완료: {len(summary_text) if summary_text else 0}자, 소요시간: {summary_time:.2f}초")
            except Exception as e:
                logger.error(f"Summarization failed: {str(e)}")
                summary_text = "요약 생성 중 오류가 발생했습니다."
        
        # 처리 시간 계산
        processing_time = time.time() - start_time
        
        # STT 시간 + 요약 시간을 분 단위로 계산
        stt_processing_time = result.get("processing_time", processing_time - summary_time)
        total_processing_time = stt_processing_time + summary_time
        audio_duration_minutes = round(total_processing_time / 60.0, 2)
        
        # 토큰 사용량 계산 (1분당 1점)
        tokens_used = round(audio_duration_minutes * 1.0, 2)
        
        # STT 결과에서 confidence와 language_code 추출
        confidence_score = result.get('confidence')
        language_detected = result.get('language_code')
        
        # 응답 정보 저장 (새로운 컬럼들 포함)
        response_record = transcription_service.create_response(
            request_id=request_record.request_id,
            transcription_text=result.get("text", ""),  # STT 매니저는 'text' 필드를 사용
            summary_text=summary_text,
            service_used=result.get("service_name", ""),  # STT 매니저는 'service_name' 필드를 사용
            processing_time=processing_time,
            duration=processing_time,
            success=True,
            error_message=None,
            service_provider=result.get("service_name", ""),
            audio_duration_minutes=audio_duration_minutes,
            tokens_used=tokens_used,
            response_data=json.dumps(result, ensure_ascii=False) if result else None,
            confidence_score=confidence_score,
            language_detected=language_detected
        )

        # response_rid 업데이트 추가
        # TranscriptionService.update_request_with_rid(
        #     db=db,
        #     request_id=request_record.request_id,
        #     response_rid=str(response_record.id)
        # )
        
        transcript_id = result.get('transcript_id')
        if transcript_id:
            try:
                logger.info(f"💾 response_rid 업데이트 중 - ID: {request_record.request_id}, RID: {transcript_id}")
                TranscriptionService.update_request_with_rid(db, request_record.request_id, transcript_id)
                logger.info(f"✅ response_rid 업데이트 완료")
            except Exception as rid_error:
                logger.error(f"❌ response_rid 업데이트 실패: {rid_error}")                
        
        logger.info("💾 response_rid -------------------------------0 ")
        logger.info(f"💾 response_rid RID: {transcript_id}")
            
        # 요청 완료 상태로 업데이트
        TranscriptionService.complete_request(
            db=db,
            request_id=request_record.request_id,
            status="completed"
        )
        
        # API 사용 로그 저장
        api_usage_service.log_usage(
            user_uuid=current_user,
            endpoint="/transcribe/protected/",
            method="POST",
            status_code=200,
            processing_time=processing_time,
            client_ip=request.client.host,
            user_agent=request.headers.get("user-agent", "")
        )
        
        return {
            "status": "success",
            "transcription": result.get("text", ""),
            "summary": summary_text,
            "service_used": result.get("service_name", ""),
            "duration": result.get("duration", 0),
            "processing_time": round(processing_time, 2),
            "audio_duration_minutes": audio_duration_minutes,
            "tokens_used": tokens_used,
            "user_uuid": current_user,
            "filename": file.filename,
            "request_id": request_record.request_id,
            "response_id": response_record.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time

        # 실패한 경우에도 응답 기록 저장
        if 'request_record' in locals():
            try:
                error_response = transcription_service.create_response(
                    request_id=request_record.request_id,
                    transcription_text="",
                    summary_text=None,
                    service_used="",
                    processing_time=processing_time,
                    duration=processing_time,
                    success=False,
                    error_message=str(e),
                    service_provider="",
                    audio_duration_minutes=0.0,
                    tokens_used=0.0,
                    confidence_score=None,
                    language_detected=None
                )
                
                # 실패 케이스에서도 response_rid 업데이트
                # TranscriptionService.update_request_with_rid(
                #     db=db,
                #     request_id=request_record.request_id,
                #     response_rid=str(error_response.id)
                # )
                
                # transcript_id(response_rid) 저장
                transcript_id = result.get('transcript_id')
                if transcript_id:
                    try:
                        logger.info(f"💾 response_rid 업데이트 중 - ID: {request_record.request_id}, RID: {transcript_id}")
                        TranscriptionService.update_request_with_rid(db, request_record.request_id, transcript_id)
                        logger.info(f"✅ response_rid 업데이트 완료")
                    except Exception as rid_error:
                        logger.error(f"❌ response_rid 업데이트 실패: {rid_error}")                
                
                logger.info("💾 response_rid -------------------------------1 ")
                logger.info(f"💾 response_rid RID: {transcript_id}")

                # 요청을 실패 상태로 완료 처리
                TranscriptionService.complete_request(
                    db=db,
                    request_id=request_record.request_id,
                    status="failed",
                    error_message=str(e)
                )
            except Exception as db_error:
                logger.error(f"❌ 응답 저장 실패: {db_error}")
        
        # API 사용 로그 저장
        api_usage_service.log_usage(
            user_uuid=current_user,
            endpoint="/transcribe/protected/",
            method="POST",
            status_code=500,
            processing_time=processing_time,
            client_ip=request.client.host,
            user_agent=request.headers.get("user-agent", "")
        )
        
        logger.error(f"Transcription error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import logging
    
    # 로깅 레벨 설정
    logging.basicConfig(level=logging.DEBUG)
    
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=False, log_level="debug")