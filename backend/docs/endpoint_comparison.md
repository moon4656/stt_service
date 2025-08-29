# STT 엔드포인트 응답 구조 비교

## 개요
이 문서는 `/transcribe/`와 `/transcribe/protected/` 엔드포인트의 응답 구조 차이점을 분석합니다.

## 엔드포인트 비교

### 1. 일반 엔드포인트: `/transcribe/`

**응답 구조:**
```json
{
    "user_id": null,
    "email": null,
    "request_id": "요청 ID",
    "status": "completed",
    "stt_message": "변환된 텍스트",
    "stt_summary": "요약 텍스트",
    "service_name": "사용된 서비스명",
    "processing_time": "처리 시간",
    "original_response": "원본 응답 데이터",
    "assemblyai_summary": "AssemblyAI 요약 (조건부)"
}
```

**특징:**
- 인증이 필요하지 않음
- `user_id`와 `email`은 항상 `null`
- AssemblyAI 요약이 있는 경우에만 `assemblyai_summary` 필드 추가
- 기본적인 변환 정보만 제공

### 2. 보호된 엔드포인트: `/transcribe/protected/`

**응답 구조:**
```json
{
    "status": "success",
    "transcription": "변환된 텍스트",
    "summary": "요약 텍스트",
    "service_used": "사용된 서비스명",
    "duration": "오디오 길이",
    "processing_time": "처리 시간",
    "audio_duration_minutes": "오디오 길이(분)",
    "tokens_used": "사용된 토큰 수",
    "user_uuid": "사용자 UUID",
    "filename": "파일명",
    "request_id": "요청 ID",
    "response_id": "응답 ID"
}
```

**특징:**
- API 키 인증 필요
- 실제 사용자 정보 (`user_uuid`) 포함
- 더 상세한 메타데이터 제공
- 토큰 사용량 추적
- 파일명 정보 포함
- 응답 ID로 추적 가능

## 주요 차이점

### 1. 필드명 차이
| 일반 엔드포인트 | 보호된 엔드포인트 | 설명 |
|---|---|---|
| `stt_message` | `transcription` | 변환된 텍스트 |
| `stt_summary` | `summary` | 요약 텍스트 |
| `service_name` | `service_used` | 사용된 STT 서비스 |
| `status: "completed"` | `status: "success"` | 상태 값 |

### 2. 추가 정보
**보호된 엔드포인트에만 있는 필드:**
- `user_uuid`: 실제 사용자 식별자
- `filename`: 업로드된 파일명
- `response_id`: 응답 추적 ID
- `tokens_used`: 사용된 토큰 수
- `audio_duration_minutes`: 오디오 길이(분 단위)
- `duration`: 오디오 길이

**일반 엔드포인트에만 있는 필드:**
- `user_id`: 항상 null
- `email`: 항상 null
- `original_response`: 원본 STT 서비스 응답
- `assemblyai_summary`: AssemblyAI 요약 (조건부)

### 3. 기능적 차이

#### 일반 엔드포인트
- 인증 불필요
- 기본적인 STT 변환 기능
- 제한된 메타데이터
- 사용자 추적 불가

#### 보호된 엔드포인트
- API 키 인증 필수
- 사용자별 사용량 추적
- 상세한 메타데이터 제공
- 토큰 사용량 모니터링
- 파일 정보 보존

## 결론

두 엔드포인트는 동일한 STT 변환 기능을 제공하지만, **응답 구조가 완전히 다릅니다**:

1. **필드명이 다름**: 같은 정보를 다른 필드명으로 제공
2. **메타데이터 수준이 다름**: 보호된 엔드포인트가 더 상세한 정보 제공
3. **사용자 추적**: 보호된 엔드포인트만 실제 사용자 정보 포함
4. **응답 형식**: 구조적으로 다른 JSON 형태

이러한 차이로 인해 클라이언트 애플리케이션에서는 각 엔드포인트에 맞는 별도의 응답 처리 로직이 필요합니다.