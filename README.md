# Speech-to-Text 서비스

이 프로젝트는 [Daglo API](https://developers.daglo.ai/guide/)를 활용하여 음성 파일을 텍스트로 변환하는 서비스입니다. 또한 가상의 회의록을 생성하고 이를 음성 파일로 변환하는 기능도 포함하고 있습니다.

## 기능

- 다양한 오디오 파일 형식(mp3, wav, m4a, ogg, flac) 지원
- 간단한 REST API 인터페이스
- FastAPI를 통한 자동 API 문서화
- 가상의 3자 대면 회의록 텍스트 생성
- 텍스트를 음성 파일로 변환(TTS)

## 설치 방법

1. 저장소 클론 또는 다운로드

2. 가상환경 설정 (권장)

   **Windows**:
   ```bash
   setup_venv.bat
   ```
   
   **macOS/Linux**:
   ```bash
   chmod +x setup_venv.sh
   ./setup_venv.sh
   ```
   
   또는 수동으로 가상환경 설정:
   ```bash
   # 가상환경 생성
   python -m venv venv
   
   # 가상환경 활성화 (Windows)
   # venv\Scripts\activate
   python -m venv venv
   /venv/Scripts/Activate.ps1
   
   # 가상환경 활성화 (macOS/Linux)
   # source venv/bin/activate
   
   # 패키지 설치
   python.exe -m pip install --upgrade pip
   cd backend/config
   pip install -r requirements.txt
   ```

3. 환경 변수 설정
   - `.env` 파일을 열고 다음 API 키 값을 실제 API 키로 변경합니다:
     - `DAGLO_API_KEY`: Daglo API 서비스 사용을 위한 API 키
     - `ASSEMBLYAI_API_KEY`: AssemblyAI 서비스 사용을 위한 API 키
     - `DEEPGRAM_API_KEY`: Deepgram 서비스 사용을 위한 API 키
     - `TIRO_API_KEY`: Tiro 서비스 사용을 위한 API 키

## 실행 방법

### 전체 데모 실행 (권장)

```bash
python run_demo.py
```

이 명령어는 전체 워크플로우를 자동으로 실행합니다:
1. 가상 회의록 생성
2. 텍스트를 음성으로 변환 (기본적으로 모의 TTS 사용 - 실제 음성 파일이 아닌 텍스트 파일 생성)
3. 생성된 파일을 텍스트 에디터로 확인 가능 (선택 사항)
4. STT 서비스 실행 및 브라우저에서 Swagger UI 열기

**참고**: 기본 설정에서는 실제 음성 파일이 생성되지 않으므로, STT 서비스 테스트를 위해서는 실제 음성 파일을 별도로 준비해야 합니다.

### 개별 스크립트 실행

#### STT 서비스 실행

```bash
python app.py
```

서버가 시작되면 `http://localhost:8000`에서 서비스에 접근할 수 있습니다.

#### 가상 회의록 생성

```bash
python generate_meeting_audio.py
```

이 명령어는 가상의 3자 대면 회의록을 생성하고 `meeting_scripts` 디렉토리에 저장합니다.

#### 텍스트를 음성으로 변환

```bash
python text_to_speech.py meeting_scripts/meeting_20250812_112132.txt --use-real-api --voice ko_KR_Jimin
```

생성된 회의록 텍스트를 음성 파일로 변환합니다. 

**중요 참고사항**: 
- 기본적으로 모의 TTS를 사용하며, 이는 실제 음성 파일이 아닌 텍스트 파일(.mp3 확장자를 가진)을 생성합니다.
- 이 텍스트 파일은 일반 미디어 플레이어로 재생되지 않으며, 텍스트 에디터로 열어서 내용을 확인할 수 있습니다.
- 실제 TTS API를 사용하려면 `.env` 파일에 TTS_API_KEY를 설정하고 `--use-real-api` 옵션을 추가하세요.

## API 사용법

### 음성 파일 변환

**엔드포인트**: `POST /transcribe/`

**요청**: 음성 파일을 `multipart/form-data` 형식으로 전송

**예시 (curl)**:
```bash
# 기본 서비스 사용
curl -X POST "http://localhost:8000/transcribe/" -F "file=@/path/to/audio/file.mp3"

# 특정 서비스 지정 (Tiro 서비스 사용)
curl -X POST "http://localhost:8000/transcribe/?service=tiro" -F "file=@/path/to/audio/file.mp3"
```

**예시 (Python)**:
```python
import requests

# 기본 서비스 사용
url = "http://localhost:8000/transcribe/"
files = {"file": open("audio_file.mp3", "rb")}

response = requests.post(url, files=files)
print(response.json())

# 특정 서비스 지정 (Tiro 서비스 사용)
url = "http://localhost:8000/transcribe/?service=tiro"
files = {"file": open("audio_file.mp3", "rb")}

response = requests.post(url, files=files)
print(response.json())
```

## API 문서

서비스가 실행 중일 때 다음 URL에서 자동 생성된 API 문서를 확인할 수 있습니다:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 추가 스크립트 설명

### generate_meeting_audio.py

가상의 3자 대면 회의록을 생성하는 스크립트입니다. 다음과 같은 기능을 제공합니다:

- 랜덤한 회의 주제 선택
- 3명의 참가자 간 대화 생성
- 회의록을 텍스트 및 JSON 형식으로 저장

### text_to_speech.py

텍스트를 음성으로 변환하는 스크립트입니다. 다음과 같은 기능을 제공합니다:

- 회의록 텍스트 파일을 음성으로 변환
- 실제 TTS API 연동 지원 (API 키 필요)
- 모의 TTS 기능 (실제 API 없이 테스트 가능)
  - **중요**: 모의 TTS는 실제 음성 파일이 아닌 텍스트 파일(.mp3 확장자)을 생성합니다
  - 이 파일은 텍스트 에디터로 열어서 내용을 확인할 수 있습니다

## 전체 워크플로우

1. `generate_meeting_audio.py`로 가상 회의록 생성
2. `text_to_speech.py`로 회의록을 음성 파일로 변환
   - 기본 모의 TTS 모드: 텍스트 파일(.mp3 확장자)을 생성 (실제 음성 파일 아님)
   - 실제 TTS API 사용 시: 실제 음성 파일 생성 (API 키 필요)
3. `app.py`로 STT 서비스 실행
4. STT 서비스 테스트를 위해 실제 음성 파일 업로드 필요
   - 모의 TTS로 생성된 파일은 실제 음성 파일이 아니므로 STT 테스트에 사용할 수 없음
   - 테스트를 위해 실제 음성 파일을 별도로 준비해야 함

## 라이센스
MIT License


## Project Tree
```
stt_project/
├── backend/
│   ├── app.py
│   ├── generate_meeting_audio.py
│   ├── requirements.txt
│   ├── test_api_file_storage.py
│   ├── test_file_storage.py
│   ├── text_to_speech.py
│   └── utils.py
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── meeting_scripts/
├── stt_results/
└── README.md
```
stt_storage/
├── {user_uuid}/              # 사용자별 디렉토리
│   └── 2025-08-15/           # 날짜별 디렉토리 (YYYY-MM-DD)
│       └── {request_id}/     # 요청 ID별 디렉토리
│           └── 음성파일.wav   # 업로드된 음성파일
└── anonymous/                # 익명 사용자용
    └── 2025-08-15/
        └── 20250815-091119-643c4e89/
            └── test_upload.wav

## GITHUB   

- git init
- git status
- git remote -v
- git config --list

# git 사용자정보 설정
# 전역 설정 (모든 저장소에 적용)
- git config --global user.name "사용자명"
- git config --global user.email "이메일@example.com"

# 로컬 설정 (현재 저장소에만 적용)
- git config user.name "사용자명"
- git config user.email "이메일@example.com"

# 프로젝트 루트 디렉토리에서
- git init
- git add .
- git commit -m "Initial commit: STT project with FastAPI, Vue3, PostgreSQL"
- git branch -M main
- git remote add origin https://github.com/moon4656/stt_service.git
- git push -u origin main

# 향후 변경사항 푸시:
- git add .
- git commit -m "커밋 메시지"
- git push

# 브랜치 확인:
- git branch
- git branch -a

# 브랜치 생성:
- git branch <브랜치명>

# 브랜치 변경:
- git checkout <브랜치명>

# 브랜치 병합:
- git checkout <병합할 브랜치>
- git merge <병합할 브랜치>
- git branch -d <병합된 브랜치>

# 원격 브랜치 삭제:
- git branch -r -d origin/<브랜치명>
- git push origin --delete <브랜치명>

# 서버 8001 포트 확인
- netstat -an | findstr :8001

# 서버 8001 포트 종료
- taskkill /f /pid <PID>

# uvicorn 서버 실행
- uvicorn app:app --host 0.0.0.0 --port 8001 --reload

# 1단계: Git 상태 확인
- git status

# 2단계: 변경 사항 확인
- git diff

# 3단계: 변경 사항 스테이징
- git add .

# 4단계: 커밋
- git commit -m "Add new feature"

# 5단계: 원격 저장소에 푸시
- git push origin main

# Personal Access Token 사용 
- git remote set-url origin https://[moonsoo-dx]:[TOKEN]@github.com/moonsoo-dx/stt_service.git



MIT
