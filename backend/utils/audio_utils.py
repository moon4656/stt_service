import io
import wave
import struct
from typing import Optional

def get_audio_duration(file_content: bytes, filename: str) -> Optional[float]:
    """
    음성파일의 재생 시간을 계산합니다.
    
    Args:
        file_content: 음성 파일의 바이트 데이터
        filename: 파일명 (확장자 확인용)
        
    Returns:
        float: 재생 시간 (초), 실패시 None
    """
    try:
        file_extension = filename.split('.')[-1].lower()
        
        if file_extension == 'wav':
            return _get_wav_duration(file_content)
        elif file_extension in ['mp3', 'mp4', 'm4a', 'aac', 'ogg', 'flac']:
            # 다른 포맷들은 mutagen 라이브러리 사용
            return _get_duration_with_mutagen(file_content, file_extension)
        else:
            print(f"⚠️ 지원하지 않는 오디오 포맷: {file_extension}")
            return None
            
    except Exception as e:
        print(f"❌ 오디오 duration 계산 실패: {e}")
        return None

def _get_wav_duration(file_content: bytes) -> Optional[float]:
    """
    WAV 파일의 재생 시간을 계산합니다.
    """
    try:
        # 바이트 데이터를 파일 객체로 변환
        audio_file = io.BytesIO(file_content)
        
        with wave.open(audio_file, 'rb') as wav_file:
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            duration = frames / float(sample_rate)
            return duration
            
    except Exception as e:
        print(f"❌ WAV duration 계산 실패: {e}")
        return None

def _get_duration_with_mutagen(file_content: bytes, file_extension: str) -> Optional[float]:
    """
    mutagen 라이브러리를 사용하여 다양한 오디오 포맷의 재생 시간을 계산합니다.
    """
    try:
        from mutagen import File as MutagenFile
        import tempfile
        import os
        
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(suffix=f'.{file_extension}', delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # mutagen으로 메타데이터 읽기
            audio_file = MutagenFile(temp_file_path)
            if audio_file is not None and hasattr(audio_file, 'info'):
                duration = audio_file.info.length
                return duration
            else:
                print(f"⚠️ mutagen으로 파일 정보를 읽을 수 없음: {file_extension}")
                return None
                
        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except ImportError:
        print("⚠️ mutagen 라이브러리가 설치되지 않음. WAV 파일만 지원됩니다.")
        print("   설치 명령: pip install mutagen")
        return None
    except Exception as e:
        print(f"❌ mutagen duration 계산 실패: {e}")
        return None

def format_duration(duration: Optional[float]) -> str:
    """
    재생 시간을 사람이 읽기 쉬운 형태로 포맷합니다.
    
    Args:
        duration: 재생 시간 (초)
        
    Returns:
        str: 포맷된 시간 문자열
    """
    if duration is None:
        return "알 수 없음"
    
    if duration < 60:
        return f"{duration:.1f}초"
    elif duration < 3600:
        minutes = int(duration // 60)
        seconds = duration % 60
        return f"{minutes}분 {seconds:.1f}초"
    else:
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = duration % 60
        return f"{hours}시간 {minutes}분 {seconds:.1f}초"