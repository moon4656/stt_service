from sqlalchemy import Date, ForeignKey, Index, UniqueConstraint, create_engine, Column, Integer, String, DateTime, Text, Boolean, Float
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

def generate_request_id():
    """날짜-시간-UUID 형태의 요청 ID를 생성합니다. (한국 시간 기준)"""
    # 한국 시간(KST) 사용 - UTC+9
    from datetime import timezone, timedelta
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst).strftime("%Y%m%d-%H%M%S")
    unique = uuid.uuid4().hex[:8]
    return f"{now}-{unique}"

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
    """사용자 테이블 - 시스템 사용자 정보를 관리하는 테이블
    
    개인 및 조직 사용자의 기본 정보, 인증 정보, 연락처 정보를 저장합니다.
    각 사용자는 고유한 UUID를 가지며, 패스워드는 해시화되어 저장됩니다.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)  # 사용자 고유 식별자 (자동 증가)
    user_id = Column(String(100), unique=True, nullable=False, index=True)  # 사용자 로그인 ID (중복 불가)
    user_uuid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))  # 사용자 고유 UUID (시스템 내부 식별용)
    email = Column(String(255), nullable=False)  # 사용자 이메일 주소
    name = Column(String(100), nullable=False)  # 사용자 실명
    user_type = Column(String(20), nullable=False)  # 사용자 유형 ("개인" 또는 "조직")
    phone_number = Column(String(20), nullable=True)  # 사용자 전화번호 (선택사항)
    password_hash = Column(String(255), nullable=False)  # 해시화된 패스워드 (bcrypt 등)
    is_active = Column(Boolean, default=True)  # 계정 활성화 상태 (비활성화시 로그인 불가)
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 계정 생성 시간
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # 계정 정보 최종 수정 시간

class TranscriptionRequest(Base):
    """음성 변환 요청 테이블"""
    __tablename__ = "transcription_requests"
    
    # 기본 식별자
    request_id = Column(String(50), primary_key=True, index=True, default=generate_request_id)
    user_uuid = Column(String(36), nullable=True, index=True)  # 사용자 UUID 또는 익명
    
    # 파일 정보
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)  # 파일 크기 (bytes)
    file_extension = Column(String(10), nullable=False)
    duration = Column(Float, nullable=True)  # 음성파일 재생 시간 (초)
    
    # 서비스 제공업체
    service_provider = Column(String(50), nullable=True)  # assemblyai, daglo
    client_ip = Column(String(50), nullable=True)  # 클라이언트 IP  
    
    # 처리 상태 및 결과
    status = Column(String(50), nullable=False, default="processing")  # processing, completed, failed
    response_rid = Column(String(100), nullable=True)  # STT API Response RID
    processing_time = Column(Float, nullable=True)  # 처리 시간 (초)
    error_message = Column(Text, nullable=True)
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
class TranscriptionResponse(Base):
    """음성 변환 응답 테이블"""
    __tablename__ = "transcription_responses"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(50), nullable=False, index=True)  # TranscriptionRequest.id 참조
    service_provider = Column(String(50), nullable=True)  # 서비스 제공업체 (assemblyai, daglo)
    
    # 변환 결과 데이터
    transcribed_text = Column(Text, nullable=True)
    summary_text = Column(Text, nullable=True)  # OpenAI 요약 텍스트
    
    # 메타데이터
    confidence_score = Column(Float, nullable=True)  # 신뢰도 점수
    language_detected = Column(String(10), nullable=True)  # 감지된 언어
    duration = Column(Float, nullable=True)  # 오디오 길이 (초)
    audio_duration_minutes = Column(Float, nullable=True)  # 음성 길이 (분 단위, 소숫점 2자리)
    word_count = Column(Integer, nullable=True)  # 단어 수
    tokens_used = Column(Float, nullable=True)  # 사용된 토큰 수 (소숫점 2자리)
    
    # 원본 응답 데이터
    response_data = Column(Text, nullable=True)  # API 전체 응답 (JSON)
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class APIUsageLog(Base):
    """API 사용 로그 테이블 - API 호출 이력과 사용량을 추적하는 테이블
    
    모든 API 엔드포인트 호출에 대한 상세 로그를 기록합니다.
    요청/응답 크기, 처리 시간, 상태 코드, 클라이언트 정보 등을 포함하여
    API 사용 패턴 분석과 과금을 위한 데이터를 제공합니다.
    """
    __tablename__ = "api_usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)  # API 사용 로그 고유 식별자 (자동 증가)
    user_uuid = Column(String(36), nullable=True, index=True)  # 요청한 사용자의 UUID (익명 요청시 NULL)
    api_key_hash = Column(String(64), nullable=True, index=True)  # 사용된 API 키의 해시값 (인증 요청시)
    endpoint = Column(String(100), nullable=False)  # 호출된 API 엔드포인트 경로
    method = Column(String(10), nullable=False)  # HTTP 메소드 (GET, POST, PUT, DELETE 등)
    status_code = Column(Integer, nullable=False)  # HTTP 응답 상태 코드 (200, 404, 500 등)
    request_size = Column(Integer, nullable=True)  # 요청 데이터 크기 (바이트 단위)
    response_size = Column(Integer, nullable=True)  # 응답 데이터 크기 (바이트 단위)
    processing_time = Column(Float, nullable=True)  # 요청 처리 시간 (초 단위, 소수점 포함)
    ip_address = Column(String(45), nullable=True)  # 클라이언트 IP 주소 (IPv4/IPv6 지원)
    user_agent = Column(String(500), nullable=True)  # 클라이언트 User-Agent 헤더 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # API 호출 시간

class LoginLog(Base):
    """로그인 로그 테이블 - 사용자 로그인 이력을 추적하는 테이블
    
    사용자의 로그인 시도를 기록하며, 성공/실패 여부와 실패 사유를 포함합니다.
    보안 모니터링과 사용자 접근 패턴 분석을 위한 데이터를 제공합니다.
    IP 주소와 User-Agent 정보를 통해 접근 환경을 추적할 수 있습니다.
    """
    __tablename__ = "login_logs"
    
    id = Column(Integer, primary_key=True, index=True)  # 로그인 로그 고유 식별자 (자동 증가)
    user_uuid = Column(String(36), nullable=False, index=True)  # 로그인 시도한 사용자의 UUID
    login_time = Column(DateTime(timezone=True), server_default=func.now())  # 로그인 시도 시간
    ip_address = Column(String(45), nullable=True)  # 로그인 시도한 클라이언트 IP 주소 (IPv4/IPv6 지원)
    user_agent = Column(String(500), nullable=True)  # 로그인 시도한 클라이언트 User-Agent 헤더 정보
    success = Column(Boolean, nullable=False, default=True)  # 로그인 성공 여부 (True: 성공, False: 실패)
    failure_reason = Column(String(255), nullable=True)  # 로그인 실패 사유 (잘못된 비밀번호, 계정 비활성화 등)
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 로그 생성 시간

class APIToken(Base):
    """API 토큰 테이블 - 사용자별 API 인증 토큰을 관리하는 테이블
    
    사용자가 생성한 API 키들을 관리하며, 각 토큰의 활성화 상태와 사용 이력을 추적합니다.
    토큰은 해시화되어 저장되며, 만료 시간 설정과 마지막 사용 시간 추적이 가능합니다.
    사용자는 여러 개의 토큰을 가질 수 있으며, 각각에 대해 개별적으로 관리할 수 있습니다.
    """
    __tablename__ = "api_tokens"
    
    id = Column(Integer, primary_key=True, index=True)  # API 토큰 고유 식별자 (자동 증가)
    user_uuid = Column(String(36), nullable=False, index=True)  # 토큰 소유자의 사용자 UUID (User.user_uuid 참조)
    token_id = Column(String(100), unique=True, nullable=False, index=True)  # 토큰 고유 식별자 (중복 불가)
    token_name = Column(String(100), nullable=True)  # 토큰 이름 (사용자가 식별을 위해 지정, 선택사항)
    token_key = Column(String(255), nullable=False)  # 실제 API 키 해시값 (보안을 위해 해시화되어 저장)
    api_key = Column(String(255), nullable=False)  # 신규 컬럼: 평문 API 키
    is_active = Column(Boolean, default=True)  # 토큰 활성화 상태 (비활성화시 API 호출 불가)
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 토큰 생성 시간
    last_used_at = Column(DateTime(timezone=True), nullable=True)  # 토큰 마지막 사용 시간 (사용량 추적용)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 토큰 만료 시간 (NULL시 무제한)

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

class SubscriptionPlan(Base):
    """구독요금 테이블 - 서비스 구독 요금제 정보를 관리하는 테이블
    
    다양한 구독 요금제의 정보를 저장하며, 월 구독 금액과 제공되는 서비스 토큰 수를 관리합니다.
    각 요금제는 고유한 요금 코드를 가지며, 요금제별 상세 설명과 혜택을 포함합니다.
    """
    __tablename__ = "subscription_plans"
    
    id = Column(Integer, primary_key=True, index=True)  # 구독요금 고유 식별자 (자동 증가)
    plan_code = Column(String(50), unique=True, nullable=False, index=True)  # 요금제 코드 (예: BASIC, PREMIUM, ENTERPRISE)
    plan_description = Column(String(500), nullable=False)  # 요금제 상세 설명
    monthly_price = Column(Integer, nullable=False)  # 월 구독 금액 (원 단위)
    monthly_service_tokens = Column(Integer, nullable=False)  # 월 제공 서비스 토큰 수
    per_minute_rate = Column(Integer, nullable=True)  # 분당요금 (원 단위)
    overage_per_minute_rate = Column(Integer, nullable=True)  # 초과분당요금 (원 단위)    
    is_active = Column(Boolean, default=True)  # 요금제 활성화 상태 (비활성화시 신규 가입 불가)
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 요금제 생성 시간
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # 요금제 정보 최종 수정 시간

def generate_payment_id():
    """날짜-순번 형태의 결재 번호를 생성합니다. (한국 시간 기준)"""
    from datetime import timezone, timedelta
    from sqlalchemy import text
    
    # 한국 시간(KST) 사용 - UTC+9
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst).strftime("%Y%m%d")
    
    # 오늘 날짜의 마지막 순번 조회
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT payment_id FROM payments WHERE payment_id LIKE :pattern ORDER BY payment_id DESC LIMIT 1"),
                {"pattern": f"{today}_%"}
            )
            last_payment = result.fetchone()
            
            if last_payment:
                # 마지막 순번에서 1 증가
                last_no = int(last_payment[0].split('_')[1])
                next_no = last_no + 1
            else:
                # 오늘 첫 번째 결재
                next_no = 1
                
        return f"{today}_{next_no:03d}"  # 3자리 순번 (001, 002, ...)
    except:
        # 에러 발생시 기본값
        import random
        return f"{today}_{random.randint(1, 999):03d}"

class Payment(Base):
    """결재 테이블 - 사용자 결재 정보를 관리하는 테이블
    
    사용자의 서비스 이용료 결재 내역을 저장합니다.
    결재번호는 날짜_순번 형식으로 생성되며, 공급가액, 부가세, 합계 금액을 관리합니다.
    각 결재는 특정 사용자와 연결되며, 결재 상태와 이력을 추적할 수 있습니다.
    """
    __tablename__ = "payments"
    
    payment_id = Column(String(50), primary_key=True, index=True, default=generate_payment_id)  # 결재번호 (yyyymmdd_nnn 형식)
    user_uuid = Column(String(36), nullable=False, index=True)  # 결재한 사용자의 UUID (User.user_uuid 참조)
    plan_code = Column(String(50), unique=True, nullable=False, index=True)  # 요금제 코드 (예: BASIC, PREMIUM, ENTERPRISE)
    supply_amount = Column(Integer, nullable=False)  # 공급가액 (원 단위, 부가세 제외)
    vat_amount = Column(Integer, nullable=False)  # 부가세 (원 단위)
    total_amount = Column(Integer, nullable=False)  # 합계 금액 (공급가액 + 부가세)
    payment_status = Column(String(20), nullable=False, default="pending")  # 결재 상태 (pending, completed, failed, cancelled)
    payment_method = Column(String(50), nullable=True)  # 결재 수단 (card, bank_transfer, etc.)
    payment_type = Column(String(50), nullable=False, default="subscription")  # 결재 구분 (subscription, overage, token_purchase, one_time)    
    external_payment_id = Column(String(100), nullable=True)  # 외부 결재 시스템 ID (PG사 거래번호 등)
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 결재 생성 시간
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # 결재 정보 최종 수정 시간
    completed_at = Column(DateTime(timezone=True), nullable=True)  # 결재 완료 시간

    # 구독결재내역 ( 결재번호, 단가, 인원수, 금액, 생성일자, 수정일자 )
    # 초과토큰결재내역 ( 결재번호, 토큰수, 분당요금, 초과분당요금, 금액, 생성일자, 수정일자 )
    # 구독결재내역
    # subscription_payment = relationship("SubscriptionPayment", back_populates="payment", uselist=False)
    # 초과토큰결재내역
    # overage_payment = relationship("OveragePayment", back_populates="payment", uselist=False)

class MonthlyBilling(Base):
    """월별 빌링 테이블 - 사용자별 월별 사용량과 요금을 관리하는 테이블
    
    매월 사용자의 STT 서비스 사용량과 요금을 집계하여 저장합니다.
    기본 구독료, 초과 사용료, 총 청구 금액 등을 포함하며,
    월별 사용 통계와 과금 내역을 추적할 수 있습니다.
    """
    __tablename__ = "monthly_billings"
    
    id = Column(Integer, primary_key=True, index=True)  # 월별 빌링 고유 식별자 (자동 증가)
    user_uuid = Column(String(36), nullable=False, index=True)  # 사용자 UUID (User.user_uuid 참조)
    billing_year = Column(Integer, nullable=False)  # 청구 연도 (예: 2024)
    billing_month = Column(Integer, nullable=False)  # 청구 월 (1-12)
    plan_code = Column(String(50), nullable=False)  # 적용된 요금제 코드
    
    # 사용량 정보
    total_minutes_used = Column(Float, nullable=False, default=0.0)  # 총 사용 시간 (분 단위)
    included_minutes = Column(Float, nullable=False, default=0.0)  # 요금제 포함 시간 (분 단위)
    excess_minutes = Column(Float, nullable=False, default=0.0)  # 초과 사용 시간 (분 단위)
    total_requests = Column(Integer, nullable=False, default=0)  # 총 요청 건수
    
    # 요금 정보
    base_subscription_fee = Column(Integer, nullable=False, default=0)  # 기본 구독료 (원 단위)
    per_minute_rate = Column(Integer, nullable=True)  # 분당 기본 요금 (원 단위)
    excess_per_minute_rate = Column(Integer, nullable=True)  # 초과분당 요금 (원 단위)
    excess_usage_fee = Column(Integer, nullable=False, default=0)  # 초과 사용료 (원 단위)
    
    # 청구 금액
    subtotal_amount = Column(Integer, nullable=False, default=0)  # 소계 (공급가액)
    vat_amount = Column(Integer, nullable=False, default=0)  # 부가세 (10%)
    total_billing_amount = Column(Integer, nullable=False, default=0)  # 총 청구 금액
    
    # 결제 상태
    billing_status = Column(String(20), nullable=False, default="pending")  # 청구 상태 (pending, billed, paid, overdue)
    payment_due_date = Column(Date, nullable=True)  # 결제 기한
    paid_at = Column(DateTime(timezone=True), nullable=True)  # 결제 완료 시간
    
    # 메타데이터
    billing_period_start = Column(Date, nullable=False)  # 청구 기간 시작일
    billing_period_end = Column(Date, nullable=False)  # 청구 기간 종료일
    generated_at = Column(DateTime(timezone=True), server_default=func.now())  # 청구서 생성 시간
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 레코드 생성 시간
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # 레코드 수정 시간
    
    # 복합 인덱스 (사용자별 월별 유니크)
    __table_args__ = (
        Index('idx_user_billing_period', 'user_uuid', 'billing_year', 'billing_month'),
        UniqueConstraint('user_uuid', 'billing_year', 'billing_month', name='uq_user_monthly_billing'),
    )

def generate_monthly_billing_id():
    """월별 빌링 ID를 생성합니다. (YYYYMM-사용자UUID 형식)"""
    from datetime import datetime, timezone, timedelta
    
    # 한국 시간(KST) 사용 - UTC+9
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    year_month = now.strftime("%Y%m")
    
    return f"BILL-{year_month}"

class SubscriptionPayment(Base):
    """구독결재내역 테이블 - 구독 요금제 결재 상세 정보"""
    __tablename__ = "subscription_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String(50), ForeignKey('payments.payment_id'), nullable=False)
    plan_code = Column(String(50), nullable=False)  # 요금제 코드
    unit_price = Column(Integer, nullable=False)  # 단가
    quantity = Column(Integer, nullable=False, default=1)  # 인원수
    amount = Column(Integer, nullable=False)  # 금액
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class TokenPayment(Base):
    """서비스토큰결재내역 테이블 - 토큰 구매 결재 상세 정보"""
    __tablename__ = "token_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String(50), ForeignKey('payments.payment_id'), nullable=False)
    token_quantity = Column(Integer, nullable=False)  # 토큰 수량
    token_unit_price = Column(Integer, nullable=False)  # 토큰 단가
    amount = Column(Integer, nullable=False)  # 총 금액
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


    
    
