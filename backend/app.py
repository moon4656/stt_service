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
from database import get_db, create_tables, test_connection, TranscriptionRequest, TranscriptionResponse, APIUsageLog
from db_service import TranscriptionService, APIUsageService
from openai_service import OpenAIService

# 환경 변수 로드
load_dotenv()

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
        # 데이터베이스 연결 테스트
        if test_connection():
            print("✅ Database connection successful")
            # 테이블 생성
            create_tables()
            print("✅ Database tables created/verified")
        else:
            print("❌ Database connection failed - running without database logging")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        print("⚠️  Running without database logging")
    
    yield  # 애플리케이션 실행
    
    # 종료 시 실행 (필요시)
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
    print(f"Global exception handler caught: {type(exc).__name__}: {str(exc)}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
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
        print(f"Received file: {file.filename}")
        
        # 파일 확장자 확인
        file_extension = file.filename.split('.')[-1].lower()
        supported_formats = ['mp3', 'wav', 'm4a', 'ogg', 'flac', '3gp', '3gpp', 'ac3', 'aac', 'aiff', 'amr', 'au', 'opus', 'ra']
        
        print(f"File extension: {file_extension}")
        
        if file_extension not in supported_formats:
            # API 사용 로그 기록 (실패)
            try:
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
        
        # 데이터베이스에 요청 기록
        try:
            print(f"Attempting to create request record...")
            print(f"DB session: {db}")
            request_record = TranscriptionService.create_request(
                db=db,
                user_id='moon4656',  # 익명 사용자
                filename=file.filename,
                file_size=file_size,
                file_extension=file_extension
            )
            print(f"✅ Created request record with ID: {request_record.id}")
        except Exception as db_error:
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
        
        print(f"Uploading to Daglo API: {DAGLO_API_URL}")
        print(f"File size: {file_size} bytes")
        
        # 1단계: Daglo API에 음성 파일 업로드
        response = requests.post(DAGLO_API_URL, headers=headers, files=files)
        
        print(f"Daglo API response status: {response.status_code}")
        print(f"Daglo API response text: {response.text}")
        
        # 응답 확인
        if response.status_code != 200:
            error_detail = response.text
            
            # 요청 실패로 업데이트
            if request_record:
                try:
                    TranscriptionService.complete_request(
                        db=db,
                        request_id=request_record.id,
                        status="failed",
                        error_message=f"Daglo API error: {error_detail}"
                    )
                except Exception as db_error:
                    print(f"Failed to update request record: {db_error}")
            
            # API 사용 로그 기록 (실패)
            try:
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
                print(f"Failed to log API usage: {log_error}")
            
            raise HTTPException(status_code=response.status_code, detail=f"API 호출 실패: {error_detail}")
        
        # RID 추출
        upload_result = response.json()
        rid = upload_result.get('rid')
        
        if not rid:
            # 요청 실패로 업데이트
            if request_record:
                try:
                    TranscriptionService.complete_request(
                        db=db,
                        request_id=request_record.id,
                        status="failed",
                        error_message="RID not received from Daglo API"
                    )
                except Exception as db_error:
                    print(f"Failed to update request record: {db_error}")
            
            raise HTTPException(status_code=500, detail="RID를 받지 못했습니다.")
        
        # RID를 요청 기록에 업데이트
        if request_record:
            try:
                TranscriptionService.update_request_with_rid(db=db, request_id=request_record.id, daglo_rid=rid)
            except Exception as db_error:
                print(f"Failed to update RID: {db_error}")
        
        # 2단계: RID로 결과 조회 (폴링)
        result_url = f"{DAGLO_API_URL}/{rid}"
        max_attempts = 30  # 최대 30번 시도 (약 5분)
        
        for attempt in range(max_attempts):
            result_response = requests.get(result_url, headers=headers)
            
            if result_response.status_code == 200:
                result_data = result_response.json()
                status = result_data.get('status')
                
                if status == 'transcribed':
                    # 변환 완료
                    processing_time = time.time() - start_time
                    
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
                    
                    # OpenAI 요약 생성
                    summary_text = None
                    if transcribed_text and openai_service.is_configured():
                        try:
                            summary_text = await openai_service.summarize_text(transcribed_text)
                            print(f"Summary generated successfully: {len(summary_text) if summary_text else 0} characters")
                        except Exception as summary_error:
                            print(f"Failed to generate summary: {summary_error}")
                    
                    # 요청 완료로 업데이트
                    if request_record:
                        try:
                            TranscriptionService.complete_request(
                                db=db,
                                request_id=request_record.id,
                                status="completed"
                            )
                            
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
                    if request_record:
                        try:
                            TranscriptionService.complete_request(
                                db=db,
                                request_id=request_record.id,
                                status="failed",
                                error_message=f"Daglo transcription failed: {status}"
                            )
                        except Exception as db_error:
                            print(f"Failed to update request record: {db_error}")
                    
                    raise HTTPException(status_code=500, detail="음성 변환에 실패했습니다.")
                else:
                    # 아직 처리 중, 10초 대기
                    time.sleep(10)
            else:
                raise HTTPException(status_code=result_response.status_code, detail="결과 조회 실패")
        
        # 최대 시도 횟수 초과
        if request_record:
            try:
                TranscriptionService.complete_request(
                    db=db,
                    request_id=request_record.id,
                    status="failed",
                    error_message="Transcription timeout"
                )
            except Exception as db_error:
                print(f"Failed to update request record: {db_error}")
        
        raise HTTPException(status_code=408, detail="음성 변환 시간이 초과되었습니다.")
    
    except HTTPException as he:
        # API 사용 로그 기록 (HTTPException)
        try:
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
            print(f"Failed to log API usage: {log_error}")
        
        raise he
    except Exception as e:
        print(f"Exception occurred: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        
        # 요청 실패로 업데이트
        if request_record:
            try:
                TranscriptionService.complete_request(
                    db=db,
                    request_id=request_record.id,
                    status="failed",
                    error_message=str(e)
                )
            except Exception as db_error:
                print(f"Failed to update request record: {db_error}")
        
        # API 사용 로그 기록 (서버 오류)
        try:
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
            print(f"Failed to log API usage: {log_error}")
        
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
def login(login_request: LoginRequest, db: Session = Depends(get_db)):
    """
    사용자 로그인 후 JWT 토큰을 발급합니다.
    """
    # 사용자 인증 (패스워드 검증 포함)
    user = authenticate_user(login_request.user_id, login_request.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # JWT 토큰 생성
    access_token = create_access_token(data={"sub": login_request.user_id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

# 토큰 관리 API
@app.post("/tokens/{token_id}", summary="API 키 발행")
def create_token(token_id: str, description: Optional[str] = "", current_user: str = Depends(verify_token)):
    """
    사용자별 API 키를 발행합니다.
    JWT 토큰이 필요합니다.
    토큰명은 URL 파라미터로 입력합니다.
    """
    try:
        token_info = TokenManager.generate_api_key(
            user_id=current_user,
            token_id=token_id,
            description=description
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
def get_user_tokens(current_user: str = Depends(verify_token)):
    """
    현재 사용자의 모든 토큰을 조회합니다.
    JWT 토큰이 필요합니다.
    """
    try:
        tokens = TokenManager.get_user_tokens(current_user)
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