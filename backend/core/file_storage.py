import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class FileStorageManager:
    """
    STT 서비스에서 업로드된 음성 파일을 관리하는 클래스
    파일 저장 경로: /stt_storage/{user_uuid}/{yyyy-mm-dd}/{request_id}/음성파일
    """
    
    def __init__(self, base_storage_path: str = "stt_storage"):
        """
        파일 저장 관리자 초기화
        
        Args:
            base_storage_path: 기본 저장 경로 (기본값: "stt_storage")
        """
        self.base_storage_path = Path(base_storage_path)
        self._ensure_base_directory()
    
    def _ensure_base_directory(self):
        """
        기본 저장 디렉토리가 존재하는지 확인하고 없으면 생성합니다.
        """
        try:
            self.base_storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 기본 저장 디렉토리 확인/생성 완료: {self.base_storage_path}")
        except Exception as e:
            logger.error(f"❌ 기본 저장 디렉토리 생성 실패: {e}")
            raise
    
    def get_file_storage_path(self, user_uuid: str, request_id: str, filename: str) -> Path:
        """
        파일 저장 경로를 생성합니다.
        
        Args:
            user_uuid: 사용자 UUID
            request_id: 요청 ID
            filename: 원본 파일명
            
        Returns:
            Path: 파일 저장 경로
        """
        # 현재 날짜를 YYYY-MM-DD 형식으로 가져오기
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 경로 구성: stt_storage/{user_uuid}/{yyyy-mm-dd}/{request_id}/
        storage_dir = self.base_storage_path / user_uuid / today / request_id
        
        # 파일 전체 경로
        file_path = storage_dir / filename
        
        return file_path
    
    def save_audio_file(self, user_uuid: str, request_id: str, filename: str, file_content: bytes) -> str:
        """
        음성 파일을 지정된 경로에 저장합니다.
        
        Args:
            user_uuid: 사용자 UUID
            request_id: 요청 ID
            filename: 원본 파일명
            file_content: 파일 내용 (바이트)
            
        Returns:
            str: 저장된 파일의 절대 경로
            
        Raises:
            Exception: 파일 저장 실패 시
        """
        try:
            # 저장 경로 생성
            file_path = self.get_file_storage_path(user_uuid, request_id, filename)
            
            # 디렉토리 생성 (부모 디렉토리까지 모두 생성)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 파일 저장
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"💾 음성 파일 저장 완료: {file_path}")
            logger.info(f"📊 파일 크기: {len(file_content):,} bytes")
            
            return str(file_path.absolute())
            
        except Exception as e:
            logger.error(f"❌ 음성 파일 저장 실패: {e}")
            logger.error(f"   - 사용자: {user_uuid}")
            logger.error(f"   - 요청 ID: {request_id}")
            logger.error(f"   - 파일명: {filename}")
            raise
    
    def get_file_path(self, user_uuid: str, request_id: str, filename: str) -> Optional[str]:
        """
        저장된 파일의 경로를 반환합니다.
        
        Args:
            user_uuid: 사용자 UUID
            request_id: 요청 ID
            filename: 원본 파일명
            
        Returns:
            Optional[str]: 파일 경로 (파일이 존재하지 않으면 None)
        """
        file_path = self.get_file_storage_path(user_uuid, request_id, filename)
        
        if file_path.exists():
            return str(file_path.absolute())
        else:
            logger.warning(f"⚠️ 파일이 존재하지 않습니다: {file_path}")
            return None
    
    def delete_file(self, user_uuid: str, request_id: str, filename: str) -> bool:
        """
        저장된 파일을 삭제합니다.
        
        Args:
            user_uuid: 사용자 UUID
            request_id: 요청 ID
            filename: 원본 파일명
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            file_path = self.get_file_storage_path(user_uuid, request_id, filename)
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"🗑️ 파일 삭제 완료: {file_path}")
                
                # 빈 디렉토리 정리 (선택적)
                self._cleanup_empty_directories(file_path.parent)
                
                return True
            else:
                logger.warning(f"⚠️ 삭제할 파일이 존재하지 않습니다: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 파일 삭제 실패: {e}")
            return False
    
    def _cleanup_empty_directories(self, directory: Path):
        """
        빈 디렉토리를 정리합니다 (재귀적으로 상위 디렉토리까지).
        
        Args:
            directory: 정리할 디렉토리
        """
        try:
            # 디렉토리가 비어있고, 기본 저장 경로가 아닌 경우에만 삭제
            if (directory.exists() and 
                not any(directory.iterdir()) and 
                directory != self.base_storage_path):
                
                directory.rmdir()
                logger.info(f"🧹 빈 디렉토리 정리: {directory}")
                
                # 상위 디렉토리도 확인
                self._cleanup_empty_directories(directory.parent)
                
        except Exception as e:
            logger.debug(f"디렉토리 정리 중 오류 (무시됨): {e}")
    
    def get_user_storage_info(self, user_uuid: str) -> dict:
        """
        특정 사용자의 저장 공간 정보를 반환합니다.
        
        Args:
            user_uuid: 사용자 UUID
            
        Returns:
            dict: 저장 공간 정보
        """
        user_path = self.base_storage_path / user_uuid
        
        if not user_path.exists():
            return {
                "user_uuid": user_uuid,
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0.0,
                "directories": []
            }
        
        total_files = 0
        total_size = 0
        directories = []
        
        try:
            for item in user_path.rglob("*"):
                if item.is_file():
                    total_files += 1
                    total_size += item.stat().st_size
                elif item.is_dir():
                    directories.append(str(item.relative_to(user_path)))
            
            return {
                "user_uuid": user_uuid,
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "directories": sorted(directories)
            }
            
        except Exception as e:
            logger.error(f"❌ 사용자 저장 공간 정보 조회 실패: {e}")
            return {
                "user_uuid": user_uuid,
                "error": str(e)
            }


# 전역 파일 저장 관리자 인스턴스
file_storage_manager = FileStorageManager()


def save_uploaded_file(user_uuid: str, request_id: str, filename: str, file_content: bytes) -> str:
    """
    업로드된 파일을 저장하는 편의 함수
    
    Args:
        user_uuid: 사용자 UUID
        request_id: 요청 ID
        filename: 파일명
        file_content: 파일 내용
        
    Returns:
        str: 저장된 파일 경로
    """
    return file_storage_manager.save_audio_file(user_uuid, request_id, filename, file_content)


def get_stored_file_path(user_uuid: str, request_id: str, filename: str) -> Optional[str]:
    """
    저장된 파일 경로를 조회하는 편의 함수
    
    Args:
        user_uuid: 사용자 UUID
        request_id: 요청 ID
        filename: 파일명
        
    Returns:
        Optional[str]: 파일 경로 (없으면 None)
    """
    return file_storage_manager.get_file_path(user_uuid, request_id, filename)