from unicodedata import numeric
from sqlalchemy import Date, ForeignKey, Index, UniqueConstraint, create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, CheckConstraint, NUMERIC
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
    __table_args__ = {'comment': '사용자 정보를 관리하는 테이블'}
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True, comment="사용자일련번호")  # 사용자 고유 식별자 (자동 증가)
    user_id = Column(String(100), unique=True, nullable=False, index=True, comment="사용자아이디")  # 사용자 로그인 ID (중복 불가)
    user_uuid = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()), comment="사용자고유식별자")  # 사용자 고유 UUID (시스템 내부 식별용)
    email = Column(String(255), nullable=False, comment="이메일주소")  # 사용자 이메일 주소
    name = Column(String(100), nullable=False, comment="사용자명")  # 사용자 실명
    user_type = Column(String(20), nullable=False, comment="사용자유형")  # 사용자 유형 ("개인" 또는 "조직")
    phone_number = Column(String(20), nullable=True, comment="전화번호")  # 사용자 전화번호 (선택사항)
    password_hash = Column(String(255), nullable=False, comment="비밀번호해시")  # 해시화된 패스워드 (bcrypt 등)
    is_active = Column(Boolean, default=True, comment="활성화상태")  # 계정 활성화 상태 (비활성화시 로그인 불가)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")  # 계정 생성 시간
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")  # 계정 정보 최종 수정 시간

class TranscriptionRequest(Base):
    """음성 변환 요청 테이블"""
    __tablename__ = "transcription_requests"
    __table_args__ = {'comment': '음성 파일의 텍스트 변환 요청 정보를 저장하는 테이블'}
    
    # 기본 식별자
    request_id = Column(String(50), primary_key=True, index=True, default=generate_request_id, comment="요청식별자")
    user_uuid = Column(String(36), nullable=True, index=True, comment="사용자고유식별자")  # 사용자 UUID 또는 익명
    
    # 파일 정보
    filename = Column(String(255), nullable=False, comment="파일명")
    file_size = Column(Integer, nullable=False, comment="파일크기")  # 파일 크기 (bytes)
    file_extension = Column(String(10), nullable=False, comment="파일확장자")
    duration = Column(NUMERIC(10,2), nullable=True, comment="재생시간")  # 음성파일 재생 시간 (초)
    
    # 서비스 제공업체
    service_provider = Column(String(50), nullable=True, comment="서비스제공업체")  # assemblyai, daglo
    client_ip = Column(String(50), nullable=True, comment="클라이언트IP주소")  # 클라이언트 IP  
    
    # 처리 상태 및 결과
    status = Column(String(50), nullable=False, default="processing", comment="처리상태")  # processing, completed, failed
    response_rid = Column(String(100), nullable=True, comment="응답식별자")  # STT API Response RID
    processing_time = Column(Float, nullable=True, comment="처리시간")  # 처리 시간 (초)
    error_message = Column(Text, nullable=True, comment="오류메시지")
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="완료일시")
    
class TranscriptionResponse(Base):
    """음성 변환 응답 테이블"""
    __tablename__ = "transcription_responses"
    __table_args__ = {'comment': '음성 파일의 텍스트 변환 결과를 저장하는 테이블'}
    
    # 기본 정보
    id = Column(Integer, primary_key=True, index=True, comment="응답일련번호")
    request_id = Column(String(50), nullable=False, index=True, comment="요청식별자")  # 
    service_provider = Column(String(50), nullable=True, comment="서비스제공업체")  # 서비스 제공업체 (assemblyai, daglo)
    
    # 변환 결과 데이터
    transcribed_text = Column(Text, nullable=True, comment="변환텍스트")
    summary_text = Column(Text, nullable=True, comment="요약텍스트")  # OpenAI 요약 텍스트
    
    # 메타데이터
    confidence_score = Column(Float, nullable=True, comment="신뢰도점수")  # 신뢰도 점수
    language_detected = Column(String(10), nullable=True, comment="감지언어")  # 감지된 언어
    duration = Column(Float, nullable=True, comment="오디오길이")  # 오디오 길이 (초)
    audio_duration_minutes = Column(Float, nullable=True, comment="음성길이분")  # 음성 길이 (분 단위, 소숫점 2자리)
    word_count = Column(Integer, nullable=True, comment="단어수")  # 단어 수
    tokens_used = Column(Float, nullable=True, comment="사용토큰수")  # 사용된 토큰 수 (소숫점 2자리)
    
    # 원본 응답 데이터
    response_data = Column(Text, nullable=True, comment="원본응답데이터")  # API 전체 응답 (JSON)
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")

class APIUsageLog(Base):
    """API 사용 로그 테이블 - API 호출 이력과 사용량을 추적하는 테이블
    
    모든 API 엔드포인트 호출에 대한 상세 로그를 기록합니다.
    요청/응답 크기, 처리 시간, 상태 코드, 클라이언트 정보 등을 포함하여
    API 사용 패턴 분석과 과금을 위한 데이터를 제공합니다.
    """
    __tablename__ = "api_usage_logs"
    __table_args__ = {'comment': 'API 호출 이력과 사용량을 추적하는 테이블'}
    
    id = Column(Integer, primary_key=True, index=True, comment="API사용로그일련번호")  # API 사용 로그 고유 식별자 (자동 증가)
    user_uuid = Column(String(36), nullable=True, index=True, comment="사용자고유식별자")  # 요청한 사용자의 UUID (익명 요청시 NULL)
    api_key_hash = Column(String(64), nullable=True, index=True, comment="API키해시값")  # 사용된 API 키의 해시값 (인증 요청시)
    endpoint = Column(String(100), nullable=False, comment="API엔드포인트")  # 호출된 API 엔드포인트 경로
    method = Column(String(10), nullable=False, comment="HTTP메소드")  # HTTP 메소드 (GET, POST, PUT, DELETE 등)
    status_code = Column(Integer, nullable=False, comment="HTTP상태코드")  # HTTP 응답 상태 코드 (200, 404, 500 등)
    request_size = Column(Integer, nullable=True, comment="요청데이터크기")  # 요청 데이터 크기 (바이트 단위)
    response_size = Column(Integer, nullable=True, comment="응답데이터크기")  # 응답 데이터 크기 (바이트 단위)
    processing_time = Column(Float, nullable=True, comment="처리시간")  # 요청 처리 시간 (초 단위, 소수점 포함)
    ip_address = Column(String(45), nullable=True, comment="클라이언트IP주소")  # 클라이언트 IP 주소 (IPv4/IPv6 지원)
    user_agent = Column(String(500), nullable=True, comment="사용자에이전트")  # 클라이언트 User-Agent 헤더 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")  # API 호출 시간

class LoginLog(Base):
    """로그인 로그 테이블 - 사용자 로그인 이력을 추적하는 테이블
    
    사용자의 로그인 시도를 기록하며, 성공/실패 여부와 실패 사유를 포함합니다.
    보안 모니터링과 사용자 접근 패턴 분석을 위한 데이터를 제공합니다.
    IP 주소와 User-Agent 정보를 통해 접근 환경을 추적할 수 있습니다.
    """
    __tablename__ = "login_logs"
    __table_args__ = {'comment': '사용자 로그인 이력을 추적하는 테이블'}
    
    id = Column(Integer, primary_key=True, index=True, comment="로그인로그일련번호")  # 로그인 로그 고유 식별자 (자동 증가)
    user_uuid = Column(String(36), nullable=False, index=True, comment="사용자고유식별자")  # 로그인 시도한 사용자의 UUID
    login_time = Column(DateTime(timezone=True), server_default=func.now(), comment="로그인시도시간")  # 로그인 시도 시간
    ip_address = Column(String(45), nullable=True, comment="클라이언트IP주소")  # 로그인 시도한 클라이언트 IP 주소 (IPv4/IPv6 지원)
    user_agent = Column(String(500), nullable=True, comment="사용자에이전트")  # 로그인 시도한 클라이언트 User-Agent 헤더 정보
    success = Column(Boolean, nullable=False, default=True, comment="로그인성공여부")  # 로그인 성공 여부 (True: 성공, False: 실패)
    failure_reason = Column(String(255), nullable=True, comment="실패사유")  # 로그인 실패 사유 (잘못된 비밀번호, 계정 비활성화 등)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")  # 로그 생성 시간

class APIToken(Base):
    """API 토큰 테이블 - 사용자별 API 인증 토큰을 관리하는 테이블
    
    사용자가 생성한 API 키들을 관리하며, 각 토큰의 활성화 상태와 사용 이력을 추적합니다.
    토큰은 해시화되어 저장되며, 만료 시간 설정과 마지막 사용 시간 추적이 가능합니다.
    사용자는 여러 개의 토큰을 가질 수 있으며, 각각에 대해 개별적으로 관리할 수 있습니다.
    """
    __tablename__ = "api_tokens"
    __table_args__ = {'comment': '사용자별 API 인증 토큰을 관리하는 테이블'}
    
    id = Column(Integer, primary_key=True, index=True, comment="API토큰일련번호")  # API 토큰 고유 식별자 (자동 증가)
    user_uuid = Column(String(36), nullable=False, index=True, comment="사용자고유식별자")  # 토큰 소유자의 사용자 UUID (User.user_uuid 참조)
    token_id = Column(String(100), unique=True, nullable=False, index=True, comment="토큰식별자")  # 토큰 고유 식별자 (중복 불가)
    token_name = Column(String(100), nullable=True, comment="토큰명")  # 토큰 이름 (사용자가 식별을 위해 지정, 선택사항)
    token_key = Column(String(255), nullable=False, comment="토큰키해시값")  # 실제 API 키 해시값 (보안을 위해 해시화되어 저장)
    api_key = Column(String(255), nullable=False, comment="API키")  # 신규 컬럼: 평문 API 키
    is_active = Column(Boolean, default=True, comment="활성화상태")  # 토큰 활성화 상태 (비활성화시 API 호출 불가)
    expires_at = Column(DateTime(timezone=True), nullable=True, comment="만료일시")  # 토큰 만료 시간 (NULL시 무제한)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")  # 토큰 생성 시간
    last_used_at = Column(DateTime(timezone=True), nullable=True, comment="마지막사용일시")  # 토큰 마지막 사용 시간 (사용량 추적용)

# 데이터베이스 세션 의존성
def get_db():
    """데이터베이스 세션 생성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 테이블 생성 함수
def create_tables():
    """모든 테이블 생성"""
    Base.metadata.create_all(bind=engine)

# 데이터베이스 연결 테스트 함수
def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

def update_service_token_usage(db, user_uuid: str, tokens_used: float, request_id: str) -> bool:
    """
    서비스 토큰 사용량을 업데이트하고 사용 이력을 기록합니다.
    update lock을 방지하기 위해 적절한 트랜잭션 처리를 수행합니다.
    
    Args:
        db: 데이터베이스 세션
        user_uuid: 사용자 UUID
        tokens_used: 사용된 토큰 수량 (분 단위)
        request_id: 요청 고유 식별자
    
    Returns:
        bool: 업데이트 성공 여부
    """
    import logging
    from sqlalchemy.exc import IntegrityError, OperationalError
    from sqlalchemy.orm.exc import StaleDataError
    import time
    import random
    
    logger = logging.getLogger(__name__)
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # 트랜잭션 시작
            with db.begin():
                # 활성 상태인 서비스 토큰 조회 (FOR UPDATE로 행 잠금)
                service_token = db.query(ServiceToken).filter(
                    ServiceToken.user_uuid == user_uuid,
                    ServiceToken.status == 'active',
                    ServiceToken.token_expiry_date >= func.current_date()
                ).with_for_update().first()
                
                if not service_token:
                    logger.warning(f"⚠️ 활성 서비스 토큰을 찾을 수 없음 - 사용자: {user_uuid}")
                    return False
                
                # 토큰 잔량 확인
                remaining_tokens = service_token.quota_tokens - service_token.used_tokens
                if remaining_tokens < tokens_used:
                    logger.warning(f"⚠️ 토큰 잔량 부족 - 잔량: {remaining_tokens}, 요청: {tokens_used}")
                    return False
                
                # 토큰 사용량 업데이트
                service_token.used_tokens += tokens_used
                service_token.updated_at = func.now()
                
                # 사용 이력 기록 (중복 방지를 위해 request_id 사용)
                existing_usage = db.query(TokenUsageHistory).filter(
                    TokenUsageHistory.request_id == request_id
                ).first()
                
                if not existing_usage:
                    usage_history = TokenUsageHistory(
                        token_id=str(service_token.id),
                        used_tokens=tokens_used,
                        request_id=request_id
                    )
                    db.add(usage_history)
                
                # 변경사항 커밋
                db.flush()
                
                logger.info(f"✅ 서비스 토큰 사용량 업데이트 완료 - 사용자: {user_uuid}, 사용량: {tokens_used}, 잔량: {remaining_tokens - tokens_used}")
                return True
                
        except (IntegrityError, OperationalError, StaleDataError) as e:
            # 동시성 관련 오류 발생 시 재시도
            logger.warning(f"⚠️ 토큰 업데이트 동시성 오류 (시도 {attempt + 1}/{max_retries}): {str(e)}")
            db.rollback()
            
            if attempt < max_retries - 1:
                # 지수 백오프와 지터를 사용한 재시도 대기
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
            else:
                logger.error(f"❌ 토큰 업데이트 최대 재시도 횟수 초과: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 토큰 업데이트 중 예상치 못한 오류: {str(e)}")
            db.rollback()
            return False
    
    return False

class SubscriptionPlan(Base):
    """구독요금 테이블 - 서비스 구독 요금제 정보를 관리하는 테이블
    
    다양한 구독 요금제의 정보를 저장하며, 월 구독 금액과 제공되는 서비스 토큰 수를 관리합니다.
    각 요금제는 고유한 요금 코드를 가지며, 요금제별 상세 설명과 혜택을 포함합니다.
    """
    __tablename__ = "subscription_plans"
    __table_args__ = {'comment': '서비스 구독 요금제 정보를 관리하는 테이블'}
    
    id = Column(Integer, primary_key=True, index=True, comment="구독요금일련번호")  # 구독요금 고유 식별자 (자동 증가)
    plan_code = Column(String(50), nullable=False, unique=True, index=True, comment="요금제코드")  # 요금제 코드 (예: BASIC, PREMIUM, ENTERPRISE)
    plan_description = Column(String(500), nullable=False, comment="요금제설명")  # 요금제 상세 설명
    monthly_price = Column(Integer, nullable=False, comment="월구독금액")  # 월 구독 금액 (원 단위)
    monthly_service_tokens = Column(Integer, nullable=False, comment="월제공서비스토큰수")  # 월 제공 서비스 토큰 수
    per_minute_rate = Column(Integer, nullable=True, comment="분당요금")  # 분당요금 (원 단위)
    overage_per_minute_rate = Column(Integer, nullable=True, comment="초과분당요금")  # 초과분당요금 (원 단위)    
    is_active = Column(Boolean, default=True, comment="활성화상태")  # 요금제 활성화 상태 (비활성화시 신규 가입 불가)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")  # 요금제 생성 시간
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")  # 요금제 정보 최종 수정 시간

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
    __table_args__ = {'comment': '사용자 결재 정보를 관리하는 테이블'}
    
    payment_id = Column(String(50), primary_key=True, index=True, default=generate_payment_id, comment="결재번호")  # 결재번호 (yyyymmdd_nnn 형식)
    user_uuid = Column(String(36), nullable=False, index=True, comment="사용자고유식별자")  # 결재한 사용자의 UUID (User.user_uuid 참조)
    plan_code = Column(String(50), nullable=False, index=True, comment="요금제코드")  # 요금제 코드 (예: BASIC, PREMIUM, ENTERPRISE)
    supply_amount = Column(Integer, nullable=False, comment="공급가액")  # 공급가액 (원 단위, 부가세 제외)
    vat_amount = Column(Integer, nullable=False, comment="부가세")  # 부가세 (원 단위)
    total_amount = Column(Integer, nullable=False, comment="합계금액")  # 합계 금액 (공급가액 + 부가세)
    payment_status = Column(String(20), nullable=False, default="pending", comment="결재상태")  # 결재 상태 (pending, completed, failed, cancelled)
    payment_method = Column(String(50), nullable=True, comment="결재수단")  # 결재 수단 (card, bank_transfer, etc.)
    payment_type = Column(String(50), nullable=False, default="subscription", comment="결재구분")  # 결재 구분 (subscription, overage, token_purchase, one_time)    
    external_payment_id = Column(String(100), nullable=True, comment="외부결재시스템ID")  # 외부 결재 시스템 ID (PG사 거래번호 등)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")  # 결재 생성 시간
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")  # 결재 정보 최종 수정 시간
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="완료일시")  # 결재 완료 시간

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
    
    id = Column(Integer, primary_key=True, index=True, comment="월별빌링일련번호")  # 월별 빌링 고유 식별자 (자동 증가)
    user_uuid = Column(String(36), nullable=False, index=True, comment="사용자고유식별자")  # 사용자 UUID (User.user_uuid 참조)
    billing_year = Column(Integer, nullable=False, comment="청구연도")  # 청구 연도 (예: 2024)
    billing_month = Column(Integer, nullable=False, comment="청구월")  # 청구 월 (1-12)
    plan_code = Column(String(50), nullable=False, comment="요금제코드")  # 적용된 요금제 코드
    
    # 사용량 정보
    total_minutes_used = Column(Float, nullable=False, default=0.0, comment="총사용시간")  # 총 사용 시간 (분 단위)
    included_minutes = Column(Float, nullable=False, default=0.0, comment="포함시간")  # 요금제 포함 시간 (분 단위)
    excess_minutes = Column(Float, nullable=False, default=0.0, comment="초과사용시간")  # 초과 사용 시간 (분 단위)
    total_requests = Column(Integer, nullable=False, default=0, comment="총요청건수")  # 총 요청 건수
    
    # 요금 정보
    base_subscription_fee = Column(Integer, nullable=False, default=0, comment="기본구독료")  # 기본 구독료 (원 단위)
    per_minute_rate = Column(Integer, nullable=True, comment="분당기본요금")  # 분당 기본 요금 (원 단위)
    excess_per_minute_rate = Column(Integer, nullable=True, comment="초과분당요금")  # 초과분당 요금 (원 단위)
    excess_usage_fee = Column(Integer, nullable=False, default=0, comment="초과사용료")  # 초과 사용료 (원 단위)
    
    # 청구 금액
    subtotal_amount = Column(Integer, nullable=False, default=0, comment="소계금액")  # 소계 (공급가액)
    vat_amount = Column(Integer, nullable=False, default=0, comment="부가세")  # 부가세 (10%)
    total_billing_amount = Column(Integer, nullable=False, default=0, comment="총청구금액")  # 총 청구 금액
    
    # 결제 상태
    billing_status = Column(String(20), nullable=False, default="pending", comment="청구상태")  # 청구 상태 (pending, billed, paid, overdue)
    payment_due_date = Column(Date, nullable=True, comment="결제기한")  # 결제 기한
    paid_at = Column(DateTime(timezone=True), nullable=True, comment="결제완료시간")  # 결제 완료 시간
    
    # 메타데이터
    billing_period_start = Column(Date, nullable=False, comment="청구기간시작일")  # 청구 기간 시작일
    billing_period_end = Column(Date, nullable=False, comment="청구기간종료일")  # 청구 기간 종료일
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), comment="청구서생성시간")  # 청구서 생성 시간
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")  # 레코드 생성 시간
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")  # 레코드 수정 시간
    
    # 복합 인덱스 (사용자별 월별 유니크)
    __table_args__ = (
        Index('idx_user_billing_period', 'user_uuid', 'billing_year', 'billing_month'),
        UniqueConstraint('user_uuid', 'billing_year', 'billing_month', name='uq_user_monthly_billing'),
        {'comment': '사용자별 월별 사용량과 요금을 관리하는 테이블'}
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
    __table_args__ = {'comment': '구독 요금제 결재 상세 정보를 저장하는 테이블'}
    
    id = Column(Integer, primary_key=True, index=True, comment="구독결제일련번호")
    payment_id = Column(String(50), ForeignKey('payments.payment_id'), nullable=False, comment="결제식별자")
    plan_code = Column(String(50), nullable=False, comment="요금제코드")  # 요금제 코드
    unit_price = Column(Integer, nullable=False, comment="단가")  # 단가
    quantity = Column(Integer, nullable=False, default=1, comment="인원수")  # 인원수
    amount = Column(Integer, nullable=False, comment="금액")  # 금액
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")

class TokenPayment(Base):
    """서비스토큰결재내역 테이블 - 토큰 구매 결재 상세 정보"""
    __tablename__ = "token_payments"
    __table_args__ = {'comment': '토큰 구매 결재 상세 정보를 저장하는 테이블'}
    
    id = Column(Integer, primary_key=True, index=True, comment="토큰결제일련번호")
    payment_id = Column(String(50), ForeignKey('payments.payment_id'), nullable=False, comment="결제식별자")
    token_quantity = Column(Integer, nullable=False, comment="토큰수량")  # 토큰 수량
    token_unit_price = Column(Integer, nullable=False, comment="토큰단가")  # 토큰 단가
    amount = Column(Integer, nullable=False, comment="총금액")  # 총 금액
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")

class OveragePayment(Base):
    """서비스초과결재 테이블 - 서비스 초과 사용량에 대한 결재 상세 정보
    
    사용자가 구독 요금제의 포함 한도를 초과하여 사용한 서비스에 대한 결재 내역을 저장합니다.
    초과 사용량, 단가, 초과 단가 등의 정보를 포함하며, 초과 사용료 계산의 기준이 됩니다.
    """
    __tablename__ = "overage_payments"
    
    id = Column(Integer, primary_key=True, index=True, comment="초과결제일련번호")  # 서비스초과결재 고유 식별자 (자동 증가)
    payment_id = Column(String(50), ForeignKey('payments.payment_id'), nullable=False, index=True, comment="결제식별자")  # 결재번호 (payments.payment_id 참조)
    plan_code = Column(String(50), nullable=False, index=True, comment="요금제코드")  # 요금제 코드 (예: BASIC, PREMIUM, ENTERPRISE)
    unit_price = Column(Integer, nullable=False, comment="기본단가")  # 기본 단가 (원 단위, 분당 기본 요금)
    overage_unit_price = Column(Integer, nullable=False, comment="초과단가")  # 초과 단가 (원 단위, 분당 초과 요금)
    overage_tokens = Column(Float, nullable=False, comment="초과토큰시간")  # 초과 토큰/시간 (분 단위)
    amount = Column(Integer, nullable=False, comment="총초과사용료")  # 총 초과 사용료 금액 (원 단위)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")  # 레코드 생성 시간
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")  # 레코드 수정 시간
    
    # 인덱스 추가 (결재번호별 조회 최적화)
    __table_args__ = (
        Index('idx_overage_payment_id', 'payment_id'),
        Index('idx_overage_plan_code', 'plan_code'),
        {'comment': '서비스 초과 사용량에 대한 결재 상세 정보를 저장하는 테이블'}
    )

class ServiceToken(Base):
    """서비스토큰 테이블 - 사용자별 토큰 할당 및 사용량 관리
    
    사용자에게 할당된 서비스 토큰의 정보를 관리하는 테이블입니다.
    구독으로 할당받은 토큰량, 누적 사용량, 토큰 만료일, 상태 등을 추적합니다.
    """
    __tablename__ = "service_tokens"
    
    id = Column(Integer, primary_key=True, index=True, comment="서비스토큰일련번호")  # 서비스토큰 고유 식별자 (자동 증가)
    user_uuid = Column(String(36), ForeignKey('users.user_uuid'), nullable=False, index=True, comment="사용자고유식별자")  # 사용자 UUID (users.user_uuid 참조)
    quota_tokens = Column(NUMERIC(10,2), nullable=False, default=0.0, comment="구독할당토큰")  # 구독할당토큰 (분 단위)
    used_tokens = Column(NUMERIC(10,2), nullable=False, default=0.0, comment="누적사용토큰")  # 누적사용토큰 (분 단위)
    token_expiry_date = Column(Date, nullable=False, comment="토큰종료일자")  # 토큰종료일자
    status = Column(String(20), nullable=False, default='active', comment="상태")  # 상태 (active, expired, suspended)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")  # 레코드 생성 시간
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")  # 레코드 수정 시간
    
    # 제약조건 및 인덱스
    __table_args__ = (
        CheckConstraint('quota_tokens >= 0', name='check_quota_tokens_positive'),  # 구독할당토큰은 0 이상
        CheckConstraint('used_tokens >= 0', name='check_used_tokens_positive'),  # 누적사용토큰은 0 이상
        CheckConstraint("status IN ('active', 'expired', 'suspended')", name='check_status_valid'),  # 상태 값 제한
        Index('idx_service_token_user_uuid', 'user_uuid'),  # 사용자별 조회 최적화
        Index('idx_service_token_status', 'status'),  # 상태별 조회 최적화
        Index('idx_service_token_expiry', 'token_expiry_date'),  # 만료일별 조회 최적화
        # UniqueConstraint('user_uuid', 'token_id', name='uq_user_token'),  # 사용자별 토큰ID 중복 방지 - token_id 컬럼이 없으므로 주석 처리
        {'comment': '사용자별 토큰 할당 및 사용량을 관리하는 테이블'}
    )


class TokenUsageHistory(Base):
    """토큰사용내역 테이블 - 토큰 사용 이력 추적
    
    각 STT 요청에 대한 토큰 사용량을 기록하는 테이블입니다.
    요청별 토큰 소비량, 요청ID, 생성일자 등을 추적합니다.
    """
    __tablename__ = "token_usage_history"
    
    id = Column(Integer, primary_key=True, index=True, comment="토큰사용내역일련번호")  # 사용내역 고유 식별자 (자동 증가)
    token_id = Column(String(100), nullable=False, index=True, comment="토큰식별자")  # 토큰 식별자
    used_tokens = Column(NUMERIC(10,2), nullable=False, comment="사용토큰수량")  # 사용토큰 (분 단위, 소숫점 2자리)
    request_id = Column(String(100), nullable=False, unique=True, index=True, comment="요청고유식별자")  # 요청 고유 ID (중복 방지)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")  # 생성일자
    
    # 제약조건 및 인덱스
    __table_args__ = (
        CheckConstraint('used_tokens >= 0', name='check_used_tokens_positive_history'),  # 사용토큰은 0 이상
        Index('idx_token_usage_token_id', 'token_id'),  # 토큰ID별 조회 최적화
        Index('idx_token_usage_created_at', 'created_at'),  # 생성일자별 조회 최적화
        Index('idx_token_usage_request_id', 'request_id'),  # 요청ID별 조회 최적화
        {'comment': '토큰 사용 이력을 추적하는 테이블'}
    )


class SubscriptionMaster(Base):
    """구독마스터 테이블 - 사용자별 현재 구독 상태 관리
    
    각 사용자의 현재 활성화된 구독 정보를 관리하는 마스터 테이블입니다.
    사용자당 하나의 활성 구독만 존재하며, 구독 변경 시 이 테이블이 업데이트됩니다.
    """
    __tablename__ = "subscription_master"
    
    id = Column(Integer, primary_key=True, index=True, comment="구독마스터일련번호")  # 구독마스터 고유 식별자 (자동 증가)
    user_uuid = Column(String(36), ForeignKey('users.user_uuid'), nullable=False, unique=True, index=True, comment="사용자고유식별자")  # 사용자 UUID (users.user_uuid 참조, 유니크)
    subscription_id = Column(String(100), nullable=False, unique=True, index=True, comment="구독식별자")  # 구독 고유 식별자
    
    # 구독 정보
    plan_code = Column(String(50), ForeignKey('subscription_plans.plan_code'), nullable=False, index=True, comment="요금제코드")  # 현재 요금제 코드 (subscription_plans.plan_code 참조)
    unit_price = Column(Integer, nullable=False, comment="단가")  # 단가
    quantity = Column(Integer, nullable=False, default=1, comment="인원수")  # 인원수
    amount = Column(Integer, nullable=False, comment="금액")  # 금액
    subscription_status = Column(String(20), nullable=False, default='active', comment="구독상태")  # 구독 상태 (active, suspended, cancelled, expired)

    # 구독 기간
    subscription_start_date = Column(Date, nullable=False, comment="구독시작일")  # 구독 시작일
    subscription_end_date = Column(Date, nullable=True, comment="구독종료일")  # 구독 종료일 (무제한인 경우 NULL)
    next_billing_date = Column(Date, nullable=True, comment="다음결제일")  # 다음 결제 예정일
    
    # 자동 갱신 설정
    auto_renewal = Column(Boolean, nullable=False, default=True, comment="자동갱신여부")  # 자동 갱신 여부
    renewal_plan_code = Column(String(50), nullable=True, comment="갱신요금제코드")  # 갱신 시 적용할 요금제 (NULL이면 현재 요금제로 갱신)
    
    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")  # 레코드 생성 시간
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")  # 레코드 수정 시간
    
    # 제약조건 및 인덱스
    __table_args__ = (
        CheckConstraint("subscription_status IN ('active', 'suspended', 'cancelled', 'expired')", name='check_subscription_status_valid'),  # 구독 상태 값 제한
        CheckConstraint('subscription_start_date <= subscription_end_date OR subscription_end_date IS NULL', name='check_subscription_dates_valid'),  # 시작일 <= 종료일
        Index('idx_subscription_master_user_uuid', 'user_uuid'),  # 사용자별 조회 최적화
        Index('idx_subscription_master_plan_code', 'plan_code'),  # 요금제별 조회 최적화
        Index('idx_subscription_master_status', 'subscription_status'),  # 상태별 조회 최적화
        Index('idx_subscription_master_billing_date', 'next_billing_date'),  # 결제일별 조회 최적화
        {'comment': '사용자별 현재 구독 상태를 관리하는 마스터 테이블'}
    )


class SubscriptionChangeHistory(Base):
    """구독변경이력 테이블 - 구독 변경 이력 추적
    
    사용자의 구독 변경 이력을 시간순으로 기록하는 테이블입니다.
    구독 생성, 요금제 변경, 일시정지, 해지 등 모든 구독 관련 변경사항을 추적합니다.
    """
    __tablename__ = "subscription_change_history"
    
    id = Column(Integer, primary_key=True, index=True, comment="구독변경이력일련번호")  # 변경이력 고유 식별자 (자동 증가)
    user_uuid = Column(String(36), ForeignKey('users.user_uuid'), nullable=False, index=True, comment="사용자고유식별자")  # 사용자 UUID (users.user_uuid 참조)
    subscription_id = Column(String(100), nullable=False, index=True, comment="구독식별자")  # 구독 식별자
    change_id = Column(String(100), nullable=False, unique=True, index=True, comment="변경식별자")  # 변경 고유 식별자
    
    # 변경 정보
    change_type = Column(String(30), nullable=False, comment="변경유형")  # 변경 유형 (create, upgrade, downgrade, suspend, resume, cancel, expire, renew)
    change_reason = Column(String(100), nullable=True, comment="변경사유")  # 변경 사유
    
    # 변경 전후 정보
    previous_plan_code = Column(String(50), nullable=True, comment="이전요금제코드")  # 변경 전 요금제 코드
    new_plan_code = Column(String(50), nullable=True, comment="신규요금제코드")  # 변경 후 요금제 코드
    previous_status = Column(String(20), nullable=True, comment="이전구독상태")  # 변경 전 구독 상태
    new_status = Column(String(20), nullable=False, comment="신규구독상태")  # 변경 후 구독 상태
    
    # 변경 적용 일시
    effective_date = Column(Date, nullable=False, comment="적용일자")  # 변경 적용 일자
    change_requested_at = Column(DateTime(timezone=True), nullable=False, comment="변경요청일시")  # 변경 요청 일시
    change_processed_at = Column(DateTime(timezone=True), server_default=func.now(), comment="변경처리일시")  # 변경 처리 일시
    
    # 변경 관련 추가 정보
    proration_amount = Column(Integer, nullable=True, comment="일할계산금액")  # 일할 계산 금액 (원 단위)
    refund_amount = Column(Integer, nullable=True, comment="환불금액")  # 환불 금액 (원 단위)
    additional_charge = Column(Integer, nullable=True, comment="추가청구금액")  # 추가 청구 금액 (원 단위)
    
    # 처리자 정보
    processed_by = Column(String(50), nullable=True, comment="처리자")  # 처리자 (system, admin, user)
    admin_notes = Column(Text, nullable=True, comment="관리자메모")  # 관리자 메모
    
    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")  # 레코드 생성 시간
    
    # 제약조건 및 인덱스
    __table_args__ = (
        Index('idx_subscription_change_user_uuid', 'user_uuid'),  # 사용자별 조회 최적화
        Index('idx_subscription_change_subscription_id', 'subscription_id'),  # 구독별 조회 최적화
        Index('idx_subscription_change_type', 'change_type'),  # 변경유형별 조회 최적화
        Index('idx_subscription_change_effective_date', 'effective_date'),  # 적용일자별 조회 최적화
        Index('idx_subscription_change_processed_at', 'change_processed_at'),  # 처리일시별 조회 최적화
        {'comment': '구독 변경 이력을 시간순으로 추적하는 테이블'}
    )
