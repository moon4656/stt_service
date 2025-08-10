from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 데이터베이스 URL 설정 (환경변수에서 가져오기, 기본값은 SQLite)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./stt_service.db")

# SQLAlchemy 엔진 생성
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)
    
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스
Base = declarative_base()

# 데이터베이스 모델들
class User(Base):
    """사용자 테이블"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    user_type = Column(String(20), nullable=False)  # "개인" 또는 "조직"
    phone_number = Column(String(20), nullable=True)  # 전화번호 (선택사항)
    password_hash = Column(String(255), nullable=False)  # 암호화된 패스워드
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class TranscriptionRequest(Base):
    """음성 변환 요청 테이블"""
    __tablename__ = "transcription_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)  # API 키 사용자 또는 익명
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)  # 파일 크기 (bytes)
    file_extension = Column(String(10), nullable=False)
    daglo_rid = Column(String(100), nullable=True)  # Daglo API RID
    status = Column(String(50), nullable=False, default="processing")  # processing, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    processing_time = Column(Float, nullable=True)  # 처리 시간 (초)
    error_message = Column(Text, nullable=True)
    
class TranscriptionResponse(Base):
    """음성 변환 응답 테이블"""
    __tablename__ = "transcription_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, nullable=False, index=True)  # TranscriptionRequest.id 참조
    transcribed_text = Column(Text, nullable=True)
    summary_text = Column(Text, nullable=True)  # OpenAI 요약 텍스트
    confidence_score = Column(Float, nullable=True)  # 신뢰도 점수
    language_detected = Column(String(10), nullable=True)  # 감지된 언어
    duration = Column(Float, nullable=True)  # 오디오 길이 (초)
    word_count = Column(Integer, nullable=True)  # 단어 수
    daglo_response_data = Column(Text, nullable=True)  # Daglo API 전체 응답 (JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class APIUsageLog(Base):
    """API 사용 로그 테이블"""
    __tablename__ = "api_usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    api_key_hash = Column(String(64), nullable=True, index=True)
    endpoint = Column(String(100), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    request_size = Column(Integer, nullable=True)  # 요청 크기 (bytes)
    response_size = Column(Integer, nullable=True)  # 응답 크기 (bytes)
    processing_time = Column(Float, nullable=True)  # 처리 시간 (초)
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LoginLog(Base):
    """사용자 로그인 기록 테이블"""
    __tablename__ = "login_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    login_time = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(String(500), nullable=True)
    success = Column(Boolean, nullable=False, default=True)  # 로그인 성공 여부
    failure_reason = Column(String(255), nullable=True)  # 실패 사유 (실패시에만)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class APIToken(Base):
    """API 토큰 테이블"""
    __tablename__ = "api_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)  # User.user_id 참조
    token_id = Column(String(100), unique=True, nullable=False, index=True)  # 토큰 식별자
    token_key = Column(String(255), nullable=False)  # 실제 API 키 (해시화됨)
    token_name = Column(String(100), nullable=True)  # 토큰 이름 (사용자가 지정)
    is_active = Column(Boolean, default=True)  # 토큰 활성화 상태
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)  # 마지막 사용 시간
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 만료 시간 (선택사항)

# 데이터베이스 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 테이블 생성 함수
def create_tables():
    """모든 테이블을 생성합니다."""
    Base.metadata.create_all(bind=engine)

# 데이터베이스 연결 테스트 함수
def test_connection():
    """데이터베이스 연결을 테스트합니다."""
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False