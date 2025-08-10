import requests
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

DAGLO_API_KEY = os.getenv('DAGLO_API_KEY')
DAGLO_API_URL = "https://apis.daglo.ai/stt/v1/async/transcripts"

def check_daglo_result(rid):
    """Daglo API에서 특정 RID의 결과를 조회"""
    
    headers = {
        "Authorization": f"Bearer {DAGLO_API_KEY}"
    }
    
    result_url = f"{DAGLO_API_URL}/{rid}"
    
    try:
        print(f"Checking Daglo API result for RID: {rid}")
        print(f"URL: {result_url}")
        
        response = requests.get(result_url, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result_data = response.json()
            status = result_data.get('status')
            print(f"\nTranscription Status: {status}")
            
            if status == 'transcribed':
                print("✅ Transcription completed!")
                if 'sttResults' in result_data:
                    print(f"Transcription Text: {result_data['sttResults']}")
            elif status == 'processing':
                print("⏳ Still processing...")
            elif status == 'failed':
                print("❌ Transcription failed")
                if 'error' in result_data:
                    print(f"Error: {result_data['error']}")
            else:
                print(f"Unknown status: {status}")
        else:
            print(f"❌ API call failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error occurred: {e}")

if __name__ == "__main__":
    # 데이터베이스에서 가장 최근 RID 사용
    rid = "VkbrX4LOBPIYuvdOPJnKX"  # 로그에서 확인된 최신 RID
    check_daglo_result(rid)