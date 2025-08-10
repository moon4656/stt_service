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

# Daglo API 설정 가져오기
DAGLO_API_KEY = os.getenv("DAGLO_API_KEY")
DAGLO_API_URL = os.getenv("DAGLO_API_URL", "https://apis.daglo.ai/stt/v1/async/transcripts")

if not DAGLO_API_KEY:
    raise ValueError("DAGLO_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

# OpenAI 서비스 초기화
openai_service = OpenAIService()

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
    description="Daglo API를 사용한 음성-텍스트 변환 서비스",
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
async def transcribe_audio(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    음성 파일을 업로드하여 텍스트로 변환합니다.
    요청과 응답 내역이 PostgreSQL에 저장됩니다.
    
    - **file**: 변환할 음성 파일 (지원 형식: mp3, wav, m4a 등)
    """
    
    start_time = time.time()
    request_record = None
    
    try:
        logger.info(f"📁 음성 변환 요청 시작 - 파일: {file.filename}")
        print(f"Received file: {file.filename}")
        
        # 파일 확장자 확인
        file_extension = file.filename.split('.')[-1].lower()
        supported_formats = ['mp3', 'wav', 'm4a', 'ogg', 'flac', '3gp', '3gpp', 'ac3', 'aac', 'aiff', 'amr', 'au', 'opus', 'ra']
        
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
                    user_id=None,
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
        
        # 데이터베이스에 요청 기록
        try:
            logger.info("💾 데이터베이스에 요청 기록 생성 중...")
            print(f"Attempting to create request record...")
            print(f"DB session: {db}")
            request_record = TranscriptionService.create_request(
                db=db,
                user_id='moon4656',  # 익명 사용자
                filename=file.filename,
                file_size=file_size,
                file_extension=file_extension
            )
            logger.info(f"✅ 요청 기록 생성 완료 - ID: {request_record.id}")
            print(f"✅ Created request record with ID: {request_record.id}")
        except Exception as db_error:
            logger.error(f"❌ 요청 기록 생성 실패: {db_error}")
            print(f"❌ Failed to create request record: {db_error}")
            print(f"Error type: {type(db_error)}")
            import traceback
            traceback.print_exc()
        
        # Daglo API 요청 헤더
        headers = {
            "Authorization": f"Bearer {DAGLO_API_KEY}"
        }
        
        # 파일 업로드를 위한 파일 객체 생성
        files = {
            "file": (file.filename, file_content, f"audio/{file_extension}")
        }
        
        logger.info(f"🚀 Daglo API 호출 시작 - URL: {DAGLO_API_URL}")
        
        print(f"Uploading to Daglo API: {DAGLO_API_URL}")
        print(f"File size: {file_size} bytes")
        
        # 1단계: Daglo API에 음성 파일 업로드
        response = requests.post(DAGLO_API_URL, headers=headers, files=files)
        
        logger.info(f"📡 Daglo API 응답 - 상태코드: {response.status_code}")
        print(f"Daglo API response status: {response.status_code}")
        print(f"Daglo API response text: {response.text}")
        
        # 응답 확인
        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"❌ Daglo API 오류 - 상태코드: {response.status_code}, 내용: {error_detail}")
            
            # 요청 실패로 업데이트
            if request_record:
                try:
                    logger.info(f"💾 요청 기록 업데이트 중 (실패) - ID: {request_record.id}")
                    TranscriptionService.complete_request(
                        db=db,
                        request_id=request_record.id,
                        status="failed",
                        error_message=f"Daglo API error: {error_detail}"
                    )
                except Exception as db_error:
                    logger.error(f"❌ 요청 기록 업데이트 실패: {db_error}")
                    print(f"Failed to update request record: {db_error}")
            
            # API 사용 로그 기록 (실패)
            try:
                logger.info("📊 API 사용 로그 기록 중 (실패)...")
                APIUsageService.log_api_usage(
                    db=db,
                    user_id=None,
                    api_key_hash=None,
                    endpoint="/transcribe/",
                    method="POST",
                    status_code=response.status_code,
                    request_size=file_size,
                    processing_time=time.time() - start_time,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent")
                )
            except Exception as log_error:
                logger.error(f"❌ API 사용 로그 기록 실패: {log_error}")
                print(f"Failed to log API usage: {log_error}")
            
            raise HTTPException(status_code=response.status_code, detail=f"API 호출 실패: {error_detail}")
        
        # RID 추출
        upload_result = response.json()
        rid = upload_result.get('rid')
        
        if not rid:
            logger.error("❌ Daglo API에서 RID를 받지 못함")
            # 요청 실패로 업데이트
            if request_record:
                try:
                    logger.info(f"💾 요청 기록 업데이트 중 (RID 없음) - ID: {request_record.id}")
                    TranscriptionService.complete_request(
                        db=db,
                        request_id=request_record.id,
                        status="failed",
                        error_message="RID not received from Daglo API"
                    )
                except Exception as db_error:
                    logger.error(f"❌ 요청 기록 업데이트 실패: {db_error}")
                    print(f"Failed to update request record: {db_error}")
            
            raise HTTPException(status_code=500, detail="RID를 받지 못했습니다.")
        
        logger.info(f"✅ RID 수신 성공: {rid}")
        
        # RID를 요청 기록에 업데이트
        if request_record:
            try:
                logger.info(f"💾 RID 업데이트 중 - ID: {request_record.id}, RID: {rid}")
                TranscriptionService.update_request_with_rid(db=db, request_id=request_record.id, daglo_rid=rid)
            except Exception as db_error:
                logger.error(f"❌ RID 업데이트 실패: {db_error}")
                print(f"Failed to update RID: {db_error}")
        
        # 2단계: RID로 결과 조회 (폴링)
        result_url = f"{DAGLO_API_URL}/{rid}"
        max_attempts = 30  # 최대 30번 시도 (약 5분)
        
        logger.info(f"🔄 변환 결과 폴링 시작 - URL: {result_url}, 최대 시도: {max_attempts}회")
        
        for attempt in range(max_attempts):
            logger.info(f"🔄 폴링 시도 {attempt + 1}/{max_attempts}")
            result_response = requests.get(result_url, headers=headers)
            
            if result_response.status_code == 200:
                result_data = result_response.json()
                status = result_data.get('status')
                logger.info(f"📊 변환 상태: {status}")
                
                if status == 'transcribed':
                    # 변환 완료
                    processing_time = time.time() - start_time
                    logger.info(f"✅ 변환 완료! 처리 시간: {processing_time:.2f}초")
                    
                    # STT 텍스트 추출
                    transcribed_text = ""
                    if 'sttResults' in result_data and result_data['sttResults']:
                        stt_results = result_data['sttResults']
                        if isinstance(stt_results, list) and len(stt_results) > 0:
                            # sttResults가 리스트인 경우 첫 번째 요소에서 transcript 추출
                            transcribed_text = stt_results[0].get('transcript', '') if isinstance(stt_results[0], dict) else ''
                        elif isinstance(stt_results, dict):
                            # sttResults가 딕셔너리인 경우
                            transcribed_text = stt_results.get('transcript', '')
                    else:
                        transcribed_text = result_data.get('text', '')
                    
                    logger.info(f"📝 변환된 텍스트 길이: {len(transcribed_text)}자")
                    
                    # OpenAI 요약 생성
                    summary_text = None
                    if transcribed_text and openai_service.is_configured():
                        try:
                            logger.info("🤖 OpenAI 요약 생성 시작")
                            summary_text = await openai_service.summarize_text(transcribed_text)
                            logger.info(f"✅ 요약 생성 완료: {len(summary_text) if summary_text else 0}자")
                            print(f"Summary generated successfully: {len(summary_text) if summary_text else 0} characters")
                        except Exception as summary_error:
                            logger.error(f"❌ 요약 생성 실패: {summary_error}")
                            print(f"Failed to generate summary: {summary_error}")
                    
                    # 요청 완료로 업데이트
                    if request_record:
                        try:
                            logger.info(f"💾 요청 완료 처리 중 - ID: {request_record.id}")
                            TranscriptionService.complete_request(
                                db=db,
                                request_id=request_record.id,
                                status="completed"
                            )
                            logger.info("✅ 요청 완료 처리 성공")
                            
                            # 응답 데이터 저장 (요약 포함)
                            TranscriptionService.create_response(
                                db=db,
                                request_id=request_record.id,
                                daglo_response=result_data,
                                summary_text=summary_text
                            )
                        except Exception as db_error:
                            print(f"Failed to save response: {db_error}")
                    
                    # 응답 데이터 구성 (사용자 정보 포함)
                    response_data = {
                        "user_id": None,  # 현재 인증되지 않은 사용자
                        "email": None,    # 현재 인증되지 않은 사용자
                        "stt_message": transcribed_text,
                        "stt_summary": summary_text,
                        "original_response": result_data
                    }
                    
                    # API 사용 로그 기록 (성공)
                    try:
                        response_size = len(json.dumps(response_data).encode('utf-8'))
                        APIUsageService.log_api_usage(
                            db=db,
                            user_id=None,
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
                    
                    return JSONResponse(content=response_data)
                    
                elif status in ['failed', 'error']:
                    # 변환 실패
                    logger.error(f"❌ Daglo 변환 실패: {status}")
                    if request_record:
                        try:
                            logger.info(f"💾 실패 상태 업데이트 중 - ID: {request_record.id}")
                            TranscriptionService.complete_request(
                                db=db,
                                request_id=request_record.id,
                                status="failed",
                                error_message=f"Daglo transcription failed: {status}"
                            )
                        except Exception as db_error:
                            logger.error(f"❌ 실패 상태 업데이트 실패: {db_error}")
                            print(f"Failed to update request record: {db_error}")
                    
                    raise HTTPException(status_code=500, detail="음성 변환에 실패했습니다.")
                else:
                    # 아직 처리 중, 10초 대기
                    logger.info(f"⏳ 변환 진행 중... 10초 대기 (상태: {status})")
                    time.sleep(10)
            else:
                logger.error(f"❌ 결과 조회 실패 - 상태 코드: {result_response.status_code}")
                raise HTTPException(status_code=result_response.status_code, detail="결과 조회 실패")
        
        # 최대 시도 횟수 초과
        logger.error(f"⏰ 변환 타임아웃 - 최대 시도 횟수({max_attempts}) 초과")
        if request_record:
            try:
                logger.info(f"💾 타임아웃 상태 업데이트 중 - ID: {request_record.id}")
                TranscriptionService.complete_request(
                    db=db,
                    request_id=request_record.id,
                    status="failed",
                    error_message="Transcription timeout"
                )
            except Exception as db_error:
                logger.error(f"❌ 타임아웃 상태 업데이트 실패: {db_error}")
                print(f"Failed to update request record: {db_error}")
        
        raise HTTPException(status_code=408, detail="음성 변환 시간이 초과되었습니다.")
    
    except HTTPException as he:
        logger.warning(f"⚠️ HTTP 예외 발생 - 상태 코드: {he.status_code}, 메시지: {he.detail}")
        # API 사용 로그 기록 (HTTPException)
        try:
            logger.info("📊 API 사용 로그 기록 중 (HTTPException)")
            APIUsageService.log_api_usage(
                db=db,
                user_id=None,
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
        logger.error(f"💥 예상치 못한 오류 발생: {type(e).__name__}: {str(e)}")
        logger.error(f"📍 오류 추적:\n{traceback.format_exc()}")
        print(f"Exception occurred: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        
        # 요청 실패로 업데이트
        if request_record:
            try:
                logger.info(f"💾 예외 상황 요청 기록 업데이트 중 - ID: {request_record.id}")
                TranscriptionService.complete_request(
                    db=db,
                    request_id=request_record.id,
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
                user_id=None,
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
        
        logger.error("🔄 전역 예외 핸들러로 예외 전달")
        raise e  # 전역 예외 핸들러가 처리하도록 함

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
    """
    try:
        user_info = create_user(
            user_id=user.user_id, 
            email=user.email, 
            name=user.name,
            user_type=user.user_type,
            password=user.password,
            phone_number=user.phone_number,
            db=db
        )
        return {"status": "success", "user": user_info}
    except HTTPException as e:
        raise e
    except Exception as e:
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
                user_id=login_request.user_id,
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
            user_id=login_request.user_id,
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
            user_id=login_request.user_id,
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
        token_info = TokenManager.generate_api_key(
            user_id=current_user,
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
def verify_token_endpoint(current_user: str = Depends(verify_api_key_dependency)):
    """
    API 키를 검증합니다.
    Authorization 헤더에 Bearer {api_key} 형식으로 전달해야 합니다.
    """
    user = get_user(current_user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "status": "valid",
        "user_id": current_user,
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
        tokens = TokenManager.get_user_tokens(current_user, db=db)
        return {"status": "success", "tokens": tokens}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tokens/revoke", summary="API 키 비활성화")
def revoke_token(revoke_request: TokenRevoke, current_user: str = Depends(verify_token)):
    """
    API 키를 비활성화합니다.
    JWT 토큰이 필요합니다.
    """
    try:
        success = TokenManager.revoke_api_key(revoke_request.api_key_hash, current_user)
        if not success:
            raise HTTPException(status_code=404, detail="Token not found or not owned by user")
        
        return {"status": "success", "message": "Token revoked successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tokens/history", summary="토큰 사용 내역 조회")
def get_token_history(limit: int = 50, current_user: str = Depends(verify_token)):
    """
    현재 사용자의 토큰 사용 내역을 조회합니다.
    JWT 토큰이 필요합니다.
    """
    try:
        history = TokenManager.get_token_history(current_user, limit)
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
                "id": req.id,
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
def get_transcription_detail(request_id: int, db: Session = Depends(get_db)):
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
                "id": request_data.id,
                "filename": request_data.filename,
                "file_size": request_data.file_size,
                "file_extension": request_data.file_extension,
                "daglo_rid": request_data.daglo_rid,
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
def get_login_logs(limit: int = 100, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    사용자 로그인 기록을 조회합니다.
    """
    try:
        # 기본 쿼리
        query = db.query(LoginLog)
        
        # 특정 사용자 필터링
        if user_id:
            query = query.filter(LoginLog.user_id == user_id)
        
        # 최신순으로 정렬하고 제한
        logs = query.order_by(LoginLog.created_at.desc()).limit(limit).all()
        
        log_list = []
        for log in logs:
            log_list.append({
                "id": log.id,
                "user_id": log.user_id,
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
        unique_users = db.query(LoginLog.user_id).filter(
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
async def transcribe_audio_protected(file: UploadFile = File(...), current_user: str = Depends(verify_api_key_dependency)):
    """
    API 키로 보호된 음성 파일을 텍스트로 변환합니다.
    Authorization 헤더에 Bearer {api_key} 형식으로 API 키를 전달해야 합니다.
    """
    # 기존 transcribe_audio 로직과 동일
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
        
        # Daglo API 요청 준비
        headers = {
            "Authorization": f"Bearer {DAGLO_API_KEY}"
        }
        
        files = {
            "file": (file.filename, file_content, file.content_type)
        }
        
        # Daglo API 호출
        response = requests.post(DAGLO_API_URL, headers=headers, files=files)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"API 호출 실패: {response.text}"
            )
        
        # 응답에서 rid 추출
        response_data = response.json()
        rid = response_data.get("rid")
        
        if not rid:
            raise HTTPException(
                status_code=500,
                detail="API 응답에서 rid를 찾을 수 없습니다."
            )
        
        # 결과 폴링
        result_url = f"https://apis.daglo.ai/stt/v1/async/transcripts/{rid}"
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            result_response = requests.get(result_url, headers=headers)
            
            if result_response.status_code == 200:
                result_data = result_response.json()
                status = result_data.get("status")
                
                if status == "completed":
                    return {
                        "status": "success",
                        "transcription": result_data.get("text", ""),
                        "user_id": current_user,
                        "filename": file.filename
                    }
                elif status == "failed":
                    raise HTTPException(
                        status_code=500,
                        detail="음성 변환에 실패했습니다."
                    )
            
            attempt += 1
            time.sleep(2)
        
        raise HTTPException(
            status_code=408,
            detail="음성 변환 시간이 초과되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        traceback.print_exc()
        raise

if __name__ == "__main__":
    import logging
    
    # 로깅 레벨 설정
    logging.basicConfig(level=logging.DEBUG)
    
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")