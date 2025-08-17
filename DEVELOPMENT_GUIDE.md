# STT 프로젝트 개발 가이드

## 🎯 개발자를 위한 실무 가이드

### 📋 새로운 기능 개발 체크리스트

#### 1. 개발 시작 전
- [ ] 요구사항 명확히 정의
- [ ] 데이터베이스 스키마 변경 필요성 검토
- [ ] API 설계 문서 작성
- [ ] 보안 영향도 분석
- [ ] 성능 영향도 검토

#### 2. 개발 중
- [ ] 브랜치 생성 (`feature/기능명`)
- [ ] 환경 변수 추가 시 `.env.example` 업데이트
- [ ] 데이터베이스 변경 시 마이그레이션 스크립트 작성
- [ ] 새로운 API 엔드포인트에 인증/권한 검증 추가
- [ ] 로깅 및 에러 처리 구현
- [ ] 입력 데이터 검증 로직 추가

#### 3. 개발 완료 후
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 실행
- [ ] API 문서 업데이트
- [ ] 코드 리뷰 요청
- [ ] 성능 테스트 수행
- [ ] 보안 검토 완료

---

## 🔧 개발 환경 설정 가이드

### 1. 초기 환경 구성
```bash
# 1. 프로젝트 클론
git clone <repository-url>
cd stt_project

# 2. 가상환경 생성 및 활성화
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 3. 의존성 설치
cd backend
pip install -r requirements.txt

# 4. 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 실제 API 키 입력

# 5. 데이터베이스 설정
# PostgreSQL 설치 및 데이터베이스 생성
# DATABASE_URL 환경 변수 설정

# 6. 데이터베이스 마이그레이션
python -c "from database import create_tables; create_tables()"

# 7. 서버 실행
python app.py
```

### 2. 필수 환경 변수
```bash
# STT 서비스 API 키
ASSEMBLYAI_API_KEY=your_assemblyai_api_key
DAGLO_API_KEY=your_daglo_api_key
DAGLO_API_URL=https://api.daglo.ai/v1/transcribe

# OpenAI API 키 (요약 기능)
OPENAI_API_KEY=your_openai_api_key

# 데이터베이스 연결
DATABASE_URL=postgresql://username:password@localhost:5432/stt_db

# JWT 보안 키
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
```

---

## 🗄️ 데이터베이스 개발 가이드

### 1. 새 테이블 추가 시
```python
# 1. database.py에 모델 클래스 추가
class NewTable(Base):
    """테이블 설명 - 용도와 역할을 명확히 기술"""
    __tablename__ = "new_table"
    
    id = Column(Integer, primary_key=True, index=True)  # 고유 식별자
    # 다른 컬럼들...
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 2. 마이그레이션 스크립트 작성 (migration/ 디렉토리)
# 3. 테이블 주석 추가 (table_comments.sql)
# 4. 관련 서비스 클래스 업데이트 (db_service.py)
```

### 2. 컬럼 추가/수정 시
```python
# 1. 모델 클래스 수정
# 2. Alembic 마이그레이션 생성
alembic revision --autogenerate -m "Add new column"

# 3. 마이그레이션 실행
alembic upgrade head

# 4. 테이블 주석 업데이트
```

---

## 🔌 API 개발 가이드

### 1. 새 엔드포인트 추가 템플릿
```python
@app.post("/new-endpoint/", summary="엔드포인트 요약")
async def new_endpoint(
    request: Request,
    data: RequestModel,  # Pydantic 모델
    current_user: str = Depends(verify_token),  # 인증 필요시
    db: Session = Depends(get_db)
):
    """
    상세한 엔드포인트 설명
    
    - **data**: 요청 데이터 설명
    - **return**: 응답 데이터 설명
    """
    start_time = time.time()
    
    try:
        # 1. 입력 데이터 검증
        if not data.required_field:
            raise HTTPException(status_code=400, detail="필수 필드가 누락되었습니다")
        
        # 2. 비즈니스 로직 처리
        result = process_business_logic(data)
        
        # 3. 데이터베이스 저장
        db_record = save_to_database(db, result)
        
        # 4. API 사용 로그 기록
        processing_time = time.time() - start_time
        APIUsageService.log_api_usage(
            db=db,
            user_uuid=current_user,
            endpoint="/new-endpoint/",
            method="POST",
            status_code=200,
            processing_time=processing_time,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", "")
        )
        
        # 5. 성공 응답
        return {
            "success": True,
            "data": result,
            "processing_time": processing_time
        }
        
    except Exception as e:
        # 에러 로깅
        logger.error(f"❌ 엔드포인트 처리 실패: {e}")
        
        # API 사용 로그 기록 (실패)
        processing_time = time.time() - start_time
        APIUsageService.log_api_usage(
            db=db,
            user_uuid=getattr(current_user, 'user_uuid', None),
            endpoint="/new-endpoint/",
            method="POST",
            status_code=500,
            processing_time=processing_time,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", "")
        )
        
        raise HTTPException(status_code=500, detail=f"처리 중 오류가 발생했습니다: {str(e)}")
```

### 2. Pydantic 모델 정의
```python
class RequestModel(BaseModel):
    """요청 데이터 모델"""
    required_field: str
    optional_field: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "required_field": "예시 값",
                "optional_field": "선택적 값"
            }
        }

class ResponseModel(BaseModel):
    """응답 데이터 모델"""
    success: bool
    data: Dict[str, Any]
    processing_time: float
```

---

## 🔒 보안 개발 가이드

### 1. 인증이 필요한 엔드포인트
```python
# JWT 토큰 인증
@app.post("/protected-endpoint/")
def protected_endpoint(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # current_user는 사용자 UUID
    pass

# API 키 인증
@app.post("/api-protected-endpoint/")
def api_protected_endpoint(
    current_user: str = Depends(verify_api_key_dependency),
    db: Session = Depends(get_db)
):
    # current_user는 사용자 UUID
    pass
```

### 2. 입력 데이터 검증
```python
# 파일 업로드 검증
def validate_audio_file(file: UploadFile):
    # 파일 확장자 검증
    allowed_extensions = ['mp3', 'wav', 'flac', 'm4a', 'ogg']
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다")
    
    # 파일 크기 검증 (예: 100MB 제한)
    max_size = 100 * 1024 * 1024  # 100MB
    if file.size > max_size:
        raise HTTPException(status_code=400, detail="파일 크기가 너무 큽니다")

# 문자열 입력 검증
def validate_string_input(text: str, max_length: int = 1000):
    if len(text) > max_length:
        raise HTTPException(status_code=400, detail=f"텍스트 길이는 {max_length}자를 초과할 수 없습니다")
    
    # XSS 방지를 위한 HTML 태그 제거
    import re
    clean_text = re.sub(r'<[^>]+>', '', text)
    return clean_text
```

---

## 📊 로깅 및 모니터링 가이드

### 1. 로깅 패턴
```python
# 함수 시작 시
logger.info(f"🚀 {function_name} 시작 - 파라미터: {params}")

# 중요한 처리 단계
logger.info(f"📡 STT 변환 시작 - 서비스: {service_name}")

# 성공 완료
logger.info(f"✅ {function_name} 완료 - 결과: {result_summary}")

# 경고 상황
logger.warning(f"⚠️ {warning_message}")

# 에러 발생
logger.error(f"❌ {error_message}")
logger.error(f"Traceback: {traceback.format_exc()}")
```

### 2. 성능 측정
```python
def measure_performance(func_name: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                processing_time = time.time() - start_time
                logger.info(f"⏱️ {func_name} 처리 시간: {processing_time:.2f}초")
                return result
            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"❌ {func_name} 실패 (처리 시간: {processing_time:.2f}초): {e}")
                raise
        return wrapper
    return decorator

# 사용 예시
@measure_performance("STT 변환")
def transcribe_audio(audio_data):
    # STT 처리 로직
    pass
```

---

## 🧪 테스트 개발 가이드

### 1. 단위 테스트 예시
```python
# test/test_auth.py
import pytest
from auth import hash_password, verify_password, TokenManager

def test_password_hashing():
    """패스워드 해시화 테스트"""
    password = "test_password"
    hashed = hash_password(password)
    
    assert hashed != password  # 원본과 다름
    assert verify_password(password, hashed)  # 검증 성공
    assert not verify_password("wrong_password", hashed)  # 잘못된 패스워드

def test_token_generation():
    """토큰 생성 테스트"""
    user_uuid = "test-user-uuid"
    token_id = "test-token"
    
    token_info = TokenManager.generate_api_key(user_uuid, token_id)
    
    assert token_info["user_uuid"] == user_uuid
    assert token_info["token_id"] == token_id
    assert "api_key" in token_info
```

### 2. API 테스트 예시
```python
# test/test_api.py
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_transcribe_endpoint():
    """음성 변환 엔드포인트 테스트"""
    # 테스트 파일 준비
    with open("test_audio.wav", "rb") as f:
        response = client.post(
            "/transcribe/",
            files={"file": ("test_audio.wav", f, "audio/wav")},
            data={"service": "assemblyai", "fallback": True}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "transcription" in data
    assert "request_id" in data

def test_user_creation():
    """사용자 생성 테스트"""
    user_data = {
        "user_id": "test_user",
        "email": "test@example.com",
        "name": "테스트 사용자",
        "user_type": "개인",
        "password": "test_password"
    }
    
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["user_id"] == user_data["user_id"]
    assert "user_uuid" in data
```

---

## 🚀 배포 가이드

### 1. 프로덕션 환경 설정
```bash
# 1. 환경 변수 설정
export DATABASE_URL="postgresql://user:pass@prod-db:5432/stt_db"
export JWT_SECRET_KEY="production-secret-key"
export ASSEMBLYAI_API_KEY="prod-assemblyai-key"
export DAGLO_API_KEY="prod-daglo-key"
export OPENAI_API_KEY="prod-openai-key"

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 데이터베이스 마이그레이션
alembic upgrade head

# 4. 프로덕션 서버 실행
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

### 2. Docker 배포
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["gunicorn", "app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8001"]
```

---

## 🔍 디버깅 가이드

### 1. 일반적인 문제 해결

#### 데이터베이스 연결 오류
```python
# 연결 테스트
from database import test_connection
if not test_connection():
    print("데이터베이스 연결 실패 - DATABASE_URL 확인 필요")
```

#### STT 서비스 오류
```python
# 서비스 설정 확인
from stt_manager import STTManager
stt_manager = STTManager()
print(f"사용 가능한 서비스: {list(stt_manager.services.keys())}")
print(f"기본 서비스: {stt_manager.default_service}")
```

#### API 키 인증 오류
```python
# 토큰 검증
from auth import TokenManager
api_key = "your-api-key"
result = TokenManager.verify_api_key(api_key)
print(f"토큰 검증 결과: {result}")
```

### 2. 로그 분석
```bash
# 최근 에러 로그 확인
tail -f logs/app.log | grep ERROR

# 특정 요청 ID 추적
grep "request-id-here" logs/app.log

# API 응답 시간 분석
grep "처리 시간" logs/app.log | tail -20
```

---

## 📈 성능 최적화 가이드

### 1. 데이터베이스 최적화
```sql
-- 자주 사용되는 쿼리에 인덱스 추가
CREATE INDEX idx_transcription_requests_status_created 
ON transcription_requests(status, created_at);

-- 오래된 로그 데이터 정리
DELETE FROM api_usage_logs 
WHERE created_at < NOW() - INTERVAL '90 days';
```

### 2. API 응답 시간 개선
```python
# 비동기 처리 활용
import asyncio

async def process_multiple_requests(requests):
    tasks = [process_single_request(req) for req in requests]
    results = await asyncio.gather(*tasks)
    return results

# 캐싱 활용
from functools import lru_cache

@lru_cache(maxsize=100)
def get_user_info(user_uuid: str):
    # 사용자 정보 조회 (캐시됨)
    pass
```

---

**이 가이드는 STT 프로젝트의 실제 개발 과정에서 참고할 수 있는 실무 중심의 내용을 담고 있습니다.**

**마지막 업데이트**: 2024년 12월
**작성자**: STT 프로젝트 개발팀