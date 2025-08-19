# 토큰 관리 API 가이드

이 문서는 사용자별 토큰 Key 발행, 검증, 내역 조회 API의 사용법을 설명합니다.

## API 엔드포인트 개요

### 1. 사용자 관리
- `POST /users/` - 새로운 사용자 생성
- `POST /auth/login` - 사용자 로그인 (JWT 토큰 발급)

### 2. 토큰 관리
- `POST /tokens/{token_id}` - API 키 발행 (JWT 토큰 필요, token_id는 URL 파라미터)
- `GET /tokens/verify` - API 키 검증
- `GET /tokens/` - 사용자 토큰 목록 조회 (JWT 토큰 필요)
- `POST /tokens/revoke` - API 키 비활성화 (JWT 토큰 필요)
- `GET /tokens/history` - 토큰 사용 내역 조회 (JWT 토큰 필요)

### 3. 보호된 서비스
- `POST /transcribe/protected/` - API 키로 보호된 음성 변환 서비스

## 사용 예제

### 1. 사용자 생성
```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_001",
    "email": "test@example.com",
    "name": "테스트 사용자"
  }'
```

### 2. 로그인 (JWT 토큰 발급)
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_001"
  }'
```

응답 예시:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "user_id": "test_user_001",
    "email": "test@example.com",
    "name": "테스트 사용자",
    "created_at": "2024-01-01T00:00:00",
    "is_active": true
  }
}
```

### 3. API 키 발행
```bash
curl -X POST "http://localhost:8000/tokens/my_token_001?description=테스트용%20API%20키" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

응답 예시:
```json
{
  "status": "success",
  "token": {
    "api_key": "abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx",
    "api_key_hash": "hash_value",
    "token_id": "my_token_001",
    "user_id": "test_user_001",
    "description": "테스트용 API 키",
    "created_at": "2024-01-01T00:00:00",
    "is_active": true
  }
}
```

### 4. API 키 검증
```bash
curl -X GET "http://localhost:8000/tokens/verify" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 5. 사용자 토큰 목록 조회
```bash
curl -X GET "http://localhost:8000/tokens/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 6. 토큰 사용 내역 조회
```bash
curl -X GET "http://localhost:8000/tokens/history?limit=10" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 7. API 키 비활성화
```bash
curl -X POST "http://localhost:8000/tokens/revoke" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "api_key_hash": "hash_value"
  }'
```

### 8. API 키로 보호된 음성 변환 서비스 사용
```bash
curl -X POST "http://localhost:8000/transcribe/protected/" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@audio_file.mp3"
```

#### Fast-Whisper 서비스 사용 예
```bash
curl -X POST "http://localhost:8001/transcribe/" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.mp3" \
  -F "service=fast-whisper" \
  -F "model_size=base" \
  -F "task=transcribe" \
  -F "language=ko"
```

### 보호된 Fast-Whisper 서비스 사용 예
```bash
curl -X POST "http://localhost:8001/transcribe/protected/" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.mp3" \
  -F "service=fast-whisper" \
  -F "model_size=medium" \
  -F "task=translate"
```

## 인증 방식

### JWT 토큰 인증
- 사용자 관리 및 토큰 관리 API에서 사용
- `Authorization: Bearer JWT_TOKEN` 헤더 형식
- 토큰 유효기간: 24시간

### API 키 인증
- 실제 서비스 이용 시 사용
- `Authorization: Bearer API_KEY` 헤더 형식
- 사용할 때마다 사용 횟수가 증가하고 히스토리에 기록됨

## 보안 고려사항

1. **JWT 시크릿 키**: 프로덕션 환경에서는 반드시 강력한 시크릿 키를 설정하세요.
2. **API 키 저장**: API 키는 안전한 곳에 저장하고, 코드에 하드코딩하지 마세요.
3. **HTTPS 사용**: 프로덕션 환경에서는 반드시 HTTPS를 사용하세요.
4. **토큰 만료**: 정기적으로 토큰을 갱신하고 사용하지 않는 토큰은 비활성화하세요.

## 에러 코드

- `400`: 잘못된 요청 (파라미터 오류 등)
- `401`: 인증 실패 (토큰 없음, 만료, 잘못된 토큰)
- `404`: 리소스 없음 (사용자 없음, 토큰 없음)
- `422`: 유효성 검사 실패
- `500`: 서버 내부 오류

## API 문서

서버 실행 후 다음 URL에서 자동 생성된 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 테스트

제공된 테스트 스크립트를 사용하여 API를 테스트할 수 있습니다:
```bash
python test_token_api.py
```