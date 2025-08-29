from fastapi import FastAPI, File, UploadFile, HTTPException
from faster_whisper import WhisperModel
import os
import logging
import av
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
model = WhisperModel("base", device="cpu", compute_type="int8")

def validate_audio_file(file_path: str) -> bool:
    """
    오디오 파일의 유효성을 검사합니다.
    
    Args:
        file_path: 검사할 파일 경로
    
    Returns:
        파일이 유효한 오디오 파일인지 여부
    """
    try:
        # 파일 존재 여부 확인
        if not os.path.exists(file_path):
            logger.error(f"❌ 파일이 존재하지 않습니다: {file_path}")
            return False
        
        # 파일 크기 확인
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            logger.error(f"❌ 빈 파일입니다: {file_path}")
            return False
        
        if file_size < 1024:  # 1KB 미만
            logger.error(f"❌ 파일이 너무 작습니다: {file_size} bytes")
            return False
        
        # av 라이브러리로 파일 검증
        try:
            with av.open(file_path, mode="r", metadata_errors="ignore") as container:
                if not container.streams.audio:
                    logger.error(f"❌ 오디오 스트림이 없습니다: {file_path}")
                    return False
                
                # 첫 번째 오디오 스트림 확인
                audio_stream = container.streams.audio[0]
                if audio_stream.duration is None or audio_stream.duration <= 0:
                    logger.error(f"❌ 유효하지 않은 오디오 길이: {file_path}")
                    return False
                    
            logger.info(f"✅ 유효한 오디오 파일: {file_path}")
            return True
            
        except av.error.InvalidDataError:
            logger.error(f"❌ 손상된 오디오 파일: {file_path}")
            return False
        except Exception as e:
            logger.error(f"❌ 오디오 파일 검증 실패: {str(e)}")
            return False
        
    except Exception as e:
        logger.error(f"❌ 파일 검증 중 오류 발생: {str(e)}")
        return False

@app.post("/stt/")
async def stt(file: UploadFile = File(...)):
    """
    음성 파일을 텍스트로 변환합니다.
    """
    temp_files = []  # 정리할 임시 파일 목록
    
    try:
        # 파일명 검증
        if not file.filename:
            raise HTTPException(status_code=400, detail="파일명이 없습니다.")
        
        # 지원되는 확장자 확인
        supported_extensions = ['.mp3', '.wav', '.flac', '.m4a', '.ogg']
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in supported_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"지원되지 않는 파일 형식입니다. 지원 형식: {', '.join(supported_extensions)}"
            )
        
        # 디렉토리 생성
        os.makedirs("meeting_audios", exist_ok=True)
        
        # 원본 파일 저장
        original_path = f"meeting_audios/{file.filename}"
        temp_files.append(original_path)
        
        logger.info(f"🚀 파일 업로드 시작: {file.filename}")
        
        with open(original_path, "wb") as buffer:
            content = await file.read()
            if len(content) == 0:
                raise HTTPException(status_code=400, detail="빈 파일입니다.")
            buffer.write(content)
        
        logger.info(f"📁 파일 저장 완료: {original_path} ({len(content)} bytes)")
        
        # 파일 유효성 검사
        if not validate_audio_file(original_path):
            raise HTTPException(status_code=400, detail="유효하지 않은 오디오 파일입니다.")
        
        # Whisper 변환
        logger.info(f"🎵 STT 변환 시작: {original_path}")
        
        try:
            segments, info = model.transcribe(original_path, beam_size=5)
            
            # 결과 처리
            text = "".join([segment.text for segment in segments])
            
            logger.info(f"✅ STT 변환 완료: {len(text)}자, 언어: {info.language}")
            
            return {
                "text": text.strip(),
                "language": info.language,
                "duration": round(info.duration, 2) if info.duration else 0,
                "status": "success"
            }
            
        except av.error.InvalidDataError as av_error:
            logger.error(f"❌ 오디오 데이터 오류: {str(av_error)}")
            raise HTTPException(
                status_code=400, 
                detail="손상된 오디오 파일입니다. 다른 파일을 시도해주세요."
            )
        
        except Exception as whisper_error:
            logger.error(f"❌ Whisper 변환 오류: {str(whisper_error)}")
            raise HTTPException(
                status_code=500, 
                detail=f"STT 변환 중 오류가 발생했습니다: {str(whisper_error)}"
            )
        
    except HTTPException:
        raise  # HTTPException은 그대로 전달
        
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"서버 오류가 발생했습니다: {str(e)}"
        )
        
    finally:
        # 임시 파일 정리
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    logger.info(f"🗑️ 임시 파일 삭제: {temp_file}")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ 임시 파일 삭제 실패: {cleanup_error}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

