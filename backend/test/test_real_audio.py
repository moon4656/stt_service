import requests
import time
from database import engine
from sqlalchemy import text

def test_duration_calculation():
    print("=== 실제 오디오 파일로 duration 계산 테스트 ===")
    
    # 테스트 전 최신 ID 확인
    with engine.connect() as conn:
        result = conn.execute(text('SELECT MAX(id) FROM transcription_responses'))
        before_id = result.scalar() or 0
    
    print(f"테스트 전 최신 ID: {before_id}")
    
    # 실제 오디오 파일로 요청
    url = "http://localhost:8001/transcribe/"
    
    try:
        with open("real_test_audio.wav", "rb") as f:
            files = {"file": ("real_test_audio.wav", f, "audio/wav")}
            data = {
                "use_summary": "true",
                "stt_service": "daglo",
                "use_fallback": "true"
            }
            
            print("📤 실제 오디오 파일로 요청 전송 중...")
            response = requests.post(url, files=files, data=data, timeout=120)
            
            if response.status_code == 200:
                print("✅ 요청 성공!")
                result_data = response.json()
                print(f"응답 데이터: {result_data}")
            else:
                print(f"❌ 요청 실패: {response.status_code}")
                print(f"응답: {response.text}")
                
    except Exception as e:
        print(f"❌ 요청 중 오류: {e}")
    
    # 잠시 대기 후 데이터베이스 확인
    time.sleep(2)
    
    print("\n=== 데이터베이스 확인 ===")
    with engine.connect() as conn:
        result = conn.execute(text('''
            SELECT id, audio_duration_minutes, tokens_used, duration, service_provider, created_at 
            FROM transcription_responses 
            WHERE id > :before_id
            ORDER BY id DESC 
            LIMIT 1
        '''), {"before_id": before_id})
        
        row = result.fetchone()
        if row:
            print(f"새로운 레코드 발견:")
            print(f"  ID: {row[0]}")
            print(f"  audio_duration_minutes: {row[1]}")
            print(f"  tokens_used: {row[2]}")
            print(f"  duration: {row[3]}")
            print(f"  service_provider: {row[4]}")
            print(f"  created_at: {row[5]}")
            
            # 계산 검증
            if row[1] > 0 and row[2] > 0:
                print(f"\n✅ 계산 성공! audio_duration_minutes와 tokens_used가 0보다 큽니다.")
                if abs(row[1] - row[2]) < 0.01:  # 거의 같은 값인지 확인
                    print(f"✅ tokens_used가 audio_duration_minutes와 일치합니다 (1분당 1점).")
                else:
                    print(f"⚠️ tokens_used({row[2]})가 audio_duration_minutes({row[1]})와 다릅니다.")
            else:
                print(f"❌ 계산 실패: audio_duration_minutes 또는 tokens_used가 0입니다.")
        else:
            print("❌ 새로운 레코드가 생성되지 않았습니다.")

if __name__ == "__main__":
    test_duration_calculation()