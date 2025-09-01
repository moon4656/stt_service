import os
import requests
import time
import json
from typing import Dict, Any, List, Optional
from .stt_service_interface import STTServiceInterface
import logging

logger = logging.getLogger(__name__)

class TiroService(STTServiceInterface):
    """
    Tiro API를 사용하여 음성을 텍스트로 변환하는 서비스
    """
    
    def __init__(self):
        self.api_key = os.getenv("TIRO_API_KEY")
        self.base_url = "https://api.tiro-ooo.dev/v1/external/voice-file"
        self.supported_formats = ["mp3", "wav", "m4a", "flac", "ogg"]
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }        
    
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
            # 언어 설정
            transcript_locale_hints = None
            translation_locales = None
            
            if language_code == "ko":
                transcript_locale_hints = ["ko_KR"]
            elif language_code == "en":
                transcript_locale_hints = ["en_US"]
            else:
                transcript_locale_hints = ["ko_KR"]  # 기본값
            
            # 번역 옵션 처리
            if "translate_to" in kwargs:
                translation_locales = [kwargs["translate_to"]]
            
            # 완전한 워크플로우 실행
            results = self.process_audio_file_from_bytes(
                file_content=file_content,
                filename=filename,
                transcript_locale_hints=transcript_locale_hints,
                translation_locales=translation_locales
            )
            
            processing_time = time.time() - start_time
            
            if "error" in results:
                return {
                    "text": "",
                    "confidence": 0.0,
                    "audio_duration": 0.0,
                    "language_code": language_code,
                    "service_name": self.get_service_name(),
                    "transcript_id": "",
                    "full_response": {},
                    "processing_time": processing_time,
                    "error": results["error"]
                }
            
            # 결과 추출
            transcript_text = ""
            confidence = 0.9
            job_id = ""
            
            if "transcript" in results:
                transcript_data = results["transcript"]
                transcript_text = transcript_data.get("text", "")
                job_id = transcript_data.get("id", "")
            
            # 번역 결과가 있으면 번역 텍스트 사용
            if "translations" in results and results["translations"]:
                for translation in results["translations"]:
                    if translation.get("text"):
                        transcript_text = translation.get("text", transcript_text)
                        break
            
            return {
                "text": transcript_text,
                "confidence": confidence,
                "audio_duration": 0.0,  # Tiro API에서 제공하지 않음
                "language_code": language_code,
                "service_name": self.get_service_name(),
                "transcript_id": job_id,
                "full_response": results,
                "processing_time": processing_time,
                "error": None
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
    
    def create_job(self, transcript_locale_hints=None, translation_locales=None):
        """
        Tiro API에서 새로운 작업을 생성합니다.
        
        Args:
            transcript_locale_hints: 전사 언어 힌트 리스트
            translation_locales: 번역 언어 리스트
            
        Returns:
            dict: 작업 생성 응답
        """
        payload = {}
        
        if transcript_locale_hints:
            payload["transcriptLocaleHints"] = transcript_locale_hints[:1]
            
        if translation_locales:
            payload["translationLocales"] = translation_locales[:5]
        
        response = requests.post(
            f"{self.base_url}/jobs",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def upload_file_from_bytes(self, upload_uri: str, file_content: bytes, filename: str):
        """
        바이트 데이터를 사용하여 파일을 업로드합니다.
        
        Args:
            upload_uri: 업로드 URI
            file_content: 파일 바이트 데이터
            filename: 파일명
        """
        response = requests.put(upload_uri, data=file_content)
        response.raise_for_status()
        logger.info(f"File uploaded successfully: {filename}")
    
    def notify_upload_complete(self, job_id: str):
        """
        업로드 완료를 알립니다.
        
        Args:
            job_id: 작업 ID
        """
        response = requests.put(
            f"{self.base_url}/jobs/{job_id}/upload-complete",
            headers=self.headers
        )
        response.raise_for_status()
        logger.info(f"Upload complete notification sent for job: {job_id}")
    
    def poll_job_status(self, job_id: str, max_wait_time: int = 600) -> str:
        """
        작업 상태를 폴링합니다.
        
        Args:
            job_id: 작업 ID
            max_wait_time: 최대 대기 시간 (초)
            
        Returns:
            str: 최종 작업 상태
        """
        interval = 1
        max_interval = 10
        elapsed_time = 0
        
        success_statuses = ["TRANSLATION_COMPLETED", "TRANSCRIPT_COMPLETED"]
        failure_statuses = ["FAILED"]
        
        while elapsed_time < max_wait_time:
            response = requests.get(
                f"{self.base_url}/jobs/{job_id}",
                headers=self.headers
            )
            response.raise_for_status()
            
            job_data = response.json()
            status = job_data.get("status")
            
            logger.info(f"Job {job_id} status: {status} (elapsed: {elapsed_time}s)")
            
            if status in success_statuses:
                logger.info(f"Job completed successfully with status: {status}")
                return status
            elif status in failure_statuses:
                logger.error(f"Job failed with status: {status}")
                return status
            
            time.sleep(interval)
            elapsed_time += interval
            
            # 지수 백오프 적용
            interval = min(interval * 2, max_interval)
        
        logger.warning(f"Polling timeout after {max_wait_time} seconds")
        return "TIMEOUT"
    
    def get_transcript(self, job_id: str) -> dict:
        """
        전사 결과를 가져옵니다.
        
        Args:
            job_id: 작업 ID
            
        Returns:
            dict: 전사 결과
        """
        response = requests.get(
            f"{self.base_url}/jobs/{job_id}/transcript",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_translations(self, job_id: str) -> list:
        """
        번역 결과를 가져옵니다.
        
        Args:
            job_id: 작업 ID
            
        Returns:
            list: 번역 결과 리스트
        """
        response = requests.get(
            f"{self.base_url}/jobs/{job_id}/translations",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def process_audio_file_from_bytes(
        self, 
        file_content: bytes, 
        filename: str,
        transcript_locale_hints: Optional[List[str]] = None, 
        translation_locales: Optional[List[str]] = None
    ) -> dict:
        """
        바이트 데이터로부터 완전한 오디오 처리 워크플로우를 실행합니다.
        
        Args:
            file_content: 오디오 파일 바이트 데이터
            filename: 파일명
            transcript_locale_hints: 전사 언어 힌트
            translation_locales: 번역 언어 리스트
            
        Returns:
            dict: 전사 및 번역 결과
        """
        logger.info(f"Starting audio processing for: {filename}")
        
        try:
            # Step 1: 작업 생성
            job_response = self.create_job(transcript_locale_hints, translation_locales)
            job_id = job_response["id"]
            upload_uri = job_response["uploadUri"]
            
            logger.info(f"Job created: {job_id}")
            
            # Step 2: 파일 업로드
            self.upload_file_from_bytes(upload_uri, file_content, filename)
            
            # Step 3: 업로드 완료 알림
            self.notify_upload_complete(job_id)
            
            # Step 4: 완료 대기
            final_status = self.poll_job_status(job_id)
            
            if final_status not in ["TRANSCRIPT_COMPLETED", "TRANSLATION_COMPLETED"]:
                return {"error": f"Job failed with status: {final_status}"}
            
            # Step 5: 결과 수집
            results = {}
            
            try:
                transcript = self.get_transcript(job_id)
                results["transcript"] = transcript
            except requests.exceptions.RequestException as e:
                logger.error(f"Error getting transcript: {e}")
            
            if translation_locales:
                try:
                    translations = self.get_translations(job_id)
                    results["translations"] = translations
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error getting translations: {e}")
            
            return results
            
        except Exception as e:
            error_message = f"Audio processing failed: {str(e)}"
            logger.error(error_message)
            return {"error": error_message}