import requests
import json
import os
import sys

def test_daglo_speaker_diarization():
    """
    Daglo 서비스의 화자 분리 기능을 테스트합니다.
    """
    print("🧪 Daglo 화자 분리 기능 테스트 시작...")
    
    # 테스트용 작은 오디오 파일 생성 (실제 테스트에서는 실제 오디오 파일 사용 권장)
    test_file_path = "test_audio_daglo.mp3"
    with open(test_file_path, "wb") as f:
        # 실제 오디오 데이터가 아닌 더미 데이터
        f.write(b"fake audio content for daglo speaker diarization testing")
    
    try:
        # 1. 기본 Daglo 서비스 테스트 (화자 분리 기본 활성화)
        print("\n📡 1. 기본 Daglo 서비스 테스트 (화자 분리 기본 활성화)")
        with open(test_file_path, "rb") as f:
            files = {"file": ("test_audio_daglo.mp3", f, "audio/mp3")}
            data = {"service": "daglo"}
            response = requests.post("http://localhost:8000/transcribe/", files=files, data=data)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 응답 성공")
            print(f"Service Used: {result.get('service_used', 'N/A')}")
            print(f"Text: {result.get('text', 'N/A')}")
            print(f"Speaker Info: {result.get('speaker_info', 'N/A')}")
        else:
            print(f"❌ 응답 실패: {response.text}")
        
        # 2. 명시적으로 화자 분리 활성화 + 화자 수 힌트
        print("\n📡 2. 명시적 화자 분리 활성화 + 화자 수 힌트 (2명)")
        with open(test_file_path, "rb") as f:
            files = {"file": ("test_audio_daglo.mp3", f, "audio/mp3")}
            data = {
                "service": "daglo",
                "speaker_diarization_enable": "true",
                "speaker_count_hint": "2"
            }
            response = requests.post("http://localhost:8000/transcribe/", files=files, data=data)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 응답 성공")
            print(f"Service Used: {result.get('service_used', 'N/A')}")
            print(f"Text: {result.get('text', 'N/A')}")
            print(f"Speaker Info: {result.get('speaker_info', 'N/A')}")
        else:
            print(f"❌ 응답 실패: {response.text}")
        
        # 3. 화자 분리 비활성화 테스트
        print("\n📡 3. 화자 분리 비활성화 테스트")
        with open(test_file_path, "rb") as f:
            files = {"file": ("test_audio_daglo.mp3", f, "audio/mp3")}
            data = {
                "service": "daglo",
                "speaker_diarization_enable": "false"
            }
            response = requests.post("http://localhost:8000/transcribe/", files=files, data=data)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 응답 성공")
            print(f"Service Used: {result.get('service_used', 'N/A')}")
            print(f"Text: {result.get('text', 'N/A')}")
            print(f"Speaker Info: {result.get('speaker_info', 'N/A')}")
        else:
            print(f"❌ 응답 실패: {response.text}")
            
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 테스트 파일 삭제
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            print(f"\n🗑️ 테스트 파일 삭제: {test_file_path}")

if __name__ == "__main__":
    test_daglo_speaker_diarization()