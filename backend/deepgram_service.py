import os
import requests
import time
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from stt_service_interface import STTServiceInterface
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class DeepgramService(STTServiceInterface):
    """
    Deepgram API를 사용한 음성-텍스트 변환 서비스
    """
    
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        self.base_url = "https://api.deepgram.com/v1/listen"
        
        if not self.api_key:
            logger.warning("DEEPGRAM_API_KEY가 설정되지 않았습니다.")
    
    def is_configured(self) -> bool:
        """서비스가 올바르게 설정되었는지 확인합니다."""
        return bool(self.api_key)
    
    def get_service_name(self) -> str:
        """서비스명을 반환합니다."""
        return "Deepgram"
    
    def get_supported_formats(self) -> list:
        """지원하는 파일 형식 목록을 반환합니다."""
        return ['mp3', 'wav', 'm4a', 'flac', 'ogg', 'aac', 'opus', 'webm', 'mp4', 'mov', 'avi']
    
    def get_max_file_size(self) -> int:
        """최대 파일 크기를 반환합니다 (바이트 단위)."""
        return 2 * 1024 * 1024 * 1024  # 2GB
    
    def transcribe_file(
        self, 
        file_content: bytes, 
        filename: str, 
        language_code: str = "ko",
        model: str = "nova-2",
        smart_format: bool = True,
        punctuate: bool = True,
        diarize: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        음성 파일을 텍스트로 변환합니다.
        
        Args:
            file_content: 음성 파일의 바이트 데이터
            filename: 파일명
            language_code: 언어 코드 (기본값: "ko")
            model: 사용할 모델 (nova-2, nova, base, enhanced)
            smart_format: 스마트 포맷팅 사용 여부
            punctuate: 구두점 추가 여부
            diarize: 화자 분리 여부
            **kwargs: 추가 옵션들
            
        Returns:
            Dict[str, Any]: 변환 결과
        """
        start_time = time.time()
        
        try:
            logger.info(f"🎤 Deepgram 변환 시작 - 파일: {filename}")
            
            # 헤더 설정
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": self._get_content_type(filename)
            }
            
            # 쿼리 파라미터 설정
            params = {
                "model": model,
                "smart_format": str(smart_format).lower(),
                "punctuate": str(punctuate).lower(),
                "diarize": str(diarize).lower()
            }
            
            # 언어 설정 (한국어의 경우)
            if language_code == "ko":
                params["language"] = "ko"
            elif language_code != "auto":
                params["language"] = language_code
            
            # 추가 옵션 적용
            for key, value in kwargs.items():
                if key in ["summarize", "detect_language", "search", "redact", "alternatives"]:
                    params[key] = str(value).lower() if isinstance(value, bool) else value
            
            # API 요청
            response = requests.post(
                self.base_url,
                headers=headers,
                params=params,
                data=file_content,
                timeout=300  # 5분 타임아웃
            )
            
            processing_time = time.time() - start_time
            
            if response.status_code != 200:
                error_msg = f"Deepgram API 오류: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    "text": "",
                    "confidence": 0.0,
                    "audio_duration": 0.0,
                    "language_code": language_code,
                    "service_name": "deepgram",
                    "transcript_id": "",
                    "full_response": {},
                    "processing_time": processing_time,
                    "error": error_msg
                }
            
            # 응답 파싱
            result = response.json()
            
            # 텍스트 추출
            text = ""
            confidence = 0.0
            audio_duration = 0.0
            detected_language = language_code
            
            if "results" in result and "channels" in result["results"]:
                channels = result["results"]["channels"]
                if channels and len(channels) > 0:
                    alternatives = channels[0].get("alternatives", [])
                    if alternatives and len(alternatives) > 0:
                        text = alternatives[0].get("transcript", "")
                        confidence = alternatives[0].get("confidence", 0.0)
                        
                        # 단어별 정보에서 추가 데이터 추출
                        words = alternatives[0].get("words", [])
                        if words:
                            # 마지막 단어의 end 시간을 오디오 길이로 사용
                            audio_duration = words[-1].get("end", 0.0)
            
            # 메타데이터에서 추가 정보 추출
            if "metadata" in result:
                metadata = result["metadata"]
                if "duration" in metadata:
                    audio_duration = metadata["duration"]
                if "detected_language" in metadata:
                    detected_language = metadata["detected_language"]
            
            logger.info(f"✅ Deepgram 변환 완료 - 길이: {len(text)}자, 신뢰도: {confidence:.2f}")
            
            return {
                "text": text,
                "confidence": confidence,
                "audio_duration": audio_duration,
                "language_code": detected_language,
                "service_name": "deepgram",
                "transcript_id": result.get("metadata", {}).get("request_id", ""),
                "full_response": result,
                "processing_time": processing_time,
                "error": None
            }
            
        except requests.exceptions.Timeout:
            error_msg = "Deepgram API 타임아웃 오류"
            logger.error(error_msg)
            return {
                "text": "",
                "confidence": 0.0,
                "audio_duration": 0.0,
                "language_code": language_code,
                "service_name": "deepgram",
                "transcript_id": "",
                "full_response": {},
                "processing_time": time.time() - start_time,
                "error": error_msg
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"Deepgram API 네트워크 오류: {str(e)}"
            logger.error(error_msg)
            return {
                "text": "",
                "confidence": 0.0,
                "audio_duration": 0.0,
                "language_code": language_code,
                "service_name": "deepgram",
                "transcript_id": "",
                "full_response": {},
                "processing_time": time.time() - start_time,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Deepgram 변환 중 예상치 못한 오류: {str(e)}"
            logger.error(error_msg)
            return {
                "text": "",
                "confidence": 0.0,
                "audio_duration": 0.0,
                "language_code": language_code,
                "service_name": "deepgram",
                "transcript_id": "",
                "full_response": {},
                "processing_time": time.time() - start_time,
                "error": error_msg
            }
    
    def _get_content_type(self, filename: str) -> str:
        """
        파일 확장자에 따른 Content-Type을 반환합니다.
        
        Args:
            filename: 파일명
            
        Returns:
            str: Content-Type
        """
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        content_types = {
            'wav': 'audio/wav',
            'mp3': 'audio/mpeg',
            'm4a': 'audio/mp4',
            'flac': 'audio/flac',
            'ogg': 'audio/ogg',
            'aac': 'audio/aac',
            'opus': 'audio/opus',
            'webm': 'audio/webm',
            'mp4': 'video/mp4',
            'mov': 'video/quicktime',
            'avi': 'video/x-msvideo'
        }
        
        return content_types.get(extension, 'audio/wav')