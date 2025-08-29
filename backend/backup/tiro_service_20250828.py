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
            # 파일 업로드 및 변환 요청
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
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
            
            # API 요청 데이터 준비
            request_data = {
                "transcriptLocaleHints": ["EN_US"],
                "translationLocales": ["KO_KR", "JA_JP"]
            }

            processing_time = time.time() - start_time
            payload = {}
            
            # API 요청
            logger.info(f"Tiro API 요청 시작: {filename}")
            response = requests.post(
                f"{self.base_url}/jobs",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            # 응답 처리
            if response.status_code == 200:
                result = response.json()

                logger.info(f"Tiro response id: {result.get('id')}, uploadUri : {result.get('uploadUri')}")
                
                # response 받고 
                job_id = result.get('id')
                uploadUri = result.get('uploadUri')
                
                # uploadUri에 파일 업로드
                upload_response = self._upload_file_to_uri(uploadUri, file_content, filename)
                if not upload_response:
                    logger.error("파일 업로드 실패")
                    return {
                        "text": "",
                        "confidence": 0.0,
                        "audio_duration": 0.0,
                        "language_code": language_code,
                        "service_name": self.get_service_name(),
                        "transcript_id": "",
                        "full_response": {},
                        "processing_time": processing_time,
                        "error": "파일 업로드 실패"
                    }

                # upload complete 알림
                complete_response = requests.put(
                    f"{self.base_url}/jobs/{job_id}/upload-complete",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                    
                if complete_response.status_code != 200:
                    logger.error(f"업로드 완료 알림 실패: {complete_response.status_code}")
                    return {
                            "text": "",
                            "confidence": 0.0,
                            "audio_duration": 0.0,
                            "language_code": language_code,
                            "service_name": self.get_service_name(),
                            "transcript_id": "",
                            "full_response": {},
                            "processing_time": processing_time,
                            "error": "업로드 완료 알림 실패"
                        }
                
                # 번역 결과 조회 (폴링)
                translation_result = self._get_translation_result(job_id, max_retries=30)
                if translation_result is None:
                    logger.error("번역 결과 조회 실패")
                    return {
                        "text": "",
                        "confidence": 0.0,
                        "audio_duration": 0.0,
                        "language_code": language_code,
                        "service_name": self.get_service_name(),
                        "transcript_id": job_id,
                        "full_response": {},
                        "processing_time": time.time() - start_time,
                        "error": "번역 결과 조회 실패"
                    }
                
                # 최종 처리 시간 계산
                processing_time = time.time() - start_time
                
                # 결과 형식 변환
                return {
                    "text": translation_result.get("text", ""),
                    "confidence": translation_result.get("confidence", 0.9),  # Tiro는 일반적으로 높은 신뢰도
                    "audio_duration": translation_result.get("duration", 0.0),
                    "language_code": "ko",  # 한국어로 번역된 결과
                    "service_name": self.get_service_name(),
                    "transcript_id": job_id,
                    "full_response": {
                        "job_response": result,
                        "translation_response": translation_result
                    },
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
    
    def _upload_file_to_uri(self, upload_uri: str, file_content: bytes, filename: str) -> bool:
        """
        주어진 URI에 파일을 업로드합니다.
        
        Args:
            upload_uri: 업로드할 URI
            file_content: 파일 내용 (바이트)
            filename: 파일명
            
        Returns:
            bool: 업로드 성공 여부
        """
        try:
            files = {
                "file": (filename, file_content)
            }
            
            response = requests.put(
                upload_uri,
                files=files
            )
            
            if response.status_code in [200, 201, 204]:
                logger.info(f"파일 업로드 성공: {filename}")
                return True
            else:
                logger.error(f"파일 업로드 실패: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"파일 업로드 중 예외 발생: {str(e)}")
            return False
    
    def _get_translation_result(self, job_id: str, max_retries: int = 30) -> Dict[str, Any]:
        """
        번역 결과를 조회합니다 (폴링 방식).
        
        Args:
            job_id: 작업 ID
            max_retries: 최대 재시도 횟수
            
        Returns:
            Dict[str, Any]: 번역 결과 또는 None
        """
        import time
        
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f"{self.base_url}/jobs/{job_id}/translations",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # 번역이 완료되었는지 확인
                    if result.get("status") == "completed" or result.get("text"):
                        logger.info(f"번역 결과 조회 성공: {job_id}")
                        return result
                    else:
                        logger.info(f"번역 진행 중... (시도 {attempt + 1}/{max_retries})")
                        time.sleep(2)  # 2초 대기
                        continue
                        
                elif response.status_code == 404:
                    logger.info(f"번역 작업 대기 중... (시도 {attempt + 1}/{max_retries})")
                    time.sleep(2)
                    continue
                    
                else:
                    logger.error(f"번역 결과 조회 오류: {response.status_code} - {response.text}")
                    time.sleep(2)
                    continue
                    
            except Exception as e:
                logger.error(f"번역 결과 조회 중 예외 발생: {str(e)}")
                time.sleep(2)
                continue
        
        logger.error(f"번역 결과 조회 최대 재시도 횟수 초과: {job_id}")
        return None
    
    # -------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------
    def create_job(self, transcript_locale_hints=None, translation_locales=None):
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
    
    def upload_file(self, upload_uri, file_path):
        with open(file_path, 'rb') as file:
            response = requests.put(upload_uri, data=file)
            response.raise_for_status()
        
        print(f"File uploaded successfully: {file_path}")
    
    def notify_upload_complete(self, job_id):
        response = requests.put(
            f"{self.base_url}/jobs/{job_id}/upload-complete",
            headers=self.headers
        )
        response.raise_for_status()
        print(f"Upload complete notification sent for job: {job_id}")
    
    def poll_job_status(self, job_id, max_wait_time=600):
        interval = 1
        max_interval = 10
        elapsed_time = 0
        
        success_statuses = ["TRANSLATION_COMPLETED"] # until translation
        # success_statuses = ["TRANSCRIPT_COMPLETED"]
        failure_statuses = ["FAILED"]
        
        while elapsed_time < max_wait_time:
            response = requests.get(
                f"{self.base_url}/jobs/{job_id}",
                headers=self.headers
            )
            response.raise_for_status()
            
            job_data = response.json()
            status = job_data.get("status")
            
            print(f"Job {job_id} status: {status} (elapsed: {elapsed_time}s)")
            
            if status in success_statuses:
                print(f"Job completed successfully with status: {status}")
                return status
            elif status in failure_statuses:
                print(f"Job failed with status: {status}")
                return status
            
            time.sleep(interval)
            elapsed_time += interval
            
            # Exponential backoff with cap
            interval = min(interval * 2, max_interval)
        
        print(f"Polling timeout after {max_wait_time} seconds")
        return "TIMEOUT"
    
    def get_transcript(self, job_id):
        response = requests.get(
            f"{self.base_url}/jobs/{job_id}/transcript",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_translations(self, job_id):
        response = requests.get(
            f"{self.base_url}/jobs/{job_id}/translations",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def process_audio_file(self, file_path, transcript_locale_hints=None, translation_locales=None):
        """
        Complete workflow: create job, upload file, notify, poll, and get results
        
        Args:
            file_path (str): Path to audio file
            transcript_locale_hints (list): Optional locale hints
            translation_locales (list): Optional translation locales
            
        Returns:
            dict: Complete results including transcript and translations
        """
        print(f"Starting audio processing for: {file_path}")
        
        # Step 1: Create job
        job_response = self.create_job(transcript_locale_hints, translation_locales)
        job_id = job_response["id"]
        upload_uri = job_response["uploadUri"]
        
        print(f"Job created: {job_id}")
        
        # Step 2: Upload file
        self.upload_file(upload_uri, file_path)
        
        # Step 3: Notify upload complete
        self.notify_upload_complete(job_id)
        
        # Step 4: Poll for completion
        final_status = self.poll_job_status(job_id)
        
        if final_status not in ["TRANSCRIPT_COMPLETED", "TRANSLATION_COMPLETED"]:
            return {"error": f"Job failed with status: {final_status}"}
        
        # Step 5: Get results
        results = {}
        
        try:
            transcript = self.get_transcript(job_id)
            results["transcript"] = transcript
        except requests.exceptions.RequestException as e:
            print(f"Error getting transcript: {e}")
        
        if translation_locales:
            try:
                translations = self.get_translations(job_id)
                results["translations"] = translations
            except requests.exceptions.RequestException as e:
                print(f"Error getting translations: {e}")
        
        return results