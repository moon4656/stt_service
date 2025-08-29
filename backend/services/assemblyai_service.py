import os
import requests
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from .stt_service_interface import STTServiceInterface

load_dotenv()

class AssemblyAIService(STTServiceInterface):
    """
    AssemblyAI API를 사용한 음성-텍스트 변환 서비스
    """
    
    def __init__(self):
        self.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        self.base_url = "https://api.assemblyai.com/v2"
        self.upload_url = f"{self.base_url}/upload"
        self.transcript_url = f"{self.base_url}/transcript"
        
        if not self.api_key:
            print("Warning: ASSEMBLYAI_API_KEY가 설정되지 않았습니다.")
    
    def is_configured(self) -> bool:
        """서비스가 올바르게 설정되었는지 확인합니다."""
        return bool(self.api_key)
    
    def get_service_name(self) -> str:
        """서비스명을 반환합니다."""
        return "AssemblyAI"
    
    def get_supported_formats(self) -> list:
        """지원하는 파일 형식 목록을 반환합니다."""
        return ['mp3', 'wav', 'm4a', 'flac', 'ogg', 'aac', 'aiff', 'au', 'opus']
    
    def get_max_file_size(self) -> int:
        """최대 파일 크기를 반환합니다 (바이트 단위)."""
        return 5 * 1024 * 1024 * 1024  # 5GB
    
    def upload_file(self, file_content: bytes) -> str:
        """
        AssemblyAI에 파일을 업로드하고 URL을 반환합니다.
        
        Args:
            file_content: 업로드할 파일의 바이트 데이터
            
        Returns:
            str: 업로드된 파일의 URL
        """
        headers = {
            "authorization": self.api_key,
            "content-type": "application/octet-stream"
        }
        
        response = requests.post(
            self.upload_url,
            headers=headers,
            data=file_content
        )
        
        if response.status_code != 200:
            raise Exception(f"파일 업로드 실패: {response.status_code} - {response.text}")
        
        return response.json()["upload_url"]
    
    def submit_transcription(self, audio_url: str, **options) -> str:
        """
        음성 변환 작업을 제출합니다.
        
        Args:
            audio_url: 변환할 오디오 파일의 URL
            **options: 추가 옵션들
            
        Returns:
            str: 트랜스크립트 ID
        """
        headers = {
            "authorization": self.api_key,
            "content-type": "application/json"
        }
        
        data = {
            "audio_url": audio_url,
            **options
        }
        
        response = requests.post(
            self.transcript_url,
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"변환 작업 제출 실패: {response.status_code} - {response.text}")
        
        return response.json()["id"]
    
    def get_transcription_result(self, transcript_id: str) -> Dict[str, Any]:
        """
        변환 결과를 조회합니다.
        
        Args:
            transcript_id: 트랜스크립트 ID
            
        Returns:
            Dict[str, Any]: 변환 결과
        """
        headers = {
            "authorization": self.api_key
        }
        
        url = f"{self.transcript_url}/{transcript_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"결과 조회 실패: {response.status_code} - {response.text}")
        
        return response.json()
    
    def wait_for_completion(self, transcript_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """
        변환 완료까지 대기합니다.
        
        Args:
            transcript_id: 트랜스크립트 ID
            max_wait_time: 최대 대기 시간 (초)
            
        Returns:
            Dict[str, Any]: 완료된 변환 결과
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            result = self.get_transcription_result(transcript_id)
            status = result.get("status")
            
            if status == "completed":
                return result
            elif status == "error":
                raise Exception(f"변환 실패: {result.get('error', '알 수 없는 오류')}")
            
            # 5초 대기 후 다시 확인
            time.sleep(5)
        
        raise Exception(f"변환 시간 초과 ({max_wait_time}초)")
    
    def transcribe_file(
        self, 
        file_content: bytes, 
        filename: str, 
        language_code: str = "ko",
        punctuate: bool = True,
        format_text: bool = True,
        summarization: bool = False,
        summary_model: str = "informative",
        summary_type: str = "bullets",
        **kwargs
    ) -> Dict[str, Any]:
        """
        음성 파일을 텍스트로 변환합니다.
        
        Args:
            file_content: 음성 파일의 바이트 데이터
            filename: 파일명
            language_code: 언어 코드
            punctuate: 구두점 추가 여부
            format_text: 텍스트 포맷팅 여부
            summarization: 요약 기능 사용 여부
            summary_model: 요약 모델 (informative, conversational, catchy)
            summary_type: 요약 타입 (bullets, paragraph, headline, gist)
            **kwargs: 추가 옵션
            
        Returns:
            Dict[str, Any]: 변환 결과
        """
        start_time = time.time()
        
        try:
            # 1. 파일 업로드
            audio_url = self.upload_file(file_content)
            
            # 2. 변환 작업 제출
            options = {
                "language_code": language_code,
                "punctuate": punctuate,
                "format_text": format_text,
                **kwargs
            }
            
            # 요약 기능 추가
            if summarization:
                options["summarization"] = True
                options["summary_model"] = summary_model
                options["summary_type"] = summary_type
            
            transcript_id = self.submit_transcription(audio_url, **options)
            
            # 3. 완료까지 대기
            result = self.wait_for_completion(transcript_id)
            
            processing_time = time.time() - start_time
            
            # 4. 결과 정리
            # AssemblyAI API는 audio_duration 필드를 제공하지 않으므로 0.0으로 설정
            response_data = {
                "text": result.get("text", ""),
                "confidence": result.get("confidence", 0.0),
                "audio_duration": 0.0,  # AssemblyAI API에서 제공하지 않음
                "language_code": result.get("language_code", language_code),
                "service_name": self.get_service_name(),
                "transcript_id": transcript_id,
                "full_response": result,
                "processing_time": processing_time,
                "error": None
            }
            
            # 요약이 있는 경우 추가
            if summarization and result.get("summary"):
                response_data["summary"] = result.get("summary")
                
            return response_data
            
        except Exception as e:
            processing_time = time.time() - start_time
            return {
                "text": "",
                "confidence": 0.0,
                "audio_duration": 0.0,
                "language_code": language_code,
                "service_name": self.get_service_name(),
                "transcript_id": "",
                "full_response": {},
                "processing_time": processing_time,
                "error": str(e)
            }