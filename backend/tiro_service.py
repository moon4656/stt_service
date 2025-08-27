import os
import requests
import time
import json
from typing import Dict, Any, List, Optional
from stt_service_interface import STTServiceInterface
import logging

logger = logging.getLogger(__name__)

class TiroService(STTServiceInterface):
    """
    Tiro API를 사용하여 음성을 텍스트로 변환하는 서비스
    """
    
    def __init__(self):
        self.api_key = os.getenv("TIRO_API_KEY")
        self.base_url = "https://api.tiro-ooo.dev"
        self.supported_formats = ["mp3", "wav", "m4a", "flac", "ogg"]
        self.max_file_size = 100 * 1024 * 1024  # 100MB
    
    def is_configured(self) -> bool:
        """
        Tiro API 키가 설정되었는지 확인합니다.
        
        Returns:
            bool: API 키 설정 여부
        """
        return self.api_key is not None and len(self.api_key) > 0
    
    def get_service_name(self) -> str:
        """
        서비스명을 반환합니다.
        
        Returns:
            str: 서비스명
        """
        return "tiro"
    
    def get_supported_formats(self) -> list:
        """
        지원하는 파일 형식 목록을 반환합니다.
        
        Returns:
            list: 지원 형식 리스트
        """
        return self.supported_formats
    
    def get_max_file_size(self) -> int:
        """
        최대 파일 크기를 반환합니다 (바이트 단위).
        
        Returns:
            int: 최대 파일 크기
        """
        return self.max_file_size
    
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
            **kwargs: 서비스별 추가 옵션
            
        Returns:
            Dict[str, Any]: 변환 결과
        """
        if not self.is_configured():
            return {
                "text": "",
                "confidence": 0.0,
                "audio_duration": 0.0,
                "language_code": language_code,
                "service_name": self.get_service_name(),
                "transcript_id": "",
                "full_response": {},
                "processing_time": 0.0,
                "error": "Tiro API 키가 설정되지 않았습니다."
            }
        
        start_time = time.time()
        
        try:
            # 파일 업로드 및 변환 요청
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 파일 업로드
            files = {
                "file": (filename, file_content)
            }
            
            # 요청 파라미터 설정
            params = {
                "language": language_code
            }
            
            # 추가 옵션 처리
            if "translate_to" in kwargs:
                params["translate_to"] = kwargs["translate_to"]
            
            # API 요청
            logger.info(f"Tiro API 요청 시작: {filename}")
            response = requests.post(
                f"{self.base_url}/voice/process",
                headers=headers,
                files=files,
                params=params
            )
            
            processing_time = time.time() - start_time
            
            # 응답 처리
            if response.status_code == 200:
                result = response.json()
                
                # 결과 형식 변환
                return {
                    "text": result.get("text", ""),
                    "confidence": result.get("confidence", 0.0),
                    "audio_duration": result.get("audio_duration", 0.0),
                    "language_code": result.get("detected_language", language_code),
                    "service_name": self.get_service_name(),
                    "transcript_id": result.get("id", ""),
                    "full_response": result,
                    "processing_time": processing_time,
                    "error": None
                }
            else:
                error_message = f"Tiro API 오류: {response.status_code} - {response.text}"
                logger.error(error_message)
                return {
                    "text": "",
                    "confidence": 0.0,
                    "audio_duration": 0.0,
                    "language_code": language_code,
                    "service_name": self.get_service_name(),
                    "transcript_id": "",
                    "full_response": {},
                    "processing_time": processing_time,
                    "error": error_message
                }
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_message = f"Tiro API 예외 발생: {str(e)}"
            logger.error(error_message)
            return {
                "text": "",
                "confidence": 0.0,
                "audio_duration": 0.0,
                "language_code": language_code,
                "service_name": self.get_service_name(),
                "transcript_id": "",
                "full_response": {},
                "processing_time": processing_time,
                "error": error_message
            }