# STT 프로젝트 규칙 (Project Rules)

## 🎯 프로젝트 개요
이 문서는 STT(Speech-to-Text) 프로젝트의 개발 규칙과 가이드라인을 정의합니다. 모든 개발자는 이 규칙을 준수하여 일관성 있고 고품질의 코드를 작성해야 합니다.

---

## 🏗️ 프로젝트 아키텍처

### 기술 스택
- **백엔드**: Python 3.8+, FastAPI, SQLAlchemy, PostgreSQL
- **STT 서비스**: AssemblyAI, Daglo (다중 서비스 지원)
- **인증**: JWT 토큰, API 키 기반 인증
- **데이터베이스**: PostgreSQL with Alembic 마이그레이션
- **로깅**: Python logging 모듈
- **테스트**: pytest 프레임워크

### 프로젝트 구조
```
stt_project/
├── backend/                 # FastAPI 백엔드 서버
│   ├── app.py              # 메인 애플리케이션
│   ├── database.py         # 데이터베이스 모델
│   ├── auth.py             # 인증 및 권한 관리
│   ├── stt_manager.py      # STT 서비스 관리자
│   ├── *_service.py        # STT 서비스 구현체
│   ├── alembic/            # 데이터베이스 마이그레이션
│   ├── stt_storge/         # 전송받은 음성 파일
│   ├── test/               # 테스트 코드
│   └── check/              # 데이터베이스 검증 스크립트
├── frontend/               # 프론트엔드 (향후 확장)
└── .trae/rules/           # Trae AI IDE 프로젝트 규칙
```

---

## 📝 코딩 규칙

### Python 코딩 스타일
- **PEP 8** 스타일 가이드 엄격히 준수
- **타입 힌트** 모든 함수와 메서드에 필수 적용
- **한국어 docstring** 모든 클래스와 함수에 작성
- **영어 변수명** 의미가 명확한 영어로 작성
- **상수 사용** 매직 넘버 대신 명명된 상수 사용

### 함수 및 클래스 설계
```python
# 올바른 예시
def transcribe_audio_file(file_path: str, service_name: str) -> Dict[str, Any]:
    """
    음성 파일을 텍스트로 변환합니다.
    
    Args:
        file_path: 변환할 음성 파일 경로
        service_name: 사용할 STT 서비스명 (assemblyai, daglo)
    
    Returns:
        변환 결과를 포함한 딕셔너리
    
    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        STTServiceError: STT 서비스 오류 발생 시
    """
    pass
```

### FastAPI 개발 규칙
- 모든 엔드포인트에 `summary`와 상세 설명 추가
- Pydantic 모델로 요청/응답 검증
- 적절한 HTTP 상태 코드 사용
- 의존성 주입 패턴 활용
- 비동기 처리 시 `async/await` 사용

---

## 🗄️ 데이터베이스 규칙

### 스키마 설계 원칙
- 모든 테이블과 컬럼에 **한국어 주석** 필수
- 적절한 데이터 타입 선택 (UUID, TIMESTAMP WITH TIME ZONE 등)
- 외래 키 관계 명확히 정의
- 성능을 위한 인덱스 설정
- 필수 필드는 `nullable=False` 설정

### 주요 테이블 구조
```python
# 사용자 테이블
class User(Base):
    # 사용자 정보를 저장하는 테이블
    id = Column(Integer, primary_key=True, comment="사용자 고유 ID")
    user_uuid = Column(String, unique=True, comment="사용자 UUID")
    email = Column(String, unique=True, comment="이메일 주소")
    # ... 기타 필드

# STT 요청 테이블
class TranscriptionRequest(Base):
    # STT 변환 요청 정보를 저장하는 테이블
    request_id = Column(String, primary_key=True, comment="요청 고유 ID")
    user_uuid = Column(String, ForeignKey('users.user_uuid'), comment="요청자 UUID")
    # ... 기타 필드
```

### 마이그레이션 규칙
- 모든 스키마 변경은 Alembic 마이그레이션으로 관리
- 롤백 가능한 마이그레이션 작성
- 프로덕션 적용 전 충분한 테스트
- 마이그레이션 스크립트에 상세한 주석 추가

---

## 🔌 API 설계 규칙

### RESTful API 원칙
- HTTP 메서드 적절히 활용 (GET, POST, PUT, DELETE)
- 리소스 중심의 URL 설계
- 일관된 응답 형식 유지
- 에러 응답에 상세한 한국어 메시지 포함

### 엔드포인트 예시
```python
@app.post("/transcribe", summary="음성 파일 텍스트 변환")
async def transcribe_audio(
    file: UploadFile = File(...),
    service: str = Query("auto", description="STT 서비스 선택"),
    current_user: User = Depends(get_current_user)
):
    """
    업로드된 음성 파일을 텍스트로 변환합니다.
    
    - **file**: 변환할 음성 파일 (mp3, wav, flac 등)
    - **service**: 사용할 STT 서비스 (auto, assemblyai, daglo)
    """
    pass
```

### STT 서비스 통합
- 다중 STT 서비스 지원 (AssemblyAI, Daglo)
- 폴백 메커니즘으로 안정성 확보
- 서비스별 응답 형식 표준화
- 처리 시간 및 정확도 모니터링

---

## 🔒 보안 규칙

### 인증 및 권한
- **JWT 토큰** 기반 사용자 인증
- **API 키** 를 통한 서비스 접근 제어
- 패스워드는 **bcrypt** 로 해시화
- 토큰 만료 시간 적절히 설정 (기본 24시간)

### 데이터 보호
- 민감한 정보는 환경 변수로 관리
- SQL 인젝션 방지 (ORM 사용)
- 입력 데이터 검증 및 sanitization
- HTTPS 사용 필수 (프로덕션)

### 접근 로깅
```python
# 모든 API 요청 로깅
class APIUsageLog(Base):
    # API 사용 로그를 기록하는 테이블
    id = Column(Integer, primary_key=True)
    user_uuid = Column(String, comment="사용자 UUID")
    endpoint = Column(String, comment="호출된 엔드포인트")
    ip_address = Column(String, comment="클라이언트 IP 주소")
    created_at = Column(DateTime, comment="요청 시간")
```

---

## 📊 로깅 및 모니터링

### 로깅 시스템
- Python `logging` 모듈 사용
- 구조화된 로그 메시지 작성
- 로그 레벨 적절히 활용 (DEBUG, INFO, WARNING, ERROR)
- 민감한 정보 로깅 금지

### 로깅 패턴
```python
# 함수 시작 시
logger.info(f"🚀 {function_name} 시작 - 파라미터: {params}")

# 중요한 처리 단계
logger.info(f"📡 STT 변환 시작 - 서비스: {service_name}")

# 성공 완료
logger.info(f"✅ {function_name} 완료 - 결과: {result_summary}")

# 에러 발생
logger.error(f"❌ {error_message}")
logger.error(f"Traceback: {traceback.format_exc()}")
```

### 성능 모니터링
- API 요청/응답 시간 측정
- STT 서비스별 처리 시간 비교
- 데이터베이스 쿼리 성능 추적
- 시스템 리소스 사용량 모니터링

---

## 🧪 테스트 규칙

### 테스트 구조
- `test/` 디렉토리에 테스트 코드 구성
- pytest 프레임워크 사용
- 단위 테스트, 통합 테스트, E2E 테스트 구분

### 테스트 커버리지
- 핵심 비즈니스 로직 **80% 이상** 커버리지
- 모든 API 엔드포인트 테스트
- STT 서비스 모킹 테스트
- 에러 시나리오 테스트

### 테스트 예시
```python
def test_transcribe_audio_success():
    """
    음성 파일 변환 성공 테스트
    """
    # Given
    test_file = "test_audio.wav"
    expected_text = "안녕하세요"
    
    # When
    result = transcribe_audio(test_file, "assemblyai")
    
    # Then
    assert result["status"] == "success"
    assert expected_text in result["text"]
```

---

## 🚀 배포 및 운영

### 환경 구성
- 개발(Development), 스테이징(Staging), 프로덕션(Production) 환경 분리
- 환경별 설정 파일 관리 (`.env` 파일)
- 컨테이너화 고려 (Docker)

### CI/CD 파이프라인
- 코드 푸시 시 자동 테스트 실행
- 테스트 통과 후 자동 배포
- 롤백 메커니즘 구현
- 배포 전 보안 검사

### 백업 및 복구
- 데이터베이스 정기 백업
- 백업 데이터 암호화
- 복구 절차 문서화
- 재해 복구 계획 수립

---

## 📚 문서화 규칙

### API 문서
- FastAPI 자동 생성 문서 활용
- 모든 엔드포인트에 상세 설명 추가
- 요청/응답 예시 제공
- 에러 코드 및 메시지 문서화

### 코드 문서
- README.md 파일 최신 상태 유지
- 설치 및 실행 가이드 제공
- 아키텍처 다이어그램 포함
- 변경 이력 관리 (CHANGELOG.md)

---

## 📈 성능 최적화

### 데이터베이스 최적화
- 자주 사용되는 쿼리에 인덱스 추가
- N+1 쿼리 문제 방지
- 페이지네이션 구현
- 오래된 로그 데이터 정리

### API 성능 개선
- 비동기 처리 활용
- 캐싱 전략 적용
- 응답 데이터 크기 최소화
- 압축 사용 (gzip)

---

## 🔍 코드 리뷰 가이드

### 리뷰 체크리스트
- [ ] 요구사항 충족 여부
- [ ] 코딩 스타일 준수
- [ ] 보안 취약점 검토
- [ ] 성능 영향도 분석
- [ ] 테스트 코드 작성 여부
- [ ] 문서 업데이트 여부

### 리뷰 우선순위
- **🔴 필수**: 보안, 기본 기능, 에러 처리
- **🟡 권장**: 성능 최적화, 코드 품질
- **🟢 선택**: 고급 기능, 추가 최적화

---

## 🛠️ 개발 도구 및 설정

### 필수 도구
- **IDE**: Trae AI (권장), VS Code
- **Python**: 3.8 이상
- **데이터베이스**: PostgreSQL 12 이상
- **버전 관리**: Git

### 개발 환경 설정
```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집

# 데이터베이스 마이그레이션
alembic upgrade head

# 서버 실행
python app.py
```

---

## 📋 체크리스트

### 새 기능 개발 시
- [ ] 요구사항 명확히 정의
- [ ] 데이터베이스 스키마 검토
- [ ] API 설계 문서 작성
- [ ] 보안 영향도 분석
- [ ] 테스트 계획 수립
- [ ] 성능 영향도 검토

### 코드 작성 시
- [ ] PEP 8 스타일 준수
- [ ] 타입 힌트 추가
- [ ] 한국어 docstring 작성
- [ ] 에러 처리 구현
- [ ] 로깅 추가
- [ ] 입력 검증 로직

### 배포 전
- [ ] 모든 테스트 통과
- [ ] 코드 리뷰 완료
- [ ] 보안 검토 완료
- [ ] 성능 테스트 수행
- [ ] 문서 업데이트
- [ ] 백업 완료

---

**이 프로젝트 규칙은 STT 프로젝트의 품질과 일관성을 보장하기 위한 필수 가이드라인입니다.**

**마지막 업데이트**: 2024년 12월  
**작성자**: STT 프로젝트 개발팀  
**버전**: 1.0