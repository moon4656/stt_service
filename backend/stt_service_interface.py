from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class STTServiceInterface(ABC):
    """
    STT 서비스의 공통 인터페이스를 정의합니다.
    모든 STT 서비스는 이 인터페이스를 구현해야 합니다.
    """
    
    @abstractmethod
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
            {
                "text": str,  # 변환된 텍스트
                "confidence": float,  # 신뢰도 (0.0-1.0)
                "audio_duration": float,  # 오디오 길이 (초)
                "language_code": str,  # 감지된 언어 코드
                "service_name": str,  # 사용된 서비스명
                "transcript_id": str,  # 서비스별 트랜스크립트 ID
                "full_response": Dict[str, Any],  # 원본 응답 데이터
                "processing_time": float,  # 처리 시간 (초)
                "error": Optional[str]  # 오류 메시지 (있는 경우)
            }
        """
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """
        서비스가 올바르게 설정되었는지 확인합니다.
        
        Returns:
            bool: 설정 완료 여부
        """
        pass
    
    @abstractmethod
    def get_service_name(self) -> str:
        """
        서비스명을 반환합니다.
        
        Returns:
            str: 서비스명
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> list:
        """
        지원하는 파일 형식 목록을 반환합니다.
        
        Returns:
            list: 지원 형식 리스트
        """
        pass
    
    @abstractmethod
    def get_max_file_size(self) -> int:
        """
        최대 파일 크기를 반환합니다 (바이트 단위).
        
        Returns:
            int: 최대 파일 크기
        """
        pass