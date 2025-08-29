import calendar
import os
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, status, Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from dotenv import load_dotenv
from decimal import Decimal
import uvicorn
import time
import traceback
import sys
import json
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime, date
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from backend.core.auth import (
    TokenManager, 
    create_user, 
    get_user, 
    verify_token, 
    verify_api_key_dependency,
    get_token_id_dependency,
    create_access_token,
    authenticate_user,
    hash_password,
    verify_password
)
from backend.core.database import get_db, create_tables, test_connection, TranscriptionRequest, TranscriptionResponse, APIUsageLog, LoginLog, APIToken, SubscriptionPlan, Payment, SubscriptionPayment, TokenPayment, OveragePayment, ServiceToken, TokenUsageHistory, User, SubscriptionMaster, SubscriptionChangeHistory
from backend.core.db_service import TranscriptionService, APIUsageService
from backend.services.openai_service import OpenAIService
from backend.services.stt_manager import STTManager
from backend.utils.audio_utils import get_audio_duration, format_duration
from backend.core.file_storage import save_uploaded_file, get_stored_file_path, file_storage_manager
# Get last day of month
from calendar import monthrange
from datetime import datetime, timedelta

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

# API 사용 로그 미들웨어
class APIUsageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 요청 크기 계산
        request_size = 0
        if hasattr(request, 'body'):
            try:
                body = await request.body()
                request_size = len(body)
                # body를 다시 읽을 수 있도록 설정
                request._body = body
            except:
                request_size = 0
        
        # 응답 처리
        response = await call_next(request)
        
        # 처리 시간 계산
        processing_time = time.time() - start_time
        
        # GET, POST 요청에 대해서만 로그 기록
        if request.method in ["GET", "POST"]:
            try:
                # 데이터베이스 세션 생성
                from database import SessionLocal
                db = SessionLocal()
                
                try:
                    # API 사용 로그 기록
                    APIUsageService.log_api_usage(
                        db=db,
                        user_uuid=None,  # 미들웨어에서는 사용자 정보를 알 수 없음
                        api_key_hash=None,
                        endpoint=str(request.url.path),
                        method=request.method,
                        status_code=response.status_code,
                        request_size=request_size,
                        response_size=getattr(response, 'content_length', 0) or 0,
                        processing_time=processing_time,
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent")
                    )
                    db.commit()
                except Exception as log_error:
                    logger.error(f"API 사용 로그 기록 실패: {log_error}")
                    db.rollback()
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"미들웨어에서 오류 발생: {e}")
        
        return response

# FastAPI 앱 초기화
app = FastAPI(
    title="Speech-to-Text Service", 
    description="다중 STT 서비스(AssemblyAI, Daglo, Fast-Whisper, Deepgram, Tiro)를 지원하는 음성-텍스트 변환 서비스",
    lifespan=lifespan
)

# 미들웨어 추가
app.add_middleware(APIUsageMiddleware)

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

class SubscriptionPlanCreate(BaseModel):
    plan_code: str
    plan_description: Optional[str] = None
    monthly_price: int
    monthly_service_tokens: int
    per_minute_rate: Optional[float] = None
    overage_per_minute_rate: Optional[float] = None
    is_active: bool = True

class SubscriptionPlanUpdate(BaseModel):
    plan_code: Optional[str] = None
    plan_description: Optional[str] = None
    monthly_price: Optional[int] = None
    monthly_service_tokens: Optional[int] = None
    per_minute_rate: Optional[float] = None
    overage_per_minute_rate: Optional[float] = None
    is_active: Optional[bool] = None

# 결제 관련 Pydantic 모델들
class PaymentCreate(BaseModel):
    plan_code: str
    quantity: int = 1  # 인원수
    payment_method: Optional[str] = None
    payment_type: str = "subscription"
    external_payment_id: Optional[str] = None

class PaymentUpdate(BaseModel):
    payment_status: Optional[str] = None
    payment_method: Optional[str] = None
    external_payment_id: Optional[str] = None

class SubscriptionPaymentCreate(BaseModel):
    payment_id: str
    plan_code: str
    unit_price: int
    quantity: int = 1
    amount: int

class TokenPaymentCreate(BaseModel):
    payment_id: str
    token_quantity: int
    token_unit_price: int
    amount: int

class OveragePaymentCreate(BaseModel):
    payment_id: str
    plan_code: str
    unit_price: int
    overage_unit_price: int
    overage_tokens: float
    amount: int

class ServiceTokenCreate(BaseModel):
    user_uuid: str
    token_id: str
    quota_tokens: Decimal
    token_expiry_date: str  # YYYY-MM-DD 형식
    status: str = "active"

class ServiceTokenUpdate(BaseModel):
    quota_tokens: Optional[Decimal] = None
    used_tokens: Optional[Decimal] = None
    token_expiry_date: Optional[str] = None
    status: Optional[str] = None

# 추가 토큰 구매 관련 Pydantic 모델
class AdditionalTokenPurchaseRequest(BaseModel):
    token_quantity: int = Field(..., gt=0, description="구매할 토큰 수량 (양수만 허용)")
    payment_method: Optional[str] = Field(None, description="결제 수단")

class AdditionalTokenPurchaseResponse(BaseModel):
    status: str
    message: str
    data: dict

# 월빌링 관련 Pydantic 모델들
class MonthlyBillingRequest(BaseModel):
    target_year: int = Field(..., ge=2020, le=2030, description="청구 연도")
    target_month: int = Field(..., ge=1, le=12, description="청구 월")

class MonthlyBillingResponse(BaseModel):
    status: str
    message: str
    data: dict

class MonthlySubscriptionBillingRequest(BaseModel):
    target_year: int = Field(..., ge=2020, le=2030, description="결제 연도")
    target_month: int = Field(..., ge=1, le=12, description="결제 월")

class MonthlyBillingSummaryRequest(BaseModel):
    target_year: int = Field(..., ge=2020, le=2030, description="조회 연도")
    target_month: int = Field(..., ge=1, le=12, description="조회 월")

class TokenUsageCreate(BaseModel):
    token_id: str
    used_tokens: float
    request_id: str

class SubscriptionMasterCreate(BaseModel):
    plan_code: str
    subscription_start_date: str  # YYYY-MM-DD 형식
    subscription_end_date: Optional[str] = None  # YYYY-MM-DD 형식
    next_billing_date: Optional[str] = None  # YYYY-MM-DD 형식
    auto_renewal: bool = True
    renewal_plan_code: Optional[str] = None

class SubscriptionMasterUpdate(BaseModel):
    plan_code: Optional[str] = None
    subscription_status: Optional[str] = None
    subscription_end_date: Optional[str] = None
    next_billing_date: Optional[str] = None
    auto_renewal: Optional[bool] = None
    renewal_plan_code: Optional[str] = None

class SubscriptionChangeCreate(BaseModel):
    change_type: str  # create, upgrade, downgrade, suspend, resume, cancel, expire, renew
    change_reason: Optional[str] = None
    new_plan_code: Optional[str] = None
    effective_date: str  # YYYY-MM-DD 형식
    proration_amount: Optional[int] = None
    refund_amount: Optional[int] = None
    additional_charge: Optional[int] = None
    admin_notes: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

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
    다중 STT 서비스(Daglo, Tiro, AssemblyAI, Deepgram, Fast-Whisper)를 지원하며 폴백 기능을 제공합니다.
    요청과 응답 내역이 PostgreSQL에 저장됩니다.
    
    - **file**: 변환할 음성 파일
    - **service**: 사용할 STT 서비스 (daglo, tiro, assemblyai, deepgram, fast-whisper). 미지정시 기본 서비스 사용
    - **model_size**: Fast-Whisper 모델 크기 (tiny, base, small, medium, large-v2, large-v3)
    - **task**: Fast-Whisper 작업 유형 (transcribe: 전사, translate: 영어 번역)
    - **fallback**: 실패시 다른 서비스로 폴백 여부 (기본값: True)
    - **summarization**: ChatGPT API 요약 기능 사용 여부 (기본값: False, 모든 서비스에서 지원)
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
        
        # 데이터베이스에 요청 기록 (파일 경로 포함)
        request_record = None  # 초기화
        try:
            logger.info("💾 데이터베이스에 요청 기록 생성 중...")
            print(f"Attempting to create request record...")
            print(f"DB session: {db}")
            transcription_service = TranscriptionService(db)
            request_record = transcription_service.create_request(
                filename=file.filename,  # 수정됨
                file_size=file_size,
                service_requested=service,
                fallback_enabled=fallback,
                duration=duration,
                client_ip=request.client.host,
                user_agent=request.headers.get("user-agent", "")
            )

            logger.info(f"✅ 요청 기록 생성 완료 - ID: {request_record.request_id}")
            logger.info(f"✅ Created request record with ID: {request_record.request_id}")
            logger.info(f"✅ Created request record with client_ip: {request_record.client_ip}")
                
        except Exception as db_error:
            logger.error(f"❌ 요청 기록 생성 실패: {db_error}")
            print(f"❌ Failed to create request record: {db_error}")
            print(f"Error type: {type(db_error)}")
            import traceback
            traceback.print_exc()
            # 요청 기록 생성 실패 시 HTTP 예외 발생
            raise HTTPException(
                status_code=500, 
                detail="요청 기록 생성에 실패했습니다. 다시 시도해 주세요."
            )        
        
        # 음성 파일을 지정된 경로에 저장 (데이터베이스 기록 전에 수행)
        stored_file_path = None
        try:
            logger.info(f"💾 음성 파일 저장 시작")
            transcription_service = TranscriptionService(db)
            stored_file_path = save_uploaded_file(
                user_uuid="anonymous",
                request_id=request_record.request_id,
                filename=file.filename,
                file_content=file_content
            )
            logger.info(f"✅ 음성 파일 저장 완료 - 경로: {stored_file_path}")
            print(f"✅ Audio file saved to: {stored_file_path}")
            
            # 파일 경로를 /stt_storage/부터의 상대 경로로 변환
            from pathlib import Path
            relative_path = stored_file_path.replace(str(Path.cwd()), "/").replace("\\", "/")
            if relative_path.startswith("//stt_storage"):
                relative_path = relative_path[1:]  # 맨 앞의 / 제거
                
            # 3단계: 파일 경로 업데이트
            transcription_service.update_file_path(
                db=db,
                request_id=request_record.request_id, 
                file_path=relative_path
            )
                
        except Exception as storage_error:
            logger.error(f"❌ 음성 파일 저장 실패: {storage_error}")
            print(f"❌ Failed to save audio file: {storage_error}")
            relative_path = file.filename  # 저장 실패 시 원본 파일명 사용
        
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
                total_processing_time = processing_time + summary_time
                
                # STT 시간 + 요약 시간을 분 단위로 계산
                audio_duration_minutes = round(total_processing_time / 60, 2)
                
                if duration_seconds == 0:
                    duration_seconds = duration

                logger.info(f' duration_seconds 1: {duration_seconds}')
                
                # 토큰 사용량 계산 (1분당 1점)
                # tokens_used = round(audio_duration_minutes * 1.0, 2)
                tokens_used = round(duration_seconds / 60, 2)
                
                # 서비스 제공업체 정보
                service_provider = transcription_result.get('service_name', 'unknown')
                
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
        
        # AssemblyAI 요약이 있는 경우 추가
        if transcription_result.get('summary'):
            response_data["assemblyai_summary"] = transcription_result.get('summary')
            logger.info(f"📝 AssemblyAI 요약 포함됨: {len(transcription_result.get('summary', ''))}자")
                
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

@app.get("/test2")
def test_endpoint():
    print("Test endpoint called")

    current_date = datetime.now()
    last_day = get_last_day_of_month(current_date.year, current_date.month)      
    
    # Get today's date
    today1 = datetime.now().date()
    logger.info(f'today1 -------------- {today1}')

    # Get today's date
    today2 = datetime.today().date()          
    logger.info(f'today2 -------------- {today2}')

    now = datetime.now()
    # formatted_date = now.strftime("%Y-%m-%d %H:%M:%S")
    formatted_date = now.strftime("%d")
    print("포맷된 날짜와 일자:", formatted_date)    

    today = date.today()
    first_day, last_day = calendar.monthrange(current_date.year, current_date.month)
    subscription_day = last_day - today.day + 1
    
    current_date = datetime.now()    
    
    return {"status": "ok", "message": today.month, "message2" : current_date.day}

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

@app.put("/auth/change-password", summary="패스워드 변경")
def change_password(
    password_request: PasswordChangeRequest, 
    current_user: str = Depends(verify_token), 
    db: Session = Depends(get_db)
):
    """
    사용자의 패스워드를 변경합니다.
    
    - **current_password**: 현재 패스워드
    - **new_password**: 새로운 패스워드
    """
    try:
        logger.info(f"🔐 패스워드 변경 요청 - 사용자: {current_user}")
        user_info = get_user(current_user, db=db)
        
        if not user_info:
            logger.warning(f"⚠️ 사용자 정보를 찾을 수 없음: {current_user}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        # 사용자 정보 조회
        user = db.query(User).filter(User.user_uuid == user_info["user_uuid"]).first()
        if not user:
            logger.warning(f"⚠️ 사용자를 찾을 수 없음: {current_user} / {user_info['user_uuid']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        # 현재 패스워드 검증
        if not verify_password(password_request.current_password, user.password_hash):
            logger.warning(f"⚠️ 현재 패스워드 불일치 - 사용자: {current_user}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="현재 패스워드가 올바르지 않습니다."
            )
        
        # 새 패스워드 해시화
        new_password_hash = hash_password(password_request.new_password)
        
        # 패스워드 업데이트
        user.password_hash = new_password_hash
        user.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"✅ 패스워드 변경 완료 - 사용자: {current_user}")
        
        return {
            "status": "success",
            "message": "패스워드가 성공적으로 변경되었습니다.",
            "user_uuid": current_user,
            "updated_at": user.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 패스워드 변경 실패: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="패스워드 변경 중 오류가 발생했습니다."
        )


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
    token_id: str = Depends(get_token_id_dependency),
    db: Session = Depends(get_db)
):
 
    """
    API 키로 보호된 음성 파일을 텍스트로 변환합니다.
    Authorization 헤더에 Bearer {api_key} 형식으로 API 키를 전달해야 합니다.
    음성 파일을 업로드하여 텍스트로 변환합니다.
    다중 STT 서비스(Daglo, Tiro, AssemblyAI, Deepgram, Fast-Whisper)를 지원하며 폴백 기능을 제공합니다.
    요청과 응답 내역이 PostgreSQL에 저장됩니다.
    
    - /transcribe/protected/
    - **file**: 변환할 음성 파일
    - **service**: 사용할 STT 서비스 (daglo, tiro, assemblyai, deepgram, fast-whisper). 미지정시 기본 서비스 사용
    - **model_size**: Fast-Whisper 모델 크기 (tiny, base, small, medium, large-v2, large-v3)
    - **task**: Fast-Whisper 작업 유형 (transcribe: 전사, translate: 영어 번역)
    - **fallback**: 실패시 다른 서비스로 폴백 여부 (기본값: True)
    - **summarization**: ChatGPT API 요약 기능 사용 여부 (기본값: False, 모든 서비스에서 지원)
    """
    
    start_time = time.time()
    transcription_service = TranscriptionService(db)
    api_usage_service = APIUsageService(db)
    
    logger.info(f' token_id --------------1 : {token_id}')
    
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
        
        # 요청 정보 저장 (파일 경로 포함)
        request_record = transcription_service.create_request(
            filename=file.filename,  # 주석 해제 및 수정
            file_size=len(file_content),
            service_requested=service,
            fallback_enabled=fallback,
            client_ip=request.client.host,
            user_agent=request.headers.get("user-agent", ""),
            user_uuid=current_user
        )
        
        # 음성 파일을 지정된 경로에 저장 (요청 정보 저장 전에 수행)
        stored_file_path = None
        try:
            logger.info(f"💾 음성 파일 저장 시작 - 사용자: {current_user}")
            stored_file_path = save_uploaded_file(
                user_uuid=current_user,
                request_id=request_record.request_id,
                filename=file.filename,
                file_content=file_content
            )
            logger.info(f"✅ 음성 파일 저장 완료 - 경로: {stored_file_path}")
            
            # 파일 경로를 /stt_storage/부터의 상대 경로로 변환
            from pathlib import Path
            relative_path = stored_file_path.replace(str(Path.cwd()), "").replace("\\", "/")
            if relative_path.startswith("/"):
                relative_path = relative_path[1:]  # 맨 앞의 / 제거
               
            # 3단계: 파일 경로 업데이트
            transcription_service.update_file_path(
                db=db, 
                request_id=request_record.request_id, 
                file_path=relative_path
            )               
                
        except Exception as storage_error:
            logger.error(f"❌ 음성 파일 저장 실패: {storage_error}")
            relative_path = file.filename  # 저장 실패 시 원본 파일명 사용        
        
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
        # stt_processing_time = result.get("processing_time", processing_time - summary_time)
        duration_seconds = result.get('audio_duration', 0)
        total_processing_time = processing_time + summary_time
        audio_duration_minutes = round(total_processing_time / 60.0, 2)
        
        logger.info(f' duration_seconds1 : {duration_seconds}')
        logger.info(f' audio_duration_minutes : {audio_duration_minutes}')
        
        if duration_seconds == 0:
            duration_seconds = duration

        logger.info(f' duration_seconds 1: {duration_seconds}')
        
        # 토큰 사용량 계산 (1분당 1점)
        tokens_used = round(duration_seconds / 60, 2)
        # tokens_used = round(audio_duration_minutes * 1.0, 2)
        
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
        transcript_id = result.get('transcript_id')
        if transcript_id:
            try:
                logger.info(f"💾 response_rid 업데이트 중 - ID: {request_record.request_id}, RID: {transcript_id}")
                TranscriptionService.update_request_with_rid(db, request_record.request_id, transcript_id)
                logger.info(f"✅ response_rid 업데이트 완료")
            except Exception as rid_error:
                logger.error(f"❌ response_rid 업데이트 실패: {rid_error}")                
        
        logger.info(f"💾 response_rid RID: {transcript_id}")
            
        # 요청 완료 상태로 업데이트
        TranscriptionService.complete_request(
            db=db,
            request_id=request_record.request_id,
            status="completed"
        )
        
        logger.info(f' token_id --------------2 : {token_id}')
        
        # 서비스 토큰 사용량 업데이트 (update lock 방지 처리 포함)
        try:
            from database import update_service_token_usage
            token_update_success = update_service_token_usage(
                db=db,
                user_uuid=current_user,
                token_id=token_id,
                tokens_used=tokens_used,
                request_id=request_record.request_id
            )
            
            if token_update_success:
                logger.info(f"✅ 서비스 토큰 사용량 업데이트 성공 - 사용자: {current_user}, 사용량: {tokens_used}")
            else:
                logger.warning(f"⚠️ 서비스 토큰 사용량 업데이트 실패 - 사용자: {current_user}, 사용량: {tokens_used}")
                
        except Exception as token_error:
            logger.error(f"❌ 서비스 토큰 업데이트 중 오류: {str(token_error)}")
            # 토큰 업데이트 실패해도 STT 처리는 성공으로 처리
        
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
                
                transcript_id = result.get('transcript_id')
                if transcript_id:
                    try:
                        logger.info(f"💾 response_rid 업데이트 중 - ID: {request_record.request_id}, RID: {transcript_id}")
                        TranscriptionService.update_request_with_rid(db, request_record.request_id, transcript_id)
                        logger.info(f"✅ response_rid 업데이트 완료")
                    except Exception as rid_error:
                        logger.error(f"❌ response_rid 업데이트 실패: {rid_error}")                
                
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

# 구독 요금제 관리 API
@app.post("/subscription-plans/", summary="구독 요금제 등록")
def create_subscription_plan(plan: SubscriptionPlanCreate, db: Session = Depends(get_db)):
    """
    새로운 구독 요금제를 등록합니다.
    
    - **plan_code**: 요금제 코드 (예: BASIC, PREMIUM, ENTERPRISE)
    - **plan_description**: 요금제 상세 설명
    - **monthly_price**: 월 구독 금액 (원 단위)
    - **monthly_service_tokens**: 월 제공 서비스 토큰 수
    - **per_minute_rate**: 분당 요금 (선택사항)
    - **overage_per_minute_rate**: 초과분당 요금 (선택사항)
    - **is_active**: 활성화 상태 (기본값: True)
    """
    try:
        logger.info(f"🚀 구독 요금제 등록 시작 - 요금제 코드: {plan.plan_code}")
        
        # 중복 요금제 코드 확인
        existing_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_code == plan.plan_code).first()
        if existing_plan:
            logger.warning(f"⚠️ 중복된 요금제 코드: {plan.plan_code}")
            raise HTTPException(status_code=400, detail=f"요금제 코드 '{plan.plan_code}'가 이미 존재합니다.")
        
        # 새 요금제 생성
        db_plan = SubscriptionPlan(
            plan_code=plan.plan_code,
            plan_description=plan.plan_description,
            monthly_price=plan.monthly_price,
            monthly_service_tokens=plan.monthly_service_tokens,
            per_minute_rate=plan.per_minute_rate,
            overage_per_minute_rate=plan.overage_per_minute_rate,
            is_active=plan.is_active
        )
        
        db.add(db_plan)
        db.commit()
        db.refresh(db_plan)
        
        logger.info(f"✅ 구독 요금제 등록 완료 - ID: {db_plan.id}, 코드: {db_plan.plan_code}")
        
        return {
            "status": "success",
            "message": "구독 요금제가 성공적으로 등록되었습니다.",
            "plan": {
                "id": db_plan.id,
                "plan_code": db_plan.plan_code,
                "plan_description": db_plan.plan_description,
                "monthly_price": db_plan.monthly_price,
                "monthly_service_tokens": db_plan.monthly_service_tokens,
                "per_minute_rate": db_plan.per_minute_rate,
                "overage_per_minute_rate": db_plan.overage_per_minute_rate,
                "is_active": db_plan.is_active,
                "created_at": db_plan.created_at.isoformat() if db_plan.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 구독 요금제 등록 실패: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(status_code=500, detail="구독 요금제 등록 중 오류가 발생했습니다.")

@app.get("/subscription-plans/", summary="구독 요금제 목록 조회")
def get_subscription_plans(active_only: bool = True, db: Session = Depends(get_db)):
    """
    구독 요금제 목록을 조회합니다.
    
    - **active_only**: True인 경우 활성화된 요금제만 조회 (기본값: True)
    """
    try:
        logger.info(f"🔍 구독 요금제 목록 조회 시작 - 활성화만: {active_only}")
        
        query = db.query(SubscriptionPlan)
        if active_only:
            query = query.filter(SubscriptionPlan.is_active == True)
        
        plans = query.order_by(SubscriptionPlan.monthly_price.asc()).all()
        
        plan_list = []
        for plan in plans:
            plan_list.append({
                "id": plan.id,
                "plan_code": plan.plan_code,
                "plan_description": plan.plan_description,
                "monthly_price": plan.monthly_price,
                "monthly_service_tokens": plan.monthly_service_tokens,
                "per_minute_rate": plan.per_minute_rate,
                "overage_per_minute_rate": plan.overage_per_minute_rate,
                "is_active": plan.is_active,
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
                "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
            })
        
        logger.info(f"✅ 구독 요금제 목록 조회 완료 - 총 {len(plan_list)}개")
        
        return {
            "status": "success",
            "message": f"구독 요금제 목록을 성공적으로 조회했습니다. (총 {len(plan_list)}개)",
            "plans": plan_list,
            "total_count": len(plan_list)
        }
        
    except Exception as e:
        logger.error(f"❌ 구독 요금제 목록 조회 실패: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="구독 요금제 목록 조회 중 오류가 발생했습니다.")

@app.get("/subscription-plans/{plan_code}", summary="구독 요금제 상세 조회")
def get_subscription_plan(plan_code: str, db: Session = Depends(get_db)):
    """
    특정 구독 요금제의 상세 정보를 조회합니다.
    
    - **plan_code**: 조회할 요금제코드
    """
    try:
        logger.info(f"🔍 구독 요금제 상세 조회 시작 - CODE: {plan_code}")
        
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_code == plan_code).first()
        if not plan:
            logger.warning(f"⚠️ 요금제를 찾을 수 없음 - CODE: {plan_code}")
            raise HTTPException(status_code=404, detail=f"요금제 코드 '{plan_code}'를 찾을 수 없습니다.")
        
        logger.info(f"✅ 구독 요금제 상세 조회 완료 - 코드: {plan.plan_code}")
        
        return {
            "status": "success",
            "message": "구독 요금제 정보를 성공적으로 조회했습니다.",
            "plan": {
                "id": plan.id,
                "plan_code": plan.plan_code,
                "plan_description": plan.plan_description,
                "monthly_price": plan.monthly_price,
                "monthly_service_tokens": plan.monthly_service_tokens,
                "per_minute_rate": plan.per_minute_rate,
                "overage_per_minute_rate": plan.overage_per_minute_rate,
                "is_active": plan.is_active,
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
                "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 구독 요금제 상세 조회 실패: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="구독 요금제 조회 중 오류가 발생했습니다.")

@app.put("/subscription-plans/{plan_code}", summary="구독 요금제 수정")
def update_subscription_plan(plan_code: str, plan_update: SubscriptionPlanUpdate, db: Session = Depends(get_db)):
    """
    기존 구독 요금제 정보를 수정합니다.
    
    - **plan_code**: 수정할 요금제 코드
    - 수정할 필드만 제공하면 됩니다 (부분 업데이트 지원)
    """
    try:
        logger.info(f"🔧 구독 요금제 수정 시작 - CODE: {plan_code}")
        
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_code == plan_code).first()
        if not plan:
            logger.warning(f"⚠️ 요금제를 찾을 수 없음 - CODE: {plan_code}")
            raise HTTPException(status_code=404, detail=f"요금제 코드 '{plan_code}'를 찾을 수 없습니다.")
        
        # 수정할 필드만 업데이트
        update_data = plan_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(plan, field, value)
        
        db.commit()
        db.refresh(plan)
        
        logger.info(f"✅ 구독 요금제 수정 완료 - 코드: {plan.plan_code}")
        
        return {
            "status": "success",
            "message": "구독 요금제가 성공적으로 수정되었습니다.",
            "plan": {
                "id": plan.id,
                "plan_code": plan.plan_code,
                "plan_description": plan.plan_description,
                "monthly_price": plan.monthly_price,
                "monthly_service_tokens": plan.monthly_service_tokens,
                "per_minute_rate": plan.per_minute_rate,
                "overage_per_minute_rate": plan.overage_per_minute_rate,
                "is_active": plan.is_active,
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
                "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 구독 요금제 수정 실패: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(status_code=500, detail="구독 요금제 수정 중 오류가 발생했습니다.")

@app.delete("/subscription-plans/{plan_code}", summary="구독 요금제 삭제")
def delete_subscription_plan(plan_code: str, db: Session = Depends(get_db)):
    """
    구독 요금제를 삭제합니다.
    
    - **plan_code**: 삭제할 요금제코드
    - 실제로는 is_active를 False로 설정하여 비활성화합니다 (소프트 삭제)
    """
    try:
        logger.info(f"🗑️ 구독 요금제 삭제 시작 - CODE: {plan_code}")
        
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_code == plan_code).first()
        if not plan:
            logger.warning(f"⚠️ 요금제를 찾을 수 없음 - CODE: {plan_code}")
            raise HTTPException(status_code=404, detail=f"요금제 코드 '{plan_code}'를 찾을 수 없습니다.")
        
        # 소프트 삭제 (is_active를 False로 설정)
        plan.is_active = False
        db.commit()
        
        logger.info(f"✅ 구독 요금제 삭제 완료 - 코드: {plan.plan_code}")
        
        return {
            "status": "success",
            "message": "구독 요금제가 성공적으로 삭제되었습니다.",
            "plan_code": plan.plan_code
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 구독 요금제 삭제 실패: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(status_code=500, detail="구독 요금제 삭제 중 오류가 발생했습니다.")


# 결제 관련 API 엔드포인트들
@app.post("/payments/", summary="구독 결제 생성")
def create_payment(
    payment: PaymentCreate, 
    subscription_type: str = Query(..., description="Subscription type (NEW, SUBSCRIPTION)"),
    current_user: str = Depends(verify_token), 
    db: Session = Depends(get_db)
):
    """
    요금제 코드와 인원수를 입력하여 구독 결제를 생성합니다.
    
    - /payments/
    - **plan_code**: 요금제 코드 (예: BASIC, PREMIUM, ENTERPRISE)
    - **quantity**: 인원수 (기본값: 1)
    - **subscription_type**: 구독 형태 (예: NEW, SUBSCRIPTION)
    - **payment_method**: 결제 수단 (선택사항)
    - **payment_type**: 결제 구분 (기본값: subscription)
    - **external_payment_id**: 외부 결제 시스템 ID (선택사항)
    """
    try:
        # current_user는 user_id이므로 user_uuid를 조회해야 함
        user_info = get_user(current_user, db=db)
        if not user_info:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        user_uuid = user_info["user_uuid"]
        logger.info(f"🚀 구독 결제 생성 시작 - 사용자: {user_uuid}, 요금제: {payment.plan_code}, 인원수: {payment.quantity}")
        
        # 요금제 정보 조회
        subscription_plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.plan_code == payment.plan_code,
            SubscriptionPlan.is_active == True
        ).first()
        
        if not subscription_plan:
            logger.warning(f"⚠️ 요금제를 찾을 수 없음 - 코드: {payment.plan_code}")
            raise HTTPException(status_code=404, detail=f"요금제 코드 '{payment.plan_code}'를 찾을 수 없거나 비활성화되었습니다.")
        
        # Check if subscription master already exists
        # existing_subscription_master = db.query(SubscriptionMaster).filter(
        #    SubscriptionMaster.user_uuid == user_uuid,
        #    SubscriptionMaster.subscription_status == 'active'
        # ).first()

        current_date = datetime.now()
        unit_price = subscription_plan.monthly_price  # 단가 (월 구독 금액)
        supply_amount = unit_price * payment.quantity  # 공급가액 = 단가 × 인원수
        quota_tokens = subscription_plan.monthly_service_tokens * payment.quantity
        last_day = calendar.monthrange(current_date.year, current_date.month)[1]

        # 구독 일자
        subscription_start_date = datetime.now().date()
        subscription_end_date = datetime(current_date.year, current_date.month, last_day, 23, 59, 59)

        # 다음 청구일
        next_billing_date = subscription_end_date + timedelta(days=1)
        next_billing_date = datetime(next_billing_date.year, next_billing_date.month, next_billing_date.day, 0, 0, 0)
        quantity = payment.quantity
        
        logger.info(f"구독 계산1 - ubscription_plan.monthly_service_tokens : {subscription_plan.monthly_service_tokens} ")
        

        # 구독
        if "NEW" == subscription_type:
            # 신규 구독 기간 계산
            subscription_day = last_day - current_date.day + 1
            logger.info(f"구독 계산0 - subscription_day : {subscription_day}, last_day: {last_day}")
            subscription_amount_day = supply_amount / last_day
            logger.info(f"구독 계산0-1 - subscription_amount_day : {subscription_amount_day}, last_day: {last_day}")
            supply_amount_month = subscription_day * subscription_amount_day
            logger.info(f"구독 계산0-1 - supply_amount_month : {supply_amount_month}")

            supply_amount = int(supply_amount_month)
            quantity = int(supply_amount / unit_price)
            quota_tokens_day = quota_tokens / last_day
            quota_tokens = int(quota_tokens_day * subscription_day)            # 금액 계산
            logger.info(f"구독 계산1 - quota_tokens : {quota_tokens}, supply_amount: {supply_amount}, quantity: {quantity}, last_day: {last_day}, subscription_day: {subscription_day}, quota_tokens_day : {quota_tokens_day} ")
        
        else :
            vat_amount = int(supply_amount * 0.1)  # 부가세 10%
            total_amount = supply_amount + vat_amount  # 총 금액
            subscription_start_date = datetime(subscription_start_date.year, subscription_start_date.month, subscription_start_date.day, 0, 0, 0)
            
        logger.info(f"구독 계산2 - quota_tokens: {quota_tokens} ")

        vat_amount = int(supply_amount * 0.1)  # 부가세 10%
        total_amount = supply_amount + vat_amount  # 총 금액 
        
        logger.info(f"💰 금액 계산 완료 - 단가: {unit_price:,}원, 인원수: {quantity}, 공급가액: {supply_amount:,}원, 부가세: {vat_amount:,}원, 총액: {total_amount:,}원")
        
        # 새 결제 생성
        new_payment = Payment(
            user_uuid=user_uuid,
            plan_code=payment.plan_code,
            supply_amount=supply_amount,
            vat_amount=vat_amount,
            total_amount=total_amount,
            payment_method=payment.payment_method,
            payment_type=payment.payment_type,
            external_payment_id=payment.external_payment_id
        )
        
        db.add(new_payment)
        db.commit()
        db.refresh(new_payment)
        
        # 구독 결제 상세 정보 생성
        subscription_payment = SubscriptionPayment(
            payment_id=new_payment.payment_id,
            plan_code=payment.plan_code,
            unit_price=unit_price,
            quantity=quantity,
            amount=supply_amount
        )
        
        db.add(subscription_payment)
        db.commit()
        db.refresh(subscription_payment)
        

        # 서비스 토큰 생성 (구독할당토큰 = 월제공서비스토큰수 × 인원수)
        # quota_tokens = subscription_plan.monthly_service_tokens * payment.quantity
        
        # 토큰 만료일 설정 (결제일로부터 1개월 후)
        # from datetime import datetime, timedelta
        # token_expiry_date = (datetime.now() + timedelta(days=30)).date()
        
        # 토큰 ID 생성 (payment_id 기반)
        token_id = f"TOKEN_{new_payment.payment_id}"
        
        logger.info(f"🎫 서비스 토큰 생성 시작 - 할당토큰: {quota_tokens}, 만료일: {subscription_end_date}")
        
        # service_tokens update 로 수정

        # Check if service token already exists and delete if found
        existing_token = db.query(ServiceToken).filter(
            ServiceToken.user_uuid == user_uuid
        ).first()
        
        # 구독 신규
        if "NEW" == subscription_type: 

            if existing_token:
                logger.info(f"Found existing active service token for user {user_uuid} - deleting")
                db.delete(existing_token)
                db.commit()
                logger.info("Existing token deleted successfully")
            
            # 서비스 토큰 레코드 생성
            service_token = ServiceToken(
                user_uuid=user_uuid,
                quota_tokens=quota_tokens,
                used_tokens=0.0,  # 초기값은 0으로 설정
                token_expiry_date=subscription_end_date,
                status='active'
            )
            
            db.add(service_token)
            db.commit()
            db.refresh(service_token)
        
        # 기존 구독
        else :
            
            if existing_token:
                # Get existing token
                existing_token.quota_tokens = quota_tokens
                existing_token.used_tokens = 0.0
                existing_token.token_expiry_date = subscription_end_date
                existing_token.status = "active"
                existing_token.updated_at = datetime.now()
                db.commit()
                db.refresh(existing_token)

            else :
                # 서비스 토큰 레코드 생성
                service_token = ServiceToken(
                    user_uuid=user_uuid,
                    quota_tokens=quota_tokens,
                    used_tokens=0.0,  # 초기값은 0으로 설정
                    token_expiry_date=subscription_end_date,
                    status='active'
                )
                
                db.add(service_token)
                db.commit()
                db.refresh(service_token)
            
        
        # 구독 마스터 생성 (신규 구독)
        # subscription_end_date = subscription_start_date + timedelta(days=30)  # 1개월 후
        
        logger.info(f"📋 구독 마스터 생성 시작 - 시작일: {subscription_start_date}, 종료일: {subscription_end_date}")
        
        # SubscriptionMaster 수정
        # 기존 활성 구독이 있는지 확인
        existing_subscription = db.query(SubscriptionMaster).filter(
            SubscriptionMaster.user_uuid == user_uuid,
            SubscriptionMaster.subscription_status == 'active'
        ).first()
        
        if existing_subscription:
            # 기존 구독을 취소 상태로 변경
            # existing_subscription.subscription_status = 'cancelled'
            # existing_subscription.subscription_end_date = subscription_start_date
            # logger.info(f"⚠️ 기존 활성 구독 취소 - 구독ID: {existing_subscription.subscription_id}")
            logger.info(f"Found existing active Subscription Master for user {user_uuid} - deleting")
            db.delete(existing_subscription)
            db.commit()
            logger.info("Existing token deleted successfully")
        
        # 구독 ID 생성
        import uuid
        subscription_id = str(uuid.uuid4())

        supply_amount = unit_price * payment.quantity  # 공급가액 = 단가 × 인원수
        
        # 새 구독 마스터 생성
        new_subscription = SubscriptionMaster(
            user_uuid=user_uuid,
            subscription_id=subscription_id,
            plan_code=payment.plan_code,
            unit_price=unit_price,
            quantity=payment.quantity,
            amount=supply_amount,
            quota_tokens=quota_tokens,
            subscription_status='active',
            subscription_start_date=subscription_start_date,
            subscription_end_date=subscription_end_date,
            next_billing_date=next_billing_date,
            auto_renewal=True,
            renewal_plan_code=payment.plan_code
        )

        db.add(new_subscription)
        db.commit()
        db.refresh(new_subscription)
        
        # 구독 변경 이력 생성 (신규 구독)
        subscription_change = SubscriptionChangeHistory(
            user_uuid=user_uuid,
            subscription_id=new_subscription.subscription_id,
            change_id=f"CHG_{current_user}_{int(datetime.now().timestamp())}_{str(uuid.uuid4())[:8]}",
            change_type='create',
            change_reason='신규 구독 생성',
            previous_plan_code=None,
            new_plan_code=payment.plan_code,
            previous_status=None,
            new_status='active',
            effective_date=subscription_start_date,
            change_requested_at=datetime.now(),
            proration_amount=0,
            refund_amount=0,
            additional_charge=total_amount,
            processed_by='system',
            admin_notes=f"결제ID: {new_payment.payment_id}를 통한 신규 구독 생성"
        )
        
        db.add(subscription_change)
        db.commit()
        db.refresh(subscription_change)
        
        logger.info(f"✅ 구독 결제, 서비스 토큰, 구독 마스터 생성 완료 - 결제번호: {new_payment.payment_id}, 토큰ID: {token_id}, 구독ID: {new_subscription.subscription_id}")
        
        return {
            "status": "success",
            "message": "구독 결제, 서비스 토큰 및 구독 마스터가 성공적으로 생성되었습니다.",
            "data": {
                "payment_id": new_payment.payment_id,
                "user_uuid": new_payment.user_uuid,
                "plan_code": new_payment.plan_code,
                "plan_description": subscription_plan.plan_description,
                "unit_price": unit_price,
                "quantity": payment.quantity,
                "supply_amount": supply_amount,
                "vat_amount": vat_amount,
                "total_amount": total_amount,
                "payment_status": new_payment.payment_status,
                "service_token": {
                    "token_id": token_id,
                    "quota_tokens": quota_tokens,
                    "token_expiry_date": subscription_end_date.isoformat(),
                    "status": "active"
                },
                "subscription": {
                    "subscription_id": new_subscription.subscription_id,
                    "subscription_status": new_subscription.subscription_status,
                    "subscription_start_date": new_subscription.subscription_start_date.isoformat(),
                    "subscription_end_date": new_subscription.subscription_end_date.isoformat(),
                    "next_billing_date": new_subscription.next_billing_date.isoformat(),
                    "auto_renewal": new_subscription.auto_renewal,
                    "renewal_plan_code": new_subscription.renewal_plan_code
                },
                "created_at": new_payment.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 구독 결제 생성 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(status_code=500, detail="구독 결제 생성 중 오류가 발생했습니다.")

@app.get("/payments/", summary="결제 목록 조회")
def get_payments(limit: int = 50, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    현재 사용자의 결제 목록을 조회합니다.
    
    - **limit**: 조회할 최대 건수 (기본값: 50)
    """
    try:
        # current_user는 user_id이므로 user_uuid를 조회해야 함
        user_info = get_user(current_user, db=db)
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_uuid = user_info["user_uuid"]
        logger.info(f"🔍 결제 목록 조회 시작 - 사용자: {user_uuid}, 제한: {limit}")
        
        query = db.query(Payment).filter(Payment.user_uuid == user_uuid)
            
        payments = query.order_by(Payment.created_at.desc()).limit(limit).all()
        
        payment_list = []
        for payment in payments:
            payment_list.append({
                "payment_id": payment.payment_id,
                "user_uuid": payment.user_uuid,
                "plan_code": payment.plan_code,
                "supply_amount": payment.supply_amount,
                "vat_amount": payment.vat_amount,
                "total_amount": payment.total_amount,
                "payment_status": payment.payment_status,
                "payment_method": payment.payment_method,
                "payment_type": payment.payment_type,
                "external_payment_id": payment.external_payment_id,
                "created_at": payment.created_at.isoformat(),
                "updated_at": payment.updated_at.isoformat() if payment.updated_at else None,
                "completed_at": payment.completed_at.isoformat() if payment.completed_at else None
            })
        
        logger.info(f"✅ 결제 목록 조회 완료 - 총 {len(payment_list)}건")
        
        return {
            "status": "success",
            "message": f"결제 목록을 성공적으로 조회했습니다. (총 {len(payment_list)}건)",
            "data": payment_list
        }
        
    except Exception as e:
        logger.error(f"❌ 결제 목록 조회 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="결제 목록 조회 중 오류가 발생했습니다."
        )

@app.get("/payments/{payment_id}", summary="결제 상세 조회")
def get_payment(payment_id: str, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    특정 결제의 상세 정보를 조회합니다.
    
    - **payment_id**: 조회할 결제 번호
    """
    try:
        logger.info(f"🔍 결제 상세 조회 시작 - 결제번호: {payment_id}")
        
        payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
        
        if not payment:
            logger.warning(f"⚠️ 결제를 찾을 수 없음 - 결제번호: {payment_id}")
            raise HTTPException(
                status_code=404,
                detail="해당 결제를 찾을 수 없습니다."
            )
        
        logger.info(f"✅ 결제 상세 조회 완료 - 결제번호: {payment_id}")
        
        return {
            "status": "success",
            "message": "결제 정보를 성공적으로 조회했습니다.",
            "data": {
                "payment_id": payment.payment_id,
                "user_uuid": payment.user_uuid,
                "plan_code": payment.plan_code,
                "supply_amount": payment.supply_amount,
                "vat_amount": payment.vat_amount,
                "total_amount": payment.total_amount,
                "payment_status": payment.payment_status,
                "payment_method": payment.payment_method,
                "payment_type": payment.payment_type,
                "external_payment_id": payment.external_payment_id,
                "created_at": payment.created_at.isoformat(),
                "updated_at": payment.updated_at.isoformat() if payment.updated_at else None,
                "completed_at": payment.completed_at.isoformat() if payment.completed_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 결제 상세 조회 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="결제 상세 조회 중 오류가 발생했습니다."
        )

@app.put("/payments/{payment_id}", summary="결제 정보 수정")
def update_payment(payment_id: str, payment_update: PaymentUpdate, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    결제 정보를 수정합니다.
    
    - **payment_id**: 수정할 결제 번호
    - **payment_status**: 결제 상태 (선택사항)
    - **payment_method**: 결제 수단 (선택사항)
    - **external_payment_id**: 외부 결제 시스템 ID (선택사항)
    """
    try:
        logger.info(f"🔄 결제 정보 수정 시작 - 결제번호: {payment_id}")
        
        payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
        
        if not payment:
            logger.warning(f"⚠️ 결제를 찾을 수 없음 - 결제번호: {payment_id}")
            raise HTTPException(
                status_code=404,
                detail="해당 결제를 찾을 수 없습니다."
            )
        
        # 수정할 필드들 업데이트
        if payment_update.payment_status is not None:
            payment.payment_status = payment_update.payment_status
            if payment_update.payment_status == "completed":
                from datetime import datetime
                payment.completed_at = datetime.now()
                
        if payment_update.payment_method is not None:
            payment.payment_method = payment_update.payment_method
            
        if payment_update.external_payment_id is not None:
            payment.external_payment_id = payment_update.external_payment_id
        
        db.commit()
        db.refresh(payment)
        
        logger.info(f"✅ 결제 정보 수정 완료 - 결제번호: {payment_id}")
        
        return {
            "status": "success",
            "message": "결제 정보가 성공적으로 수정되었습니다.",
            "data": {
                "payment_id": payment.payment_id,
                "user_uuid": payment.user_uuid,
                "plan_code": payment.plan_code,
                "total_amount": payment.total_amount,
                "payment_status": payment.payment_status,
                "payment_method": payment.payment_method,
                "external_payment_id": payment.external_payment_id,
                "updated_at": payment.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 결제 정보 수정 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="결제 정보 수정 중 오류가 발생했습니다."
        )


# 구독 결제 관리 API 엔드포인트들
@app.post("/subscription-payments/", summary="구독 결제 생성")
def create_subscription_payment(subscription_payment: SubscriptionPaymentCreate, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    새로운 구독 결제를 생성합니다.
    
    - **payment_id**: 결제 번호
    - **plan_code**: 요금제 코드
    - **unit_price**: 단가
    - **quantity**: 수량 (기본값: 1)
    - **amount**: 금액
    """
    try:
        logger.info(f"🚀 구독 결제 생성 시작 - 결제번호: {subscription_payment.payment_id}, 요금제: {subscription_payment.plan_code}")
        
        # 결제 정보 확인
        payment = db.query(Payment).filter(Payment.payment_id == subscription_payment.payment_id).first()
        if not payment:
            logger.warning(f"⚠️ 결제를 찾을 수 없음 - 결제번호: {subscription_payment.payment_id}")
            raise HTTPException(
                status_code=404,
                detail="해당 결제를 찾을 수 없습니다."
            )
        
        # 새 구독 결제 생성
        new_subscription_payment = SubscriptionPayment(
            payment_id=subscription_payment.payment_id,
            plan_code=subscription_payment.plan_code,
            unit_price=subscription_payment.unit_price,
            quantity=subscription_payment.quantity,
            amount=subscription_payment.amount
        )
        
        db.add(new_subscription_payment)
        db.commit()
        db.refresh(new_subscription_payment)
        
        logger.info(f"✅ 구독 결제 생성 완료 - ID: {new_subscription_payment.id}")
        
        return {
            "status": "success",
            "message": "구독 결제가 성공적으로 생성되었습니다.",
            "data": {
                "id": new_subscription_payment.id,
                "payment_id": new_subscription_payment.payment_id,
                "plan_code": new_subscription_payment.plan_code,
                "unit_price": new_subscription_payment.unit_price,
                "quantity": new_subscription_payment.quantity,
                "amount": new_subscription_payment.amount,
                "created_at": new_subscription_payment.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 구독 결제 생성 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="구독 결제 생성 중 오류가 발생했습니다."
        )

@app.get("/subscription-payments/", summary="구독 결제 목록 조회")
def get_subscription_payments(payment_id: Optional[str] = None, plan_code: Optional[str] = None, limit: int = 50, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    구독 결제 목록을 조회합니다.
    
    - **payment_id**: 특정 결제의 구독 결제만 조회 (선택사항)
    - **plan_code**: 특정 요금제의 구독 결제만 조회 (선택사항)
    - **limit**: 조회할 최대 건수 (기본값: 50)
    """
    try:
        logger.info(f"🔍 구독 결제 목록 조회 시작 - 결제번호: {payment_id}, 요금제: {plan_code}, 제한: {limit}")
        
        query = db.query(SubscriptionPayment)
        
        if payment_id:
            query = query.filter(SubscriptionPayment.payment_id == payment_id)
        if plan_code:
            query = query.filter(SubscriptionPayment.plan_code == plan_code)
            
        subscription_payments = query.order_by(SubscriptionPayment.created_at.desc()).limit(limit).all()
        
        subscription_payment_list = []
        for sp in subscription_payments:
            subscription_payment_list.append({
                "id": sp.id,
                "payment_id": sp.payment_id,
                "plan_code": sp.plan_code,
                "unit_price": sp.unit_price,
                "quantity": sp.quantity,
                "amount": sp.amount,
                "created_at": sp.created_at.isoformat(),
                "updated_at": sp.updated_at.isoformat() if sp.updated_at else None
            })
        
        logger.info(f"✅ 구독 결제 목록 조회 완료 - 총 {len(subscription_payment_list)}건")
        
        return {
            "status": "success",
            "message": f"구독 결제 목록을 성공적으로 조회했습니다. (총 {len(subscription_payment_list)}건)",
            "data": subscription_payment_list
        }
        
    except Exception as e:
        logger.error(f"❌ 구독 결제 목록 조회 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="구독 결제 목록 조회 중 오류가 발생했습니다."
        )

@app.get("/subscription-payments/{subscription_payment_id}", summary="구독 결제 상세 조회")
def get_subscription_payment(subscription_payment_id: int, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    특정 구독 결제의 상세 정보를 조회합니다.
    
    - **subscription_payment_id**: 조회할 구독 결제 ID
    """
    try:
        logger.info(f"🔍 구독 결제 상세 조회 시작 - ID: {subscription_payment_id}")
        
        subscription_payment = db.query(SubscriptionPayment).filter(SubscriptionPayment.id == subscription_payment_id).first()
        
        if not subscription_payment:
            logger.warning(f"⚠️ 구독 결제를 찾을 수 없음 - ID: {subscription_payment_id}")
            raise HTTPException(
                status_code=404,
                detail="해당 구독 결제를 찾을 수 없습니다."
            )
        
        logger.info(f"✅ 구독 결제 상세 조회 완료 - ID: {subscription_payment_id}")
        
        return {
            "status": "success",
            "message": "구독 결제 정보를 성공적으로 조회했습니다.",
            "data": {
                "id": subscription_payment.id,
                "payment_id": subscription_payment.payment_id,
                "plan_code": subscription_payment.plan_code,
                "unit_price": subscription_payment.unit_price,
                "quantity": subscription_payment.quantity,
                "amount": subscription_payment.amount,
                "created_at": subscription_payment.created_at.isoformat(),
                "updated_at": subscription_payment.updated_at.isoformat() if subscription_payment.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 구독 결제 상세 조회 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="구독 결제 상세 조회 중 오류가 발생했습니다."
        )

# 토큰 결제 관리 API 엔드포인트들
@app.post("/token-payments/", summary="토큰 결제 생성")
def create_token_payment(token_payment: TokenPaymentCreate, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    새로운 토큰 결제를 생성합니다.
    
    - **payment_id**: 결제 번호
    - **token_quantity**: 토큰 수량
    - **token_unit_price**: 토큰 단가
    - **amount**: 금액
    """
    try:
        logger.info(f"🚀 토큰 결제 생성 시작 - 결제번호: {token_payment.payment_id}, 토큰수량: {token_payment.token_quantity}")
        
        # 결제 정보 확인
        payment = db.query(Payment).filter(Payment.payment_id == token_payment.payment_id).first()
        if not payment:
            logger.warning(f"⚠️ 결제를 찾을 수 없음 - 결제번호: {token_payment.payment_id}")
            raise HTTPException(
                status_code=404,
                detail="해당 결제를 찾을 수 없습니다."
            )
        
        # 새 토큰 결제 생성
        new_token_payment = TokenPayment(
            payment_id=token_payment.payment_id,
            token_quantity=token_payment.token_quantity,
            token_unit_price=token_payment.token_unit_price,
            amount=token_payment.amount
        )
        
        db.add(new_token_payment)
        db.commit()
        db.refresh(new_token_payment)
        
        logger.info(f"✅ 토큰 결제 생성 완료 - ID: {new_token_payment.id}")
        
        return {
            "status": "success",
            "message": "토큰 결제가 성공적으로 생성되었습니다.",
            "data": {
                "id": new_token_payment.id,
                "payment_id": new_token_payment.payment_id,
                "token_quantity": new_token_payment.token_quantity,
                "token_unit_price": new_token_payment.token_unit_price,
                "amount": new_token_payment.amount,
                "created_at": new_token_payment.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 토큰 결제 생성 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="토큰 결제 생성 중 오류가 발생했습니다."
        )

@app.get("/token-payments/", summary="토큰 결제 목록 조회")
def get_token_payments(payment_id: Optional[str] = None, limit: int = 50, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    토큰 결제 목록을 조회합니다.
    
    - **payment_id**: 특정 결제의 토큰 결제만 조회 (선택사항)
    - **limit**: 조회할 최대 건수 (기본값: 50)
    """
    try:
        logger.info(f"🔍 토큰 결제 목록 조회 시작 - 결제번호: {payment_id}, 제한: {limit}")
        
        query = db.query(TokenPayment)
        
        if payment_id:
            query = query.filter(TokenPayment.payment_id == payment_id)
            
        token_payments = query.order_by(TokenPayment.created_at.desc()).limit(limit).all()
        
        token_payment_list = []
        for tp in token_payments:
            token_payment_list.append({
                "id": tp.id,
                "payment_id": tp.payment_id,
                "token_quantity": tp.token_quantity,
                "token_unit_price": tp.token_unit_price,
                "amount": tp.amount,
                "created_at": tp.created_at.isoformat(),
                "updated_at": tp.updated_at.isoformat() if tp.updated_at else None
            })
        
        logger.info(f"✅ 토큰 결제 목록 조회 완료 - 총 {len(token_payment_list)}건")
        
        return {
            "status": "success",
            "message": f"토큰 결제 목록을 성공적으로 조회했습니다. (총 {len(token_payment_list)}건)",
            "data": token_payment_list
        }
        
    except Exception as e:
        logger.error(f"❌ 토큰 결제 목록 조회 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="토큰 결제 목록 조회 중 오류가 발생했습니다."
        )


# 서비스 토큰 관리 API 엔드포인트들
@app.post("/service-tokens/", summary="서비스 토큰 생성")
def create_service_token(service_token: ServiceTokenCreate, 
                         current_user: str = Depends(verify_token), 
                         db: Session = Depends(get_db)):

    """
    새로운 서비스 토큰을 생성합니다.
    
    - **user_uuid**: 사용자 UUID
    - **token_type**: 토큰 타입 (subscription, prepaid)
    - **plan_code**: 요금제 코드 (구독형인 경우)
    - **total_tokens**: 총 토큰 수량
    - **used_tokens**: 사용된 토큰 수량 (기본값: 0)
    - **expires_at**: 만료일시
    """
    try:
        logger.info(f"🚀 서비스 토큰 생성 시작 - 사용자: {service_token.user_uuid}")
        
        # 사용자 확인
        user = db.query(User).filter(User.user_uuid == service_token.user_uuid).first()
        if not user:
            logger.warning(f"⚠️ 사용자를 찾을 수 없음 - UUID: {service_token.user_uuid}")
            raise HTTPException(
                status_code=404,
                detail="해당 사용자를 찾을 수 없습니다."
            )
        
        # 새 서비스 토큰 생성
        new_service_token = ServiceToken(
            user_uuid=service_token.user_uuid,
            quota_tokens=service_token.quota_tokens,
            used_tokens=Decimal('0.0'),  # Decimal 타입으로 초기값 설정
            token_expiry_date=service_token.token_expiry_date,
            status=service_token.status
        )
        
        db.add(new_service_token)
        db.commit()
        db.refresh(new_service_token)
        
        logger.info(f"✅ 서비스 토큰 생성 완료 - ID: {new_service_token.id}")
        
        return {
            "status": "success",
            "message": "서비스 토큰이 성공적으로 생성되었습니다.",
            "data": {
                "id": new_service_token.id,
                "user_uuid": new_service_token.user_uuid,
                "quota_tokens": new_service_token.quota_tokens,
                "used_tokens": new_service_token.used_tokens,
                "remaining_tokens": new_service_token.quota_tokens - new_service_token.used_tokens,
                "token_expiry_date": new_service_token.token_expiry_date,
                "status": new_service_token.status,
                "created_at": new_service_token.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 서비스 토큰 생성 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="서비스 토큰 생성 중 오류가 발생했습니다."
        )

@app.get("/service-tokens/", summary="서비스 토큰 목록 조회")
def get_service_tokens(user_uuid: Optional[str] = None, token_type: Optional[str] = None, plan_code: Optional[str] = None, limit: int = 50, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    서비스 토큰 목록을 조회합니다.
    
    - **user_uuid**: 특정 사용자의 토큰만 조회 (선택사항)
    - **token_type**: 특정 타입의 토큰만 조회 (선택사항)
    - **plan_code**: 특정 요금제의 토큰만 조회 (선택사항)
    - **limit**: 조회할 최대 건수 (기본값: 50)
    """
    try:
        logger.info(f"🔍 서비스 토큰 목록 조회 시작 - 사용자: {user_uuid}, 타입: {token_type}, 요금제: {plan_code}, 제한: {limit}")
        
        query = db.query(ServiceToken)
        
        if user_uuid:
            query = query.filter(ServiceToken.user_uuid == user_uuid)
        if token_type:
            query = query.filter(ServiceToken.token_type == token_type)
        if plan_code:
            query = query.filter(ServiceToken.plan_code == plan_code)
            
        service_tokens = query.order_by(ServiceToken.created_at.desc()).limit(limit).all()
        
        service_token_list = []
        for st in service_tokens:
            service_token_list.append({
                "id": st.id,
                "user_uuid": st.user_uuid,
                "quota_tokens": st.quota_tokens,
                "used_tokens": st.used_tokens,
                "remaining_tokens": st.quota_tokens - st.used_tokens,
                "token_expiry_date": st.token_expiry_date,
                "status": st.status,
                "created_at": st.created_at.isoformat(),
                "updated_at": st.updated_at.isoformat() if st.updated_at else None
            })
        
        logger.info(f"✅ 서비스 토큰 목록 조회 완료 - 총 {len(service_token_list)}건")
        
        return {
            "status": "success",
            "message": f"서비스 토큰 목록을 성공적으로 조회했습니다. (총 {len(service_token_list)}건)",
            "data": service_token_list
        }
        
    except Exception as e:
        logger.error(f"❌ 서비스 토큰 목록 조회 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="서비스 토큰 목록 조회 중 오류가 발생했습니다."
        )

@app.get("/service-tokens/{service_token_id}", summary="서비스 토큰 상세 조회")
def get_service_token(service_token_id: int, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    특정 서비스 토큰의 상세 정보를 조회합니다.
    
    - **service_token_id**: 조회할 서비스 토큰 ID
    """
    try:
        logger.info(f"🔍 서비스 토큰 상세 조회 시작 - ID: {service_token_id}")
        
        service_token = db.query(ServiceToken).filter(ServiceToken.id == service_token_id).first()
        
        if not service_token:
            logger.warning(f"⚠️ 서비스 토큰을 찾을 수 없음 - ID: {service_token_id}")
            raise HTTPException(
                status_code=404,
                detail="해당 서비스 토큰을 찾을 수 없습니다."
            )
        
        logger.info(f"✅ 서비스 토큰 상세 조회 완료 - ID: {service_token_id}")
        
        return {
            "status": "success",
            "message": "서비스 토큰 정보를 성공적으로 조회했습니다.",
            "data": {
                "id": service_token.id,
                "user_uuid": service_token.user_uuid,
                "token_type": service_token.token_type,
                "plan_code": service_token.plan_code,
                "total_tokens": service_token.total_tokens,
                "used_tokens": service_token.used_tokens,
                "remaining_tokens": service_token.total_tokens - service_token.used_tokens,
                "expires_at": service_token.expires_at.isoformat() if service_token.expires_at else None,
                "created_at": service_token.created_at.isoformat(),
                "updated_at": service_token.updated_at.isoformat() if service_token.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 서비스 토큰 상세 조회 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="서비스 토큰 상세 조회 중 오류가 발생했습니다."
        )

@app.put("/service-tokens/{service_token_id}", summary="서비스 토큰 업데이트")
def update_service_token(service_token_id: int, service_token_update: ServiceTokenUpdate, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    서비스 토큰 정보를 업데이트합니다.
    
    - **service_token_id**: 업데이트할 서비스 토큰 ID
    - **total_tokens**: 총 토큰 수량 (선택사항)
    - **used_tokens**: 사용된 토큰 수량 (선택사항)
    - **expires_at**: 만료일시 (선택사항)
    """
    try:
        logger.info(f"🔄 서비스 토큰 업데이트 시작 - ID: {service_token_id}")
        
        service_token = db.query(ServiceToken).filter(ServiceToken.id == service_token_id).first()
        
        if not service_token:
            logger.warning(f"⚠️ 서비스 토큰을 찾을 수 없음 - ID: {service_token_id}")
            raise HTTPException(
                status_code=404,
                detail="해당 서비스 토큰을 찾을 수 없습니다."
            )
        
        # 업데이트할 필드들 처리
        update_data = service_token_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(service_token, field, value)
        
        service_token.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(service_token)
        
        logger.info(f"✅ 서비스 토큰 업데이트 완료 - ID: {service_token_id}")
        
        return {
            "status": "success",
            "message": "서비스 토큰이 성공적으로 업데이트되었습니다.",
            "data": {
                "id": service_token.id,
                "user_uuid": service_token.user_uuid,
                "token_type": service_token.token_type,
                "plan_code": service_token.plan_code,
                "total_tokens": service_token.total_tokens,
                "used_tokens": service_token.used_tokens,
                "remaining_tokens": service_token.total_tokens - service_token.used_tokens,
                "expires_at": service_token.expires_at.isoformat() if service_token.expires_at else None,
                "created_at": service_token.created_at.isoformat(),
                "updated_at": service_token.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 서비스 토큰 업데이트 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="서비스 토큰 업데이트 중 오류가 발생했습니다."
        )

@app.post("/service-tokens/{service_token_id}/use", summary="서비스 토큰 사용")
def use_service_token(service_token_id: int, usage_data: TokenUsageCreate, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    서비스 토큰을 사용하고 사용 이력을 기록합니다.
    
    - **service_token_id**: 사용할 서비스 토큰 ID
    - **tokens_used**: 사용할 토큰 수량
    - **usage_type**: 사용 유형 (예: transcription, translation)
    - **description**: 사용 설명 (선택사항)
    """
    try:
        logger.info(f"🎯 서비스 토큰 사용 시작 - ID: {service_token_id}, 사용량: {usage_data.tokens_used}")
        
        service_token = db.query(ServiceToken).filter(ServiceToken.id == service_token_id).first()
        
        if not service_token:
            logger.warning(f"⚠️ 서비스 토큰을 찾을 수 없음 - ID: {service_token_id}")
            raise HTTPException(
                status_code=404,
                detail="해당 서비스 토큰을 찾을 수 없습니다."
            )
        
        # 토큰 잔량 확인
        remaining_tokens = service_token.total_tokens - service_token.used_tokens
        if remaining_tokens < usage_data.tokens_used:
            logger.warning(f"⚠️ 토큰 잔량 부족 - 잔량: {remaining_tokens}, 요청: {usage_data.tokens_used}")
            raise HTTPException(
                status_code=400,
                detail=f"토큰 잔량이 부족합니다. (잔량: {remaining_tokens}, 요청: {usage_data.tokens_used})"
            )
        
        # 만료일 확인
        if service_token.expires_at and service_token.expires_at < datetime.utcnow():
            logger.warning(f"⚠️ 만료된 토큰 - 만료일: {service_token.expires_at}")
            raise HTTPException(
                status_code=400,
                detail="만료된 토큰입니다."
            )
        
        # 토큰 사용량 업데이트
        service_token.used_tokens += usage_data.tokens_used
        service_token.updated_at = datetime.utcnow()
        
        # 사용 이력 기록
        usage_history = TokenUsageHistory(
            service_token_id=service_token_id,
            tokens_used=usage_data.tokens_used,
            usage_type=usage_data.usage_type,
            description=usage_data.description
        )
        
        db.add(usage_history)
        db.commit()
        db.refresh(service_token)
        db.refresh(usage_history)
        
        logger.info(f"✅ 서비스 토큰 사용 완료 - ID: {service_token_id}, 잔량: {service_token.total_tokens - service_token.used_tokens}")
        
        return {
            "status": "success",
            "message": "서비스 토큰이 성공적으로 사용되었습니다.",
            "data": {
                "service_token_id": service_token.id,
                "tokens_used": usage_data.tokens_used,
                "remaining_tokens": service_token.total_tokens - service_token.used_tokens,
                "usage_history_id": usage_history.id,
                "used_at": usage_history.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 서비스 토큰 사용 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="서비스 토큰 사용 중 오류가 발생했습니다."
        )

@app.get("/service-tokens/{service_token_id}/usage-history", summary="토큰 사용 이력 조회")
def get_token_usage_history(service_token_id: int, limit: int = 50, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    특정 서비스 토큰의 사용 이력을 조회합니다.
    
    - **service_token_id**: 조회할 서비스 토큰 ID
    - **limit**: 조회할 최대 건수 (기본값: 50)
    """
    try:
        logger.info(f"📊 토큰 사용 이력 조회 시작 - 토큰ID: {service_token_id}, 제한: {limit}")
        
        # 서비스 토큰 존재 확인
        service_token = db.query(ServiceToken).filter(ServiceToken.id == service_token_id).first()
        if not service_token:
            logger.warning(f"⚠️ 서비스 토큰을 찾을 수 없음 - ID: {service_token_id}")
            raise HTTPException(
                status_code=404,
                detail="해당 서비스 토큰을 찾을 수 없습니다."
            )
        
        usage_history = db.query(TokenUsageHistory).filter(
            TokenUsageHistory.service_token_id == service_token_id
        ).order_by(TokenUsageHistory.created_at.desc()).limit(limit).all()
        
        usage_history_list = []
        for uh in usage_history:
            usage_history_list.append({
                "id": uh.id,
                "service_token_id": uh.service_token_id,
                "tokens_used": uh.tokens_used,
                "usage_type": uh.usage_type,
                "description": uh.description,
                "created_at": uh.created_at.isoformat()
            })
        
        logger.info(f"✅ 토큰 사용 이력 조회 완료 - 총 {len(usage_history_list)}건")
        
        return {
            "status": "success",
            "message": f"토큰 사용 이력을 성공적으로 조회했습니다. (총 {len(usage_history_list)}건)",
            "data": usage_history_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 토큰 사용 이력 조회 중 오류 발생: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="토큰 사용 이력 조회 중 오류가 발생했습니다."
        )


# ==================== 구독 관련 API ====================

@app.post("/subscriptions/", summary="구독 생성")
def create_subscription(subscription: SubscriptionMasterCreate, 
                        current_user: str = Depends(verify_token), 
                        db: Session = Depends(get_db)):
    """
    새로운 구독을 생성합니다.
    
    - **plan_code**: 구독할 요금제 코드
    - **subscription_start_date**: 구독 시작일 (YYYY-MM-DD)
    - **subscription_end_date**: 구독 종료일 (선택사항, YYYY-MM-DD)
    - **next_billing_date**: 다음 결제일 (선택사항, YYYY-MM-DD)
    - **auto_renewal**: 자동 갱신 여부 (기본값: true)
    - **renewal_plan_code**: 갱신 시 적용할 요금제 (선택사항)
    """
    try:
        logger.info(f"🚀 구독 생성 시작 - 사용자: {current_user}, 요금제: {subscription.plan_code}")
        
        # 사용자 정보 조회
        user = db.query(User).filter(User.user_uuid == current_user).first()
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 요금제 존재 확인
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_code == subscription.plan_code).first()
        if not plan:
            raise HTTPException(status_code=404, detail="요금제를 찾을 수 없습니다")
        
        # 기존 활성 구독 확인
        existing_subscription = db.query(SubscriptionMaster).filter(
            SubscriptionMaster.user_uuid == current_user,
            SubscriptionMaster.subscription_status == 'active'
        ).first()
        
        if existing_subscription:
            raise HTTPException(status_code=400, detail="이미 활성화된 구독이 존재합니다")
        
        # 구독 ID 생성
        subscription_id = f"SUB_{current_user}_{int(datetime.now().timestamp())}"
        
        # 구독 생성
        from datetime import datetime, date
        new_subscription = SubscriptionMaster(
            user_uuid=current_user,
            subscription_id=subscription_id,
            plan_code=subscription.plan_code,
            subscription_status='active',
            subscription_start_date=datetime.strptime(subscription.subscription_start_date, "%Y-%m-%d").date(),
            subscription_end_date=datetime.strptime(subscription.subscription_end_date, "%Y-%m-%d").date() if subscription.subscription_end_date else None,
            next_billing_date=datetime.strptime(subscription.next_billing_date, "%Y-%m-%d").date() if subscription.next_billing_date else None,
            auto_renewal=subscription.auto_renewal,
            renewal_plan_code=subscription.renewal_plan_code
        )
        
        db.add(new_subscription)
        
        # 구독 변경 이력 생성
        change_id = f"CHG_{subscription_id}_{int(datetime.now().timestamp())}"
        change_history = SubscriptionChangeHistory(
            user_uuid=current_user,
            subscription_id=subscription_id,
            change_id=change_id,
            change_type='create',
            change_reason='새 구독 생성',
            previous_plan_code=None,
            new_plan_code=subscription.plan_code,
            previous_status=None,
            new_status='active',
            effective_date=datetime.strptime(subscription.subscription_start_date, "%Y-%m-%d").date(),
            change_requested_at=datetime.now(),
            processed_by='user'
        )
        
        db.add(change_history)
        db.commit()
        
        logger.info(f"✅ 구독 생성 완료 - 구독ID: {subscription_id}")
        
        return {
            "status": "success",
            "message": "구독이 성공적으로 생성되었습니다",
            "data": {
                "subscription_id": subscription_id,
                "user_uuid": current_user,
                "plan_code": subscription.plan_code,
                "subscription_status": "active",
                "subscription_start_date": subscription.subscription_start_date,
                "subscription_end_date": subscription.subscription_end_date,
                "next_billing_date": subscription.next_billing_date,
                "auto_renewal": subscription.auto_renewal,
                "renewal_plan_code": subscription.renewal_plan_code,
                "created_at": new_subscription.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 구독 생성 실패: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"구독 생성 실패: {str(e)}")


@app.get("/subscriptions/", summary="사용자 구독 조회")
def get_user_subscription(current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    현재 사용자의 구독 정보를 조회합니다.
    """
    try:
        logger.info(f"🔍 사용자 구독 조회 시작 - 사용자: {current_user}")
        
        # current_user는 user_id이므로 user_uuid를 조회해야 함
        user_info = get_user(current_user, db=db)
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_uuid = user_info["user_uuid"]
        logger.info(f"🔍 사용자 구독 조회 시작 - 사용자 user_uuid: {user_uuid}")        
        
        # 사용자의 현재 구독 조회
        subscription = db.query(SubscriptionMaster).filter(
            SubscriptionMaster.user_uuid == user_uuid
        ).first()
        
        if not subscription:
            return {
                "status": "success",
                "message": "구독 정보가 없습니다",
                "data": None
            }
        
        # 요금제 정보 조회
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.plan_code == subscription.plan_code
        ).first()
        
        subscription_data = {
            "id": subscription.id,
            "subscription_id": subscription.subscription_id,
            "user_uuid": subscription.user_uuid,
            "plan_code": subscription.plan_code,
            "plan_description": plan.plan_description if plan else None,
            "monthly_price": plan.monthly_price if plan else None,
            "monthly_service_tokens": plan.monthly_service_tokens if plan else None,
            "subscription_status": subscription.subscription_status,
            "subscription_start_date": subscription.subscription_start_date.isoformat() if subscription.subscription_start_date else None,
            "subscription_end_date": subscription.subscription_end_date.isoformat() if subscription.subscription_end_date else None,
            "next_billing_date": subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
            "auto_renewal": subscription.auto_renewal,
            "renewal_plan_code": subscription.renewal_plan_code,
            "created_at": subscription.created_at.isoformat(),
            "updated_at": subscription.updated_at.isoformat()
        }
        
        logger.info(f"✅ 사용자 구독 조회 완료 - 구독ID: {subscription.subscription_id}")
        
        return {
            "status": "success",
            "message": "구독 정보 조회 성공",
            "data": subscription_data
        }
        
    except Exception as e:
        logger.error(f"❌ 사용자 구독 조회 실패: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"구독 조회 실패: {str(e)}")


@app.put("/subscriptions/{subscription_id}", summary="구독 정보 수정")
def update_subscription(
    subscription_id: str, 
    subscription_update: SubscriptionMasterUpdate, 
    current_user: str = Depends(verify_token), 
    db: Session = Depends(get_db)):
    """
    구독 정보를 수정합니다.
    
    - **plan_code**: 변경할 요금제 코드
    - **subscription_status**: 구독 상태 (active, suspended, cancelled, expired)
    - **subscription_end_date**: 구독 종료일
    - **next_billing_date**: 다음 결제일
    - **auto_renewal**: 자동 갱신 여부
    - **renewal_plan_code**: 갱신 시 적용할 요금제
    """
    try:
        logger.info(f"🔄 구독 수정 시작 - 구독ID: {subscription_id}, 사용자: {current_user}")
        
        # current_user는 user_id이므로 user_uuid를 조회해야 함
        user_info = get_user(current_user, db=db)
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_uuid = user_info["user_uuid"]
        logger.info(f"🔍 사용자 구독 조회 시작 - 사용자 user_uuid: {user_uuid}")           
        
        # 구독 조회
        subscription = db.query(SubscriptionMaster).filter(
            SubscriptionMaster.subscription_id == subscription_id,
            SubscriptionMaster.user_uuid == user_uuid
        ).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="구독을 찾을 수 없습니다")
        
        # 변경 전 정보 저장
        previous_plan_code = subscription.plan_code
        previous_status = subscription.subscription_status
        
        # 구독 정보 업데이트
        update_data = subscription_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if field in ['subscription_end_date', 'next_billing_date'] and value:
                value = datetime.strptime(value, "%Y-%m-%d").date()
            setattr(subscription, field, value)
        
        # 변경 이력 생성 (요금제나 상태가 변경된 경우)
        if subscription_update.plan_code or subscription_update.subscription_status:
            change_id = f"CHG_{subscription_id}_{int(datetime.now().timestamp())}"
            
            # 변경 유형 결정
            change_type = 'update'
            if subscription_update.subscription_status == 'suspended':
                change_type = 'suspend'
            elif subscription_update.subscription_status == 'cancelled':
                change_type = 'cancel'
            elif subscription_update.subscription_status == 'active' and previous_status != 'active':
                change_type = 'resume'
            elif subscription_update.plan_code and subscription_update.plan_code != previous_plan_code:
                # 정확한 업그레이드/다운그레이드 판단
                change_type = _determine_change_type(previous_plan_code, subscription_update.plan_code, db)
            
            logger.info(f"🔍 사용자 구독 조회 시작 - 사용자 user_uuid2 {user_uuid}")           
            change_history = SubscriptionChangeHistory(
                user_uuid=user_uuid,
                subscription_id=subscription_id,
                change_id=change_id,
                change_type=change_type,
                change_reason='구독 정보 수정',
                previous_plan_code=previous_plan_code,
                new_plan_code=subscription.plan_code,
                previous_status=previous_status,
                new_status=subscription.subscription_status,
                effective_date=datetime.now().date(),
                change_requested_at=datetime.now(),
                processed_by='user'
            )
            
            db.add(change_history)
        
        db.commit()
        
        logger.info(f"✅ 구독 수정 완료 - 구독ID: {subscription_id}")
        
        return {
            "status": "success",
            "message": "구독 정보가 성공적으로 수정되었습니다",
            "data": {
                "subscription_id": subscription.subscription_id,
                "plan_code": subscription.plan_code,
                "subscription_status": subscription.subscription_status,
                "subscription_end_date": subscription.subscription_end_date.isoformat() if subscription.subscription_end_date else None,
                "next_billing_date": subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
                "auto_renewal": subscription.auto_renewal,
                "renewal_plan_code": subscription.renewal_plan_code,
                "updated_at": subscription.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 구독 수정 실패: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"구독 수정 실패: {str(e)}")


def _get_new_status_from_change_type(change_type: str, current_status: str) -> str:
    """변경 유형에 따른 새로운 구독 상태 반환"""
    if change_type == 'suspend':
        return 'suspended'
    elif change_type == 'resume':
        return 'active'
    elif change_type == 'cancel':
        return 'cancelled'
    elif change_type in ['upgrade', 'downgrade']:
        return 'active'
    else:
        return current_status


def _determine_change_type(current_plan_code: str, new_plan_code: str, db: Session) -> str:
    """
    현재 요금제와 새 요금제를 비교하여 변경 유형을 결정합니다.
    
    Args:
        current_plan_code: 현재 요금제 코드
        new_plan_code: 새 요금제 코드
        db: 데이터베이스 세션
    
    Returns:
        변경 유형 ('upgrade', 'downgrade', 'same')
    """
    if current_plan_code == new_plan_code:
        return 'same'
    
    # 현재 요금제 정보 조회
    current_plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.plan_code == current_plan_code
    ).first()
    
    # 새 요금제 정보 조회
    new_plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.plan_code == new_plan_code
    ).first()
    
    if not current_plan or not new_plan:
        return 'update'  # 요금제 정보를 찾을 수 없는 경우 기본값
    
    # 월 구독 금액을 기준으로 업그레이드/다운그레이드 판단
    if new_plan.monthly_price > current_plan.monthly_price:
        return 'upgrade'
    elif new_plan.monthly_price < current_plan.monthly_price:
        return 'downgrade'
    else:
        # 금액이 같은 경우 서비스 토큰 수로 판단
        if new_plan.monthly_service_tokens > current_plan.monthly_service_tokens:
            return 'upgrade'
        elif new_plan.monthly_service_tokens < current_plan.monthly_service_tokens:
            return 'downgrade'
        else:
            return 'same'


def _calculate_proration(current_plan: SubscriptionPlan, new_plan: SubscriptionPlan, 
                        billing_cycle_start: date, billing_cycle_end: date, 
                        change_date: date) -> dict:
    """
    요금제 변경 시 일할 계산을 수행합니다.
    
    Args:
        current_plan: 현재 요금제 정보
        new_plan: 새 요금제 정보
        billing_cycle_start: 현재 청구 주기 시작일
        billing_cycle_end: 현재 청구 주기 종료일
        change_date: 변경 적용일
    
    Returns:
        일할 계산 결과 딕셔너리
    """
    from datetime import timedelta
    
    # 전체 청구 주기 일수
    total_days = (billing_cycle_end - billing_cycle_start).days + 1
    
    # 변경일부터 청구 주기 종료일까지의 남은 일수
    remaining_days = (billing_cycle_end - change_date).days + 1
    
    if remaining_days <= 0:
        return {
            "proration_amount": 0,
            "refund_amount": 0,
            "additional_charge": 0,
            "calculation_details": "변경일이 청구 주기를 벗어남"
        }
    
    # 현재 요금제의 일할 환불 금액
    current_daily_rate = current_plan.monthly_price / total_days
    refund_amount = int(current_daily_rate * remaining_days)
    
    # 새 요금제의 일할 청구 금액
    new_daily_rate = new_plan.monthly_price / total_days
    additional_charge = int(new_daily_rate * remaining_days)
    
    # 순 일할 계산 금액 (양수: 추가 청구, 음수: 환불)
    proration_amount = additional_charge - refund_amount
    
    calculation_details = (
        f"전체 청구 주기: {total_days}일, "
        f"남은 일수: {remaining_days}일, "
        f"현재 요금제 일할: {current_daily_rate:.2f}원/일, "
        f"새 요금제 일할: {new_daily_rate:.2f}원/일"
    )
    
    return {
        "proration_amount": proration_amount,
        "refund_amount": refund_amount if proration_amount < 0 else 0,
        "additional_charge": additional_charge if proration_amount > 0 else 0,
        "calculation_details": calculation_details
    }


def _validate_subscription_change(subscription: SubscriptionMaster, change_type: str, 
                                 new_plan_code: str = None) -> bool:
    """
    구독 변경 요청의 유효성을 검증합니다.
    
    Args:
        subscription: 현재 구독 정보
        change_type: 변경 유형
        new_plan_code: 새 요금제 코드 (선택사항)
    
    Returns:
        유효성 검증 결과
    
    Raises:
        HTTPException: 유효하지 않은 변경 요청인 경우
    """
    current_status = subscription.subscription_status
    
    # 상태별 허용되는 변경 유형 정의
    allowed_changes = {
        'active': ['upgrade', 'downgrade', 'suspend', 'cancel'],
        'suspended': ['resume', 'cancel'],
        'cancelled': [],  # 취소된 구독은 변경 불가
        'expired': []     # 만료된 구독은 변경 불가
    }
    
    if current_status not in allowed_changes:
        raise HTTPException(
            status_code=400, 
            detail=f"알 수 없는 구독 상태입니다: {current_status}"
        )
    
    if change_type not in allowed_changes[current_status]:
        raise HTTPException(
            status_code=400,
            detail=f"현재 상태({current_status})에서는 {change_type} 변경이 허용되지 않습니다"
        )
    
    # 요금제 변경 시 새 요금제 코드 필수
    if change_type in ['upgrade', 'downgrade'] and not new_plan_code:
        raise HTTPException(
            status_code=400,
            detail="요금제 변경 시 새 요금제 코드가 필요합니다"
        )
    
    # 동일한 요금제로 변경 방지
    if new_plan_code and new_plan_code == subscription.plan_code:
        raise HTTPException(
            status_code=400,
            detail="현재와 동일한 요금제로는 변경할 수 없습니다"
        )
    
    return True


@app.post("/subscriptions/{subscription_id}/change", summary="구독 변경 요청")
def create_subscription_change(subscription_id: str, change_request: SubscriptionChangeCreate, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    구독 변경을 요청합니다.
    
    - **change_type**: 변경 유형 (upgrade, downgrade, suspend, resume, cancel)
    - **change_reason**: 변경 사유
    - **new_plan_code**: 새로운 요금제 코드 (요금제 변경 시)
    - **effective_date**: 변경 적용일 (YYYY-MM-DD)
    - **proration_amount**: 일할 계산 금액
    - **refund_amount**: 환불 금액
    - **additional_charge**: 추가 청구 금액
    - **admin_notes**: 관리자 메모
    """
    try:
        logger.info(f"🔄 구독 변경 요청 시작 - 구독ID: {subscription_id}, 변경유형: {change_request.change_type}")
        
        # 구독 조회
        subscription = db.query(SubscriptionMaster).filter(
            SubscriptionMaster.subscription_id == subscription_id,
            SubscriptionMaster.user_uuid == current_user
        ).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="구독을 찾을 수 없습니다")
        
        # 변경 요청 검증
        _validate_subscription_change(subscription, change_request.change_type, change_request.new_plan_code)
        
        # 새 요금제 존재 확인 (요금제 변경 시)
        if change_request.new_plan_code:
            new_plan = db.query(SubscriptionPlan).filter(
                SubscriptionPlan.plan_code == change_request.new_plan_code
            ).first()
            if not new_plan:
                raise HTTPException(status_code=404, detail="새 요금제를 찾을 수 없습니다")
            
            # 변경 유형이 요금제 변경인 경우 정확한 타입 결정
            if change_request.change_type in ['upgrade', 'downgrade']:
                actual_change_type = _determine_change_type(subscription.plan_code, change_request.new_plan_code, db)
                if actual_change_type != change_request.change_type:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"요청한 변경 유형({change_request.change_type})과 실제 변경 유형({actual_change_type})이 일치하지 않습니다"
                    )
        
        # 변경 ID 생성
        change_id = f"CHG_{subscription_id}_{int(datetime.now().timestamp())}"
        
        # 비례 계산 (요금제 변경 시)
        proration_result = None
        if change_request.change_type in ['upgrade', 'downgrade'] and change_request.new_plan_code:
            current_plan = db.query(SubscriptionPlan).filter(
                SubscriptionPlan.plan_code == subscription.plan_code
            ).first()
            new_plan = db.query(SubscriptionPlan).filter(
                SubscriptionPlan.plan_code == change_request.new_plan_code
            ).first()
            
            if current_plan and new_plan and subscription.billing_cycle_start_date and subscription.billing_cycle_end_date:
                effective_date = datetime.strptime(change_request.effective_date, "%Y-%m-%d").date()
                proration_result = _calculate_proration(
                    current_plan, 
                    new_plan, 
                    subscription.billing_cycle_start_date,
                    subscription.billing_cycle_end_date,
                    effective_date
                )
        
        # 변경 이력 생성
        change_history = SubscriptionChangeHistory(
            user_uuid=current_user,
            subscription_id=subscription_id,
            change_id=change_id,
            change_type=change_request.change_type,
            change_reason=change_request.change_reason,
            previous_plan_code=subscription.plan_code,
            new_plan_code=change_request.new_plan_code or subscription.plan_code,
            previous_status=subscription.subscription_status,
            new_status=_get_new_status_from_change_type(change_request.change_type, subscription.subscription_status),
            effective_date=datetime.strptime(change_request.effective_date, "%Y-%m-%d").date(),
            change_requested_at=datetime.now(),
            proration_amount=proration_result['proration_amount'] if proration_result else change_request.proration_amount,
            refund_amount=proration_result['refund_amount'] if proration_result else change_request.refund_amount,
            additional_charge=proration_result['additional_charge'] if proration_result else change_request.additional_charge,
            processed_by='user',
            admin_notes=change_request.admin_notes
        )
        
        db.add(change_history)
        
        # 즉시 적용되는 변경의 경우 구독 마스터 업데이트
        effective_date = datetime.strptime(change_request.effective_date, "%Y-%m-%d").date()
        if effective_date <= datetime.now().date():
            if change_request.new_plan_code:
                subscription.plan_code = change_request.new_plan_code
            
            new_status = _get_new_status_from_change_type(change_request.change_type, subscription.subscription_status)
            subscription.subscription_status = new_status
            
            change_history.change_processed_at = datetime.now()
        
        db.commit()
        
        logger.info(f"✅ 구독 변경 요청 완료 - 변경ID: {change_id}")
        
        response_data = {
            "status": "success",
            "message": "구독 변경 요청이 성공적으로 처리되었습니다",
            "data": {
                "change_id": change_id,
                "subscription_id": subscription_id,
                "change_type": change_request.change_type,
                "change_reason": change_request.change_reason,
                "previous_plan_code": subscription.plan_code,
                "new_plan_code": change_request.new_plan_code,
                "effective_date": change_request.effective_date,
                "proration_amount": change_history.proration_amount,
                "refund_amount": change_history.refund_amount,
                "additional_charge": change_history.additional_charge,
                "created_at": change_history.created_at.isoformat()
            }
        }
        
        # 비례 계산 상세 정보 추가 (있는 경우)
        if proration_result:
            response_data["data"]["proration_details"] = {
                "remaining_days": proration_result["remaining_days"],
                "total_days": proration_result["total_days"],
                "current_plan_daily_rate": proration_result["current_plan_daily_rate"],
                "new_plan_daily_rate": proration_result["new_plan_daily_rate"],
                "calculation_method": "일할 계산 기반"
            }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 구독 변경 요청 실패: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"구독 변경 요청 실패: {str(e)}")


@app.get("/subscriptions/{subscription_id}/history", summary="구독 변경 이력 조회")
def get_subscription_history(subscription_id: str, limit: int = 50, current_user: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    구독의 변경 이력을 조회합니다.
    
    - **subscription_id**: 구독 식별자
    - **limit**: 조회할 이력 수 (기본값: 50)
    """
    try:
        logger.info(f"📋 구독 변경 이력 조회 시작 - 구독ID: {subscription_id}")
        
        # 구독 소유권 확인
        subscription = db.query(SubscriptionMaster).filter(
            SubscriptionMaster.subscription_id == subscription_id,
            SubscriptionMaster.user_uuid == current_user
        ).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="구독을 찾을 수 없습니다")
        
        # 변경 이력 조회
        history = db.query(SubscriptionChangeHistory).filter(
            SubscriptionChangeHistory.subscription_id == subscription_id
        ).order_by(SubscriptionChangeHistory.created_at.desc()).limit(limit).all()
        
        history_list = []
        for h in history:
            history_list.append({
                "id": h.id,
                "change_id": h.change_id,
                "subscription_id": h.subscription_id,
                "change_type": h.change_type,
                "change_reason": h.change_reason,
                "previous_plan_code": h.previous_plan_code,
                "new_plan_code": h.new_plan_code,
                "previous_status": h.previous_status,
                "new_status": h.new_status,
                "effective_date": h.effective_date.isoformat() if h.effective_date else None,
                "change_requested_at": h.change_requested_at.isoformat() if h.change_requested_at else None,
                "change_processed_at": h.change_processed_at.isoformat() if h.change_processed_at else None,
                "proration_amount": h.proration_amount,
                "refund_amount": h.refund_amount,
                "additional_charge": h.additional_charge,
                "processed_by": h.processed_by,
                "admin_notes": h.admin_notes,
                "created_at": h.created_at.isoformat()
            })
        
        logger.info(f"✅ 구독 변경 이력 조회 완료 - {len(history_list)}건")
        
        return {
            "status": "success",
            "message": "구독 변경 이력 조회 성공",
            "data": {
                "subscription_id": subscription_id,
                "history": history_list,
                "total_count": len(history_list)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 구독 변경 이력 조회 실패: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"구독 변경 이력 조회 실패: {str(e)}")

# ==================== 추가 토큰 구매 API ====================

@app.post("/additional-tokens/purchase", summary="추가 토큰 구매")
def purchase_additional_tokens(
    request: AdditionalTokenPurchaseRequest,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> AdditionalTokenPurchaseResponse:
    """
    사용자의 활성 구독에 기반하여 추가 토큰을 구매합니다.
    
    - **token_quantity**: 구매할 토큰 수량 (양수만 허용)
    - **payment_method**: 결제 수단 (선택사항)
    
    처리 과정:
    1. 사용자의 활성 구독 상태 확인
    2. 구독 요금제의 per_minute_rate 조회
    3. 토큰 비용 계산 (per_minute_rate × 토큰 수량)
    4. 결제 정보 생성 (payments 테이블)
    5. 토큰 구매 상세 정보 생성 (token_payments 테이블)
    6. 서비스 토큰 할당량 업데이트 (service_tokens 테이블)
    """
    try:
        logger.info(f"🛒 추가 토큰 구매 시작 - 사용자: {current_user}, 토큰 수량: {request.token_quantity}")
        
        # 1. 사용자 정보 조회
        user_info = get_user(current_user)
        if not user_info:
            logger.warning(f"⚠️ 사용자를 찾을 수 없음 - user_uuid: {current_user}")
            raise HTTPException(
                status_code=404,
                detail="사용자를 찾을 수 없습니다."
            )
        
        user_uuid = user_info["user_uuid"]
        
        # 2. 활성 구독 상태 확인
        active_subscription = db.query(SubscriptionMaster).filter(
            SubscriptionMaster.user_uuid == user_uuid,
            SubscriptionMaster.subscription_status == "active"
        ).first()
        
        if not active_subscription:
            logger.warning(f"⚠️ 활성 구독을 찾을 수 없음 - user_uuid: {user_uuid}")
            raise HTTPException(
                status_code=400,
                detail="활성 구독이 없습니다. 먼저 구독을 활성화해주세요."
            )
        
        logger.info(f"📋 활성 구독 확인 - 구독ID: {active_subscription.subscription_id}, 요금제: {active_subscription.plan_code}")
        
        # 3. 구독 요금제의 per_minute_rate 조회
        subscription_plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.plan_code == active_subscription.plan_code
        ).first()
        
        if not subscription_plan:
            logger.error(f"❌ 구독 요금제를 찾을 수 없음 - plan_code: {active_subscription.plan_code}")
            raise HTTPException(
                status_code=500,
                detail="구독 요금제 정보를 찾을 수 없습니다."
            )
        
        per_minute_rate = subscription_plan.per_minute_rate
        logger.info(f"💰 요금제 정보 - 분당 요금: {per_minute_rate}원")
        
        # 4. 토큰 비용 계산
        token_unit_price = int(per_minute_rate)  # 분당 요금을 토큰 단가로 사용
        supply_amount = token_unit_price * request.token_quantity
        total_amount = int(supply_amount * 1.1)  # 부가세 제외 공급가액
        vat_amount = total_amount - supply_amount  # 부가세
        
        logger.info(f"💵 비용 계산 - 토큰단가: {token_unit_price}원, 총액: {total_amount}원 (공급가액: {supply_amount}원, 부가세: {vat_amount}원)")
        
        # 5. 결제 정보 생성
        new_payment = Payment(
            user_uuid=user_uuid,
            plan_code=active_subscription.plan_code,
            supply_amount=supply_amount,
            vat_amount=vat_amount,
            total_amount=total_amount,
            payment_status="pending",
            payment_method=request.payment_method,
            payment_type="token_purchase"
        )
        
        db.add(new_payment)
        db.flush()  # payment_id 생성을 위해 flush
        
        logger.info(f"💳 결제 정보 생성 - 결제번호: {new_payment.payment_id}")
        
        # 6. 토큰 구매 상세 정보 생성
        token_payment = TokenPayment(
            payment_id=new_payment.payment_id,
            token_quantity=request.token_quantity,
            token_unit_price=token_unit_price,
            amount=supply_amount
        )
        
        db.add(token_payment)
        
        # 7. 서비스 토큰 할당량 업데이트
        service_token = db.query(ServiceToken).filter(
            ServiceToken.user_uuid == user_uuid,
            ServiceToken.status == "active"
        ).first()
        
        if service_token:
            # 기존 할당 토큰에 추가
            old_quota = service_token.quota_tokens
            service_token.quota_tokens += Decimal(str(request.token_quantity))
            logger.info(f"🔄 토큰 할당량 업데이트 - 기존: {old_quota} → 신규: {service_token.quota_tokens}")
        else:
            # 새로운 서비스 토큰 생성
            from datetime import timedelta
            import uuid
            
            expiry_date = datetime.now() + timedelta(days=365)  # 1년 후 만료
            new_service_token = ServiceToken(
                user_uuid=user_uuid,
                token_id=str(uuid.uuid4()),
                quota_tokens=Decimal(str(request.token_quantity)),
                used_tokens=Decimal('0'),
                token_expiry_date=expiry_date.date(),
                status="active"
            )
            db.add(new_service_token)
            logger.info(f"🆕 새 서비스 토큰 생성 - 할당량: {request.token_quantity}")
        
        # 8. 결제 상태를 완료로 변경 (실제 결제 연동 시에는 제거)
        new_payment.payment_status = "completed"
        new_payment.completed_at = datetime.now()
        
        db.commit()
        
        logger.info(f"✅ 추가 토큰 구매 완료 - 결제번호: {new_payment.payment_id}, 토큰수량: {request.token_quantity}")
        
        return AdditionalTokenPurchaseResponse(
            status="success",
            message="추가 토큰 구매가 성공적으로 완료되었습니다.",
            data={
                "payment_id": new_payment.payment_id,
                "token_quantity": request.token_quantity,
                "token_unit_price": token_unit_price,
                "total_amount": total_amount,
                "supply_amount": supply_amount,
                "vat_amount": vat_amount,
                "plan_code": active_subscription.plan_code,
                "per_minute_rate": per_minute_rate,
                "payment_status": new_payment.payment_status,
                "created_at": new_payment.created_at.isoformat()
            }
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 추가 토큰 구매 실패: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="추가 토큰 구매 중 오류가 발생했습니다."
        )


# ==================== 월빌링 API ====================

@app.post("/monthly-billing/generate", summary="월빌링 생성")
def generate_monthly_billing(
    request: MonthlyBillingRequest,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> MonthlyBillingResponse:
    """
    지정된 년월의 모든 활성 구독자에 대한 월빌링을 생성합니다.
    
    - **target_year**: 청구 연도 (2020-2030)
    - **target_month**: 청구 월 (1-12)
    
    처리 과정:
    1. 활성 구독이 있는 모든 사용자 조회
    2. 사용자별 월별 사용량 집계
    3. 초과 사용량 계산 및 요금 산정
    4. 월빌링 레코드 생성
    5. 초과 사용량이 있는 경우 초과 결제 처리
    """
    try:
        logger.info(f"🚀 월빌링 생성 API 호출 - 사용자: {current_user}, 대상: {request.target_year}년 {request.target_month}월")
        
        # 월빌링 서비스 초기화
        from monthly_billing_service import MonthlyBillingService
        billing_service = MonthlyBillingService(db)
        
        # 월빌링 생성
        result = billing_service.generate_monthly_billing(
            target_year=request.target_year,
            target_month=request.target_month
        )
        
        logger.info(f"✅ 월빌링 생성 API 완료 - 생성건수: {result.get('created_count', 0)}건")
        
        return MonthlyBillingResponse(
            status="success",
            message=result["message"],
            data=result
        )
        
    except Exception as e:
        logger.error(f"❌ 월빌링 생성 API 실패: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"월빌링 생성 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/monthly-billing/subscription-payments", summary="월구독결제 생성")
def create_monthly_subscription_payments(
    request: MonthlySubscriptionBillingRequest,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> MonthlyBillingResponse:
    """
    활성 구독자들의 월 구독료 결제를 생성하고 서비스 토큰을 초기화합니다.
    
    - **target_year**: 결제 연도 (2020-2030)
    - **target_month**: 결제 월 (1-12)
    
    처리 과정:
    1. 활성 구독 조회
    2. 구독별 결제 정보 생성
    3. 서비스 토큰 할당량 초기화
    4. 결제 상태를 완료로 처리
    """
    try:
        logger.info(f"🚀 월구독결제 생성 API 호출 - 사용자: {current_user}, 대상: {request.target_year}년 {request.target_month}월")
        
        # 월빌링 서비스 초기화
        from monthly_billing_service import MonthlyBillingService
        billing_service = MonthlyBillingService(db)
        
        # 월구독결제 생성
        result = billing_service.create_monthly_subscription_billing(
            target_year=request.target_year,
            target_month=request.target_month
        )
        
        logger.info(f"✅ 월구독결제 생성 API 완료 - 생성건수: {result.get('created_count', 0)}건")
        
        return MonthlyBillingResponse(
            status="success",
            message=result["message"],
            data=result
        )
        
    except Exception as e:
        logger.error(f"❌ 월구독결제 생성 API 실패: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"월구독결제 생성 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/monthly-billing/summary", summary="월빌링 요약 조회")
def get_monthly_billing_summary(
    target_year: int = Query(..., ge=2020, le=2030, description="조회 연도"),
    target_month: int = Query(..., ge=1, le=12, description="조회 월"),
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> MonthlyBillingResponse:
    """
    지정된 년월의 월빌링 요약 정보를 조회합니다.
    
    - **target_year**: 조회 연도 (2020-2030)
    - **target_month**: 조회 월 (1-12)
    
    반환 정보:
    - 총 빌링 건수
    - 총 청구 금액
    - 총 초과 사용료
    - 평균 사용 시간
    - 상태별 빌링 건수
    """
    try:
        logger.info(f"🔍 월빌링 요약 조회 API 호출 - 사용자: {current_user}, 대상: {target_year}년 {target_month}월")
        
        # 월빌링 서비스 초기화
        from monthly_billing_service import MonthlyBillingService
        billing_service = MonthlyBillingService(db)
        
        # 월빌링 요약 조회
        result = billing_service.get_monthly_billing_summary(
            target_year=target_year,
            target_month=target_month
        )
        
        logger.info(f"✅ 월빌링 요약 조회 API 완료 - 총 {result.get('total_billings', 0)}건")
        
        return MonthlyBillingResponse(
            status="success",
            message="월빌링 요약 조회 성공",
            data=result
        )
        
    except Exception as e:
        logger.error(f"❌ 월빌링 요약 조회 API 실패: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"월빌링 요약 조회 중 오류가 발생했습니다: {str(e)}"
        )
        
# 현재 월 빌링 생성
@app.post("/monthly-billing/current-month/generate", summary="현재 월 빌링 생성")
def generate_current_month_billing(
    # current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> MonthlyBillingResponse:
    """
    현재 월의 월빌링을 생성합니다.
    
    처리 과정:
    1. 현재 년월 자동 계산
    2. 활성 구독자 대상 월빌링 생성
    3. 초과 사용량 처리
    """
    try:

        from monthly_billing_service import create_monthly_billing_for_current_month

        # logger.info(f"🚀 현재 월 빌링 생성 API 호출 - 사용자: {current_user}")
        
        # 현재 월 빌링 생성
        result = create_monthly_billing_for_current_month(db)
        
        logger.info(f"✅ 현재 월 빌링 생성 API 완료 - 생성건수: {result.get('created_count', 0)}건")
        
        return MonthlyBillingResponse(
            status="success",
            message=result["message"],
            data=result
        )
        
    except Exception as e:
        logger.error(f"❌ 현재 월 빌링 생성 API 실패: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"현재 월 빌링 생성 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/monthly-billing/current-month/subscription-payments", summary="현재 월 구독결제 생성")
def create_current_month_subscription_payments(
    # current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
) -> MonthlyBillingResponse:
    """
    현재 월의 구독결제를 생성하고 서비스 토큰을 초기화합니다.
    
    처리 과정:
    1. 현재 년월 자동 계산
    2. 활성 구독자 대상 구독결제 생성
    3. 서비스 토큰 할당량 초기화
    """
    try:
        # logger.info(f"🚀 현재 월 구독결제 생성 API 호출 - 사용자: {current_user}")
        
        # 현재 월 구독결제 생성
        from monthly_billing_service import create_subscription_payments_for_current_month
        result = create_subscription_payments_for_current_month(db)
        
        logger.info(f"✅ 현재 월 구독결제 생성 API 완료 - 생성건수: {result.get('created_count', 0)}건")
        
        return MonthlyBillingResponse(
            status="success",
            message=result["message"],
            data=result
        )
        
    except Exception as e:
        logger.error(f"❌ 현재 월 구독결제 생성 API 실패: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"현재 월 구독결제 생성 중 오류가 발생했습니다: {str(e)}"
        )



def get_last_day_of_month(year: int, month: int) -> int:
    """
    Get the last day of specified month
    Args:
        year: Year (e.g. 2024)
        month: Month (1-12)
    Returns:
        Last day of month (28-31)
    """
    return monthrange(year, month)[1]

# Example usage:
# current_date = datetime.now()
# last_day = get_last_day_of_month(current_date.year, current_date.month)

def get_last_day_of_month(year: int, month: int) -> int:
    """
    Get the last day of specified month
    Args:
        year: Year (e.g. 2024)
        month: Month (1-12)
    Returns:
        Last day of month (28-31)
    """
    return monthrange(year, month)[1]


if __name__ == "__main__":
    import logging
    # 로깅 레벨을 DEBUG로 설정하여 더 자세한 로그 확인
    logging.basicConfig(level=logging.DEBUG)

    uvicorn.run("backend.core.app:app", host="0.0.0.0", port=8000, reload=False, log_level="debug")