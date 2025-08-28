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
            
            # API 요청 데이터 준비
            request_data = {
                "transcriptLocaleHints": ["EN_US"],
                "translationLocales": ["KO_KR", "JA_JP"]
            }
            
            # API 요청
            logger.info(f"Tiro API 요청 시작: {filename}")
            response = requests.post(
                f"{self.base_url}/v1/external/voice-file/jobs",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=request_data
            )
            
            # Auth -> response ( id, uri )
            # id, uri 파일 업로드
            # id w
            
            processing_time = time.time() - start_time
            
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
                    f"https://api.tiro.ooo/v1/external/voice-file/jobs/{job_id}/upload-complete",
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
                    f"https://api.tiro.ooo/v1/external/voice-file/jobs/{job_id}/translations/KO_KR",
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