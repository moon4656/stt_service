# main.py
# Requirements: Install dependencies with pip install fastapi uvicorn deepgram-sdk redis aiohttp websockets
# Note: You need a Deepgram API key. Sign up at deepgram.com and replace 'YOUR_DEEPGRAM_API_KEY'.
# Redis: Assumes a local Redis server running on default port 6379. Install Redis if needed.
# Run with: uvicorn main:app --reload

import asyncio
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import JSONResponse
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions, PrerecordedOptions, audio
import redis
import json
import os
from dotenv import load_dotenv
import logging
from deepgram import FileSource
from fastapi import FastAPI, HTTPException
from datetime import datetime, timezone
from psycopg2 import connect
from psycopg2.extras import RealDictCursor

deepgram_play = FastAPI(title="STT Service with Deepgram, Redis, and FastAPI")

load_dotenv()

def db():
    return connect(dbname="stt", user="postgres", password="pw", host="localhost")

# 로깅 설정 추가
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 콘솔 출력
        logging.FileHandler('deepgram_play.log', encoding='utf-8')  # 파일 출력
    ]
)
logger = logging.getLogger(__name__)

# Redis connection (for storing transcriptions)
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Deepgram client
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
deepgram = DeepgramClient(DEEPGRAM_API_KEY)

# Endpoint for file-based STT (upload audio file for transcription)
@deepgram_play.post("/transcribe_file")
async def transcribe_file(file: UploadFile = File(...)):
    try:
        # 파일을 메모리에서 직접 처리 (임시 파일 생성 없음)
        file_content = await file.read()
        
        # FileSource 객체 생성
        payload: FileSource = {
            "buffer": file_content,
        }
        
        # PrerecordedOptions 설정
        options = PrerecordedOptions(
            model="nova-2",
            language="ko",
            smart_format=True,
            punctuate=True
        )
        
        # 올바른 transcribe_file 호출 (await 제거)
        start_time = time.time()  # 시작 시간 기록
        logger.info(f"🚀 Deepgram transcribe_file 시작 - 파일: {file.filename}")
        
        response = deepgram.listen.rest.v("1").transcribe_file(
            source=payload,
            options=options
        )
        
        end_time = time.time()  # 종료 시간 기록
        elapsed_time = end_time - start_time

        logger.info(f"✅ Deepgram transcribe_file 완료 - 소요시간: {elapsed_time:.4f}초")
        
        transcription = response['results']['channels'][0]['alternatives'][0]['transcript']
        
        # Store in Redis
        redis_client.set(file.filename, transcription)
        
        return {"transcription": transcription, "filename": file.filename}
        
    except Exception as e:
        logger.error(f"❌ 전사 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"전사 처리 중 오류가 발생했습니다: {str(e)}"}
        )

# WebSocket endpoint for live/real-time STT
@deepgram_play.websocket("/transcribe_live")
async def transcribe_live(websocket: WebSocket):
    await websocket.accept()
    session_id = str(hash(websocket))  # Simple session ID
    
    async def on_message(message):
        # Handle Deepgram message
        if message and message['type'] == 'Results':
            transcript = message['channel']['alternatives'][0]['transcript']
            if transcript:
                # Append to Redis list for this session
                redis_client.rpush(f"session:{session_id}", transcript)
                await websocket.send_text(json.dumps({"transcript": transcript}))

    options = LiveOptions(
        model="nova-2",
        language="ko",
        smart_format=True,
        interim_results=True,
        utterance_end_ms=1000,
        vad_events=True,
        endpointing=10
    )

    dg_connection = deepgram.listen.live.v("1")
    dg_connection.start(options)

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
    
    try:
        while True:
            data = await websocket.receive_bytes()
            dg_connection.send(data)
    except WebSocketDisconnect:
        dg_connection.finish()
        await websocket.close()
    except Exception as e:
        print(f"Error: {e}")
        dg_connection.finish()
        await websocket.close()

# Endpoint to retrieve stored transcription from Redis
@deepgram_play.get("/get_transcription/{key}")
async def get_transcription(key: str):
    value = redis_client.get(key)
    if value:
        return JSONResponse({"transcription": value})
    else:
        # If it's a live session, get the list
        session_key = f"session:{key}"
        if redis_client.exists(session_key):
            transcripts = redis_client.lrange(session_key, 0, -1)
            full_transcript = " ".join(transcripts)
            return JSONResponse({"transcription": full_transcript})
        return JSONResponse({"error": "Not found"}, status_code=404)

@deepgram_play.post("/tokens/use")
def use_token(token_id: str, used_tokens: int, request_id: str | None = None):
    if used_tokens <= 0:
        raise HTTPException(400, "used_tokens는 양수여야 합니다.")
    now = datetime.now(timezone.utc)

    with db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        # (선택) 멱등: 같은 request_id 재시도 시 재차감 방지
        if request_id:
            cur.execute("SELECT 1 FROM token_usage_logs WHERE request_id=%s", (request_id,))
            if cur.fetchone():
                cur.execute("""
                  SELECT (quota_tokens - used_tokens) AS remaining
                    FROM service_tokens WHERE token_id=%s
                """, (token_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(404, "토큰이 존재하지 않습니다.")
                return {"status": "ok", "remaining_seconds": row["remaining"], "idempotent": True}

        # 1) 원자적 차감
        cur.execute("""
          WITH upd AS (
            UPDATE service_tokens
               SET used_tokens = used_tokens + %s
             WHERE token_id = %s
               AND status = 'active'
               AND expires_at > %s
               AND (quota_tokens - used_tokens) >= %s
          RETURNING (quota_tokens - used_tokens) AS remaining_after
          )
          SELECT remaining_after FROM upd
        """, (used_tokens, token_id, now, used_tokens))
        row = cur.fetchone()
        if not row:
            raise HTTPException(400, "잔여량 부족 또는 만료/정지된 토큰입니다.")

        remaining = row["remaining_after"]

        # 2) (선택) 사용 이력 기록
        cur.execute("""
          INSERT INTO token_usage_logs (token_id, used_tokens, request_id)
          VALUES (%s, %s, %s)
          ON CONFLICT (request_id) DO NOTHING
        """, (token_id, used_tokens, request_id))

        return {"status": "ok", "used_tokens": used_tokens, "remaining_tokens": remaining}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(deepgram_play, host="0.0.0.0", port=8000)
