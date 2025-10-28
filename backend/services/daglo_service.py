import os
import requests
import time
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from .stt_service_interface import STTServiceInterface

load_dotenv()

class DagloService(STTServiceInterface):
    """
    Daglo API를 사용한 음성-텍스트 변환 서비스
    """
    
    def __init__(self):
        self.api_key = os.getenv("DAGLO_API_KEY")
        self.base_url = os.getenv("DAGLO_API_URL", "https://api.daglo.ai/v1/transcribe")
        
        if not self.api_key:
            print("Warning: DAGLO_API_KEY가 설정되지 않았습니다.")
    
    def is_configured(self) -> bool:
        """서비스가 올바르게 설정되었는지 확인합니다."""
        return bool(self.api_key)
    
    def get_service_name(self) -> str:
        """서비스명을 반환합니다."""
        return "Daglo"
    
    def get_supported_formats(self) -> list:
        """지원하는 파일 형식 목록을 반환합니다."""
        return ['mp3', 'wav', 'm4a', 'ogg', 'flac', '3gp', '3gpp', 'ac3', 'aac', 'aiff', 'amr', 'au', 'opus', 'ra']
    
    def get_max_file_size(self) -> int:
        """최대 파일 크기를 반환합니다 (바이트 단위)."""
        return 100 * 1024 * 1024  # 100MB
    
    def transcribe_file(
        self, 
        file_content: bytes, 
        filename: str, 
        language_code: str = "ko",
        speaker_diarization_enable: bool = True,
        speaker_count_hint: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        음성 파일을 텍스트로 변환합니다.
        
        Args:
            file_content: 음성 파일의 바이트 데이터
            filename: 파일명
            language_code: 언어 코드 (기본값: "ko")
            speaker_diarization_enable: 화자 분리 활성화 여부 (기본값: True)
            speaker_count_hint: 예상 화자 수 힌트 (선택사항, 기본값: None)
            **kwargs: 추가 옵션
                
        Returns:
            Dict[str, Any]: 변환 결과
            
        Raises:
            Exception: STT 변환 실패 시
        """
        start_time = time.time()
        
        try:
            # 화자 분리 옵션 처리
            speaker_diarization_enable = kwargs.get("speaker_diarization_enable", speaker_diarization_enable)
            speaker_diarization_enable = bool(speaker_diarization_enable)
            speaker_count_hint = kwargs.get("speaker_count_hint", speaker_count_hint)
            try:
                speaker_count_hint = int(speaker_count_hint) if speaker_count_hint is not None else None
            except (TypeError, ValueError):
                speaker_count_hint = None

            stt_config: Dict[str, Any] = {}
            if speaker_diarization_enable:
                speaker_diarization_config = {"enable": True}
                if isinstance(speaker_count_hint, int) and speaker_count_hint > 0:
                    speaker_diarization_config["speakerCountHint"] = speaker_count_hint
                stt_config["speakerDiarization"] = speaker_diarization_config
                print(f"🎤 화자 분리 설정 활성화: {json.dumps(stt_config, ensure_ascii=False)}")
            else:
                print("🎤 화자 분리 설정 비활성화")
            
            # 파일 확장자 추출
            file_extension = filename.split('.')[-1].lower()
            
            # Daglo API 요청 헤더
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 파일 업로드를 위한 파일 객체 생성
            files = {
                "file": (filename, file_content, f"audio/{file_extension}")
            }
            
            # 추가 설정(sttConfig)을 폼 데이터에 포함
            post_kwargs: Dict[str, Any] = {"headers": headers, "files": files}
            if stt_config:
                post_kwargs["data"] = {"sttConfig": json.dumps(stt_config)}
            
            # 1단계: Daglo API에 음성 파일 업로드
            response = requests.post(self.base_url, **post_kwargs)
            
            if response.status_code != 200:
                raise Exception(f"Daglo API 오류: {response.status_code} - {response.text}")
            
            # RID 추출
            upload_result = response.json()
            rid = upload_result.get('rid')
            
            if not rid:
                raise Exception("RID를 받지 못했습니다.")
            
            # 2단계: RID로 결과 조회 (폴링)
            result_url = f"{self.base_url}/{rid}"
            max_attempts = 30  # 최대 30번 시도 (약 5분)
            
            for attempt in range(max_attempts):
                result_response = requests.get(result_url, headers=headers)
                
                if result_response.status_code == 200:
                    result_data = result_response.json()
                    status = result_data.get('status')
                    
                    if status == 'transcribed':
                        # 변환 완료
                        processing_time = time.time() - start_time
                        
                        # STT 텍스트 추출
                        transcribed_text = ""
                        if 'sttResults' in result_data and result_data['sttResults']:
                            stt_results = result_data['sttResults']
                            if isinstance(stt_results, list) and len(stt_results) > 0:
                                # sttResults가 리스트인 경우 첫 번째 요소에서 transcript 추출
                                transcribed_text = stt_results[0].get('transcript', '') if isinstance(stt_results[0], dict) else ''
                            elif isinstance(stt_results, dict):
                                # sttResults가 딕셔너리인 경우
                                transcribed_text = stt_results.get('transcript', '')
                        else:
                            transcribed_text = result_data.get('text', '')
                        
                        return {
                            "text": transcribed_text,
                            "confidence": result_data.get('confidence', 0.8),  # Daglo는 신뢰도를 제공하지 않으므로 기본값
                            "audio_duration": result_data.get('duration', 0.0),
                            "language_code": language_code,
                            "service_name": self.get_service_name(),
                            "transcript_id": rid,
                            "full_response": result_data,
                            "processing_time": processing_time,
                            "error": None
                        }
                        
                    elif status in ['failed', 'error']:
                        # 변환 실패
                        raise Exception(f"Daglo 변환 실패: {status}")
                    else:
                        # 아직 처리 중, 10초 대기
                        time.sleep(10)
                else:
                    raise Exception(f"결과 조회 실패: {result_response.status_code} - {result_response.text}")
            
            # 최대 시도 횟수 초과
            raise Exception(f"변환 타임아웃 - 최대 시도 횟수({max_attempts}) 초과")
            
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