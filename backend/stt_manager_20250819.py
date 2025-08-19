from typing import Dict, Any, List, Optional
from stt_service_interface import STTServiceInterface
from assemblyai_service import AssemblyAIService
from daglo_service import DagloService
import logging

logger = logging.getLogger(__name__)

class STTManager:
    """
    여러 STT 서비스를 관리하는 매니저 클래스
    """
    
    def __init__(self):
        self.services: Dict[str, STTServiceInterface] = {}
        self.default_service = None
        self._initialize_services()
    
    def _initialize_services(self):
        """사용 가능한 STT 서비스들을 초기화합니다."""
        # AssemblyAI 서비스 추가
        try:
            assemblyai = AssemblyAIService()
            if assemblyai.is_configured():
                self.services["assemblyai"] = assemblyai
                if not self.default_service:
                    self.default_service = "assemblyai"
                logger.info("AssemblyAI 서비스가 초기화되었습니다.")
            else:
                logger.warning("AssemblyAI 서비스가 설정되지 않았습니다.")
        except Exception as e:
            logger.error(f"AssemblyAI 서비스 초기화 실패: {e}")
        
        # Daglo 서비스 추가
        try:
            daglo = DagloService()
            if daglo.is_configured():
                self.services["daglo"] = daglo
                if not self.default_service:
                    self.default_service = "daglo"
                logger.info("Daglo 서비스가 초기화되었습니다.")
            else:
                logger.warning("Daglo 서비스가 설정되지 않았습니다.")
        except Exception as e:
            logger.error(f"Daglo 서비스 초기화 실패: {e}")
        
        if not self.services:
            logger.error("사용 가능한 STT 서비스가 없습니다.")
        else:
            logger.info(f"초기화된 STT 서비스: {list(self.services.keys())}")
            logger.info(f"기본 서비스: {self.default_service}")
    
    def get_available_services(self) -> List[str]:
        """사용 가능한 서비스 목록을 반환합니다."""
        return list(self.services.keys())
    
    def get_service(self, service_name: str) -> Optional[STTServiceInterface]:
        """특정 서비스를 반환합니다."""
        return self.services.get(service_name)
    
    def get_default_service(self) -> Optional[STTServiceInterface]:
        """기본 서비스를 반환합니다."""
        if self.default_service:
            return self.services.get(self.default_service)
        return None
    
    def set_default_service(self, service_name: str) -> bool:
        """기본 서비스를 설정합니다."""
        if service_name in self.services:
            self.default_service = service_name
            logger.info(f"기본 서비스가 {service_name}로 변경되었습니다.")
            return True
        return False
    
    def get_service_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """서비스 정보를 반환합니다."""
        service = self.services.get(service_name)
        if service:
            return {
                "name": service.get_service_name(),
                "supported_formats": service.get_supported_formats(),
                "max_file_size": service.get_max_file_size(),
                "is_configured": service.is_configured()
            }
        return None
    
    def get_all_services_info(self) -> Dict[str, Dict[str, Any]]:
        """모든 서비스 정보를 반환합니다."""
        info = {}
        for service_name in self.services:
            info[service_name] = self.get_service_info(service_name)
        return info
    
    def transcribe_with_service(
        self, 
        service_name: str,
        file_content: bytes, 
        filename: str, 
        language_code: str = "ko",
        **kwargs
    ) -> Dict[str, Any]:
        """지정된 서비스로 음성을 변환합니다."""
        service = self.services.get(service_name)
        if not service:
            return {
                "text": "",
                "confidence": 0.0,
                "audio_duration": 0.0,
                "language_code": language_code,
                "service_name": service_name,
                "transcript_id": "",
                "full_response": {},
                "processing_time": 0.0,
                "error": f"서비스 '{service_name}'를 찾을 수 없습니다."
            }
        
        return service.transcribe_file(
            file_content=file_content,
            filename=filename,
            language_code=language_code,
            **kwargs
        )
    
    def transcribe_with_default(
        self, 
        file_content: bytes, 
        filename: str, 
        language_code: str = "ko",
        **kwargs
    ) -> Dict[str, Any]:
        """기본 서비스로 음성을 변환합니다."""
        if not self.default_service:
            return {
                "text": "",
                "confidence": 0.0,
                "audio_duration": 0.0,
                "language_code": language_code,
                "service_name": "none",
                "transcript_id": "",
                "full_response": {},
                "processing_time": 0.0,
                "error": "사용 가능한 STT 서비스가 없습니다."
            }
        
        return self.transcribe_with_service(
            service_name=self.default_service,
            file_content=file_content,
            filename=filename,
            language_code=language_code,
            **kwargs
        )
    
    def transcribe_with_fallback(
        self, 
        file_content: bytes, 
        filename: str, 
        language_code: str = "ko",
        preferred_service: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """우선 서비스로 시도하고 실패시 다른 서비스로 폴백합니다."""
        # 시도할 서비스 순서 결정
        services_to_try = []
        
        if preferred_service and preferred_service in self.services:
            services_to_try.append(preferred_service)
        
        if self.default_service and self.default_service not in services_to_try:
            services_to_try.append(self.default_service)
        
        # 나머지 서비스들 추가
        for service_name in self.services:
            if service_name not in services_to_try:
                services_to_try.append(service_name)
        
        last_error = None
        
        # 각 서비스를 순서대로 시도
        for service_name in services_to_try:
            logger.info(f"STT 서비스 시도: {service_name}")
            
            result = self.transcribe_with_service(
                service_name=service_name,
                file_content=file_content,
                filename=filename,
                language_code=language_code,
                **kwargs
            )
            
            # 성공한 경우
            if not result.get("error"):
                logger.info(f"STT 변환 성공: {service_name}")
                return result
            
            # 실패한 경우 로그 기록
            last_error = result.get("error")
            logger.warning(f"STT 서비스 {service_name} 실패: {last_error}")
        
        # 모든 서비스 실패
        return {
            "text": "",
            "confidence": 0.0,
            "audio_duration": 0.0,
            "language_code": language_code,
            "service_name": "fallback_failed",
            "transcript_id": "",
            "full_response": {},
            "processing_time": 0.0,
            "error": f"모든 STT 서비스 실패. 마지막 오류: {last_error}"
        }
    
    def is_file_supported(self, filename: str, service_name: Optional[str] = None) -> bool:
        """파일이 지원되는지 확인합니다."""
        file_extension = filename.split('.')[-1].lower()
        
        if service_name:
            service = self.services.get(service_name)
            if service:
                return file_extension in service.get_supported_formats()
            return False
        
        # 모든 서비스에서 지원하는지 확인
        for service in self.services.values():
            if file_extension in service.get_supported_formats():
                return True
        
        return False
    
    def get_supported_formats(self, service_name: Optional[str] = None) -> List[str]:
        """지원되는 파일 형식을 반환합니다."""
        if service_name:
            service = self.services.get(service_name)
            if service:
                return service.get_supported_formats()
            return []
        
        # 모든 서비스에서 지원하는 형식들의 합집합
        all_formats = set()
        for service in self.services.values():
            all_formats.update(service.get_supported_formats())
        
        return list(all_formats)
    
    def get_all_supported_formats(self) -> List[str]:
        """모든 서비스에서 지원하는 파일 형식을 반환합니다."""
        return self.get_supported_formats()