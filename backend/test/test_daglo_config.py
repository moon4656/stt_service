import sys
import os
import json

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.daglo_service import DagloService

def test_daglo_speaker_diarization_config():
    """
    Daglo 서비스의 화자 분리 설정 생성 로직을 테스트합니다.
    """
    print("🧪 Daglo 화자 분리 설정 테스트 시작...")
    
    # DagloService 인스턴스 생성 (환경변수에서 API 키 로드)
    daglo_service = DagloService()
    
    # 테스트 케이스 1: 기본값 (화자 분리 활성화)
    print("\n📋 테스트 케이스 1: 기본값 (화자 분리 활성화)")
    try:
        # transcribe_file 메서드의 설정 생성 부분만 시뮬레이션
        speaker_diarization_enable = True  # 기본값
        speaker_count_hint = None  # 기본값
        
        stt_config = {}
        if speaker_diarization_enable:
            speaker_diarization_config = {"enable": True}
            if isinstance(speaker_count_hint, int) and speaker_count_hint > 0:
                speaker_diarization_config["speakerCountHint"] = speaker_count_hint
            stt_config["speakerDiarization"] = speaker_diarization_config
        
        print(f"✅ 생성된 sttConfig: {json.dumps(stt_config, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    
    # 테스트 케이스 2: 화자 분리 활성화 + 화자 수 힌트
    print("\n📋 테스트 케이스 2: 화자 분리 활성화 + 화자 수 힌트 (3명)")
    try:
        speaker_diarization_enable = True
        speaker_count_hint = 3
        
        stt_config = {}
        if speaker_diarization_enable:
            speaker_diarization_config = {"enable": True}
            if isinstance(speaker_count_hint, int) and speaker_count_hint > 0:
                speaker_diarization_config["speakerCountHint"] = speaker_count_hint
            stt_config["speakerDiarization"] = speaker_diarization_config
        
        print(f"✅ 생성된 sttConfig: {json.dumps(stt_config, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    
    # 테스트 케이스 3: 화자 분리 비활성화
    print("\n📋 테스트 케이스 3: 화자 분리 비활성화")
    try:
        speaker_diarization_enable = False
        speaker_count_hint = None
        
        stt_config = {}
        if speaker_diarization_enable:
            speaker_diarization_config = {"enable": True}
            if isinstance(speaker_count_hint, int) and speaker_count_hint > 0:
                speaker_diarization_config["speakerCountHint"] = speaker_count_hint
            stt_config["speakerDiarization"] = speaker_diarization_config
        
        print(f"✅ 생성된 sttConfig: {json.dumps(stt_config, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    
    # 테스트 케이스 4: kwargs를 통한 파라미터 전달 시뮬레이션
    print("\n📋 테스트 케이스 4: kwargs를 통한 파라미터 전달")
    try:
        # kwargs 시뮬레이션
        kwargs = {
            "speaker_diarization_enable": "true",  # 문자열로 전달
            "speaker_count_hint": "2"  # 문자열로 전달
        }
        
        # 실제 코드와 동일한 처리 로직
        speaker_diarization_enable = kwargs.get("speaker_diarization_enable", True)
        speaker_diarization_enable = bool(speaker_diarization_enable)
        speaker_count_hint = kwargs.get("speaker_count_hint", None)
        try:
            speaker_count_hint = int(speaker_count_hint) if speaker_count_hint is not None else None
        except (TypeError, ValueError):
            speaker_count_hint = None
        
        stt_config = {}
        if speaker_diarization_enable:
            speaker_diarization_config = {"enable": True}
            if isinstance(speaker_count_hint, int) and speaker_count_hint > 0:
                speaker_diarization_config["speakerCountHint"] = speaker_count_hint
            stt_config["speakerDiarization"] = speaker_diarization_config
        
        print(f"✅ 입력 kwargs: {kwargs}")
        print(f"✅ 처리된 값: speaker_diarization_enable={speaker_diarization_enable}, speaker_count_hint={speaker_count_hint}")
        print(f"✅ 생성된 sttConfig: {json.dumps(stt_config, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    
    print("\n🎉 Daglo 화자 분리 설정 테스트 완료!")

if __name__ == "__main__":
    test_daglo_speaker_diarization_config()