from typing import Dict, Any, Optional
import tempfile
import os
import time
import logging
from backend.services.stt_service_interface import STTServiceInterface

try:
    import faster_whisper
except ImportError:
    faster_whisper = None

logger = logging.getLogger(__name__)

class FastWhisperService(STTServiceInterface):
    """
    Fast-Whisper 기반 STT 서비스 구현체
    로컬에서 실행되는 빠른 음성 인식 서비스
    """
    
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        """
        Fast-Whisper 서비스를 초기화합니다.
        
        Args:
            model_size: 모델 크기 (tiny, base, small, medium, large-v2, large-v3)
            device: 실행 장치 (cpu, cuda)
            compute_type: 연산 타입 (int8, float16, float32)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Whisper 모델을 로드합니다."""
        try:
            if faster_whisper is None:
                logger.error("faster-whisper 패키지가 설치되지 않았습니다.")
                return
            
            logger.info(f"🤖 Fast-Whisper 모델 로딩 중... (크기: {self.model_size})")
            self.model = faster_whisper.WhisperModel(
                self.model_size, 
                device=self.device, 
                compute_type=self.compute_type
            )
            logger.info(f"✅ Fast-Whisper 모델 로딩 완료")
        except Exception as e:
            logger.error(f"❌ Fast-Whisper 모델 로딩 실패: {str(e)}")
            self.model = None
    
    def transcribe_file(
        self, 
        file_content: bytes, 
        filename: str, 
        language_code: str = "ko",
        **kwargs
    ) -> Dict[str, Any]:
        """
        음성 파일을 텍스트로 변환합니다.
        
        Args:
            file_content: 음성 파일의 바이트 데이터
            filename: 파일명
            language_code: 언어 코드 (기본값: "ko")
            **kwargs: 추가 옵션
                - task: "transcribe" 또는 "translate"
                - beam_size: 빔 서치 크기 (기본값: 5)
                - best_of: 최적화 옵션 (기본값: 5)
                - temperature: 온도 설정 (기본값: 0.0)
        
        Returns:
            Dict[str, Any]: 변환 결과
        """
        start_time = time.time()
        temp_file_path = None
        
        try:
            if not self.is_configured():
                return {
                    "text": "",
                    "confidence": 0.0,
                    "audio_duration": 0.0,
                    "language_code": language_code,
                    "service_name": "fast-whisper",
                    "transcript_id": "",
                    "full_response": {},
                    "processing_time": 0.0,
                    "error": "Fast-Whisper 서비스가 설정되지 않았습니다."
                }
            
            # 임시 파일로 저장
            file_extension = filename.split('.')[-1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(file_content)
            
            logger.info(f"📁 임시 파일 저장 완료: {temp_file_path}")
            
            # 언어 코드 변환 (한국어 처리)
            whisper_language = self._convert_language_code(language_code)
            
            # 추가 옵션 설정
            task = kwargs.get("task", "transcribe")
            beam_size = kwargs.get("beam_size", 5)
            best_of = kwargs.get("best_of", 5)
            temperature = kwargs.get("temperature", 0.0)
            
            # 음성 변환 실행
            logger.info(f"🎵 음성 변환 실행 중... (언어: {whisper_language}, 작업: {task})")
            segments, info = self.model.transcribe(
                temp_file_path,
                language=whisper_language,
                task=task,
                beam_size=beam_size,
                best_of=best_of,
                temperature=temperature
            )
            
            # 결과 텍스트 조합
            transcribed_text = ""
            segment_list = []
            
            for segment in segments:
                transcribed_text += segment.text + " "
                segment_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                })
            
            transcribed_text = transcribed_text.strip()
            processing_time = time.time() - start_time
            
            logger.info(f"✅ Fast-Whisper 변환 완료 - 처리시간: {processing_time:.2f}초")
            logger.info(f"📝 변환된 텍스트 길이: {len(transcribed_text)} 문자")
            logger.info(f"🌍 감지된 언어: {info.language} (확률: {info.language_probability:.2f})")
            
            return {
                "text": transcribed_text,
                "confidence": float(info.language_probability),
                "audio_duration": float(getattr(info, 'duration', 0.0)),
                "language_code": info.language,
                "service_name": "fast-whisper",
                "transcript_id": f"fw_{int(time.time())}_{hash(transcribed_text) % 10000}",
                "full_response": {
                    "segments": segment_list,
                    "language": info.language,
                    "language_probability": info.language_probability,
                    "duration": getattr(info, 'duration', 0.0),
                    "model_size": self.model_size,
                    "task": task
                },
                "processing_time": processing_time,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"Fast-Whisper 변환 중 오류 발생: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            return {
                "text": "",
                "confidence": 0.0,
                "audio_duration": 0.0,
                "language_code": language_code,
                "service_name": "fast-whisper",
                "transcript_id": "",
                "full_response": {},
                "processing_time": time.time() - start_time,
                "error": error_msg
            }
        
        finally:
            # 임시 파일 정리
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.info(f"🗑️ 임시 파일 삭제 완료: {temp_file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ 임시 파일 삭제 실패: {str(cleanup_error)}")
    
    def _convert_language_code(self, language_code: str) -> Optional[str]:
        """언어 코드를 Whisper 형식으로 변환합니다."""
        language_map = {
            "ko": "ko",
            "en": "en",
            "ja": "ja",
            "zh": "zh",
            "es": "es",
            "fr": "fr",
            "de": "de",
            "it": "it",
            "pt": "pt",
            "ru": "ru"
        }
        return language_map.get(language_code.lower())
    
    def is_configured(self) -> bool:
        """
        서비스가 올바르게 설정되었는지 확인합니다.
        
        Returns:
            bool: 설정 완료 여부
        """
        return faster_whisper is not None and self.model is not None
    
    def get_service_name(self) -> str:
        """
        서비스 이름을 반환합니다.
        
        Returns:
            str: 서비스 이름
        """
        return "fast-whisper"
    
    def get_supported_formats(self) -> list:
        """
        지원하는 파일 형식 목록을 반환합니다.
        
        Returns:
            list: 지원하는 파일 확장자 목록
        """
        return ['mp3', 'wav', 'flac', 'm4a', 'aac', 'ogg', 'wma']
    
    def get_max_file_size(self) -> int:
        """
        최대 파일 크기를 반환합니다.
        
        Returns:
            int: 최대 파일 크기 (바이트)
        """
        return 100 * 1024 * 1024  # 100MB