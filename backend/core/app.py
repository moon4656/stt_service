import logging
import sys
import os
from logging.handlers import TimedRotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 라우터 임포트
from core.routers import (
    auth,
    transcription,
    tokens,
    users,
    subscriptions,
    payments,
    service_tokens,
    billing,
    monitoring
)

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
    
    # 파일 핸들러 설정
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "stt_service.log"),
        when='midnight',  # 자정마다 회전
        interval=1,       # 1일 간격
        backupCount=30,   # 30일치 보관
        encoding='utf-8'
    )
    file_handler.suffix = "%Y%m%d"  # 백업 파일명 형식
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
    logger.info("🔧 로깅 시스템 초기화 완료 - 일단위 회전 설정")
    
    return logger

# 로깅 초기화
logger = setup_logging()

# 기존 설정들 (로깅, 미들웨어 등)
# ... existing code ...

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 기존 lifespan 로직
    yield

app = FastAPI(
    title="Speech-to-Text Service", 
    description="다중 STT 서비스를 지원하는 음성-텍스트 변환 서비스",
    lifespan=lifespan
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 기존 미들웨어들
# ... existing middleware ...

# 라우터 등록
app.include_router(auth.router) # 인증 관련 엔드포인트 분리
app.include_router(transcription.router) # STT 변환 엔드포인트 분리
app.include_router(tokens.router) # 토큰 관리 엔드포인트 분리
app.include_router(users.router) # 사용자 관리 엔드포인트 분리
app.include_router(subscriptions.router) # 구독 관리 엔드포인트 분리
app.include_router(payments.router) # 결제 관리 엔드포인트 분리
app.include_router(service_tokens.router) # 서비스 토큰 관리 엔드포인트 분리
app.include_router(billing.router) # 빌링 엔드포인트 분리
app.include_router(monitoring.router) # 모니터링 엔드포인트 분리

# 기본 엔드포인트들
@app.get("/", summary="서비스 상태 확인")
def read_root():
    return {"message": "STT Service is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False, log_level="debug")