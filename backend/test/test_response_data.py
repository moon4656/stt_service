import requests
import os
import time

# 테스트용 작은 오디오 파일 생성 (빈 파일)
test_file = "test_audio.wav"
with open(test_file, "wb") as f:
    f.write(b"RIFF" + b"\x00" * 40)  # 최소한의 WAV 헤더

try:
    # STT 서비스에 요청 보내기
    with open(test_file, "rb") as f:
        files = {"file": ("test_audio.wav", f, "audio/wav")}
        data = {"service": "daglo", "fallback": "false"}
        
        print("STT 서비스에 요청 보내는 중...")
        response = requests.post(
            "http://localhost:8001/transcribe/",
            files=files,
            data=data,
            timeout=30
        )
        
        print(f"응답 상태 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"요청 ID: {result.get('request_id')}")
            print(f"응답 ID: {result.get('response_id')}")
            
            # 잠시 대기 후 데이터베이스 확인
            time.sleep(2)
            
except Exception as e:
    print(f"오류 발생: {str(e)}")
    
finally:
    # 테스트 파일 삭제
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"테스트 파일 {test_file} 삭제됨")