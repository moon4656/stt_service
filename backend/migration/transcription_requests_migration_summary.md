# transcription_requests 테이블 마이그레이션 히스토리

## 개요
`transcription_requests` 테이블은 음성 변환 요청을 저장하는 핵심 테이블로, 여러 차례의 마이그레이션을 통해 현재의 구조로 발전했습니다.

## 마이그레이션 히스토리

### 1. ID 컬럼 타입 변경 (7a813374f718)
**제목**: Change transcription_requests id to string format  
**날짜**: 2025-08-15 10:46:19  
**목적**: 기존 정수형 ID를 문자열 형태의 새로운 ID 포맷으로 변경

**변경사항**:
- 기존 `id` 컬럼(Integer)을 새로운 문자열 기반 ID 시스템으로 변경
- `transcription_responses` 테이블의 참조 관계도 함께 업데이트
- 데이터 무결성을 보장하면서 안전한 마이그레이션 수행

### 2. ID 컬럼명 변경 (db3cb9363c0b)
**제목**: Rename id column to request_id in transcription_requests  
**날짜**: 2025-08-15 10:55:13  
**목적**: 컬럼명을 더 명확하게 `request_id`로 변경

**변경사항**:
- `id` 컬럼명을 `request_id`로 변경
- 기존 데이터 보존하면서 컬럼명만 변경
- 인덱스 및 제약조건 유지

### 3. Duration 컬럼 추가 (ec81596dd3fb)
**제목**: Add duration column to transcription_requests  
**날짜**: 2025-08-15 11:39:47  
**목적**: 음성파일의 재생 시간 정보 저장

**변경사항**:
- `duration` 컬럼 추가 (Float 타입, nullable)
- 음성파일의 재생 시간을 초 단위로 저장
- 기존 레코드는 NULL 값으로 유지

## 현재 테이블 구조

```sql
CREATE TABLE transcription_requests (
    request_id VARCHAR(50) PRIMARY KEY,  -- YYYYMMDD-HHMMSS-UUID 포맷
    user_uuid VARCHAR(36),               -- 사용자 식별자
    filename VARCHAR(255) NOT NULL,      -- 업로드된 파일명
    file_size INTEGER NOT NULL,          -- 파일 크기 (bytes)
    file_extension VARCHAR(10) NOT NULL, -- 파일 확장자
    duration FLOAT,                      -- 음성파일 재생 시간 (초)
    status VARCHAR(50) DEFAULT 'processing', -- 처리 상태
    response_rid VARCHAR(100),           -- STT API Response ID
    processing_time FLOAT,               -- 처리 시간 (초)
    error_message TEXT,                  -- 오류 메시지
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
```

## 주요 특징

### 1. 새로운 ID 포맷
- **포맷**: `YYYYMMDD-HHMMSS-UUID_HEX_8_CHARS`
- **예시**: `20250815-024336-6d2680d9`
- **장점**: 시간 기반 정렬 가능, 고유성 보장, 가독성 향상

### 2. Duration 기능
- **지원 포맷**: WAV, MP3, MP4, M4A, AAC, OGG, FLAC
- **계산 방식**: `mutagen` 라이브러리를 통한 메타데이터 추출
- **저장 단위**: 초 (Float 타입)
- **활용**: 처리 시간 예측, 과금 계산, UI 표시 등

### 3. 데이터 무결성
- 모든 마이그레이션에서 기존 데이터 보존
- 외래키 관계 유지
- 인덱스 및 제약조건 보존

## 관련 파일

- **모델 정의**: `database.py`
- **서비스 로직**: `db_service.py`
- **API 엔드포인트**: `app.py`
- **Duration 계산**: `audio_utils.py`
- **마이그레이션**: `alembic/versions/`

## 향후 고려사항

1. **성능 최적화**: duration 컬럼에 인덱스 추가 검토
2. **데이터 분석**: duration 기반 통계 및 분석 기능
3. **UI 개선**: 재생 시간 표시 및 진행률 표시
4. **과금 시스템**: duration 기반 과금 로직 구현

---

*이 문서는 transcription_requests 테이블의 마이그레이션 히스토리와 현재 상태를 요약한 것입니다.*