import requests
import json
import time
from database import get_db
from sqlalchemy import text

def test_stt_and_check_transcript_id():
    """STT 처리 후 transcript_id가 제대로 저장되는지 테스트"""
    
    # 1. 테스트 오디오 파일 생성 (간단한 텍스트를 음성으로)
    test_text = "안녕하세요. 이것은 테스트입니다."
    
    # 2. STT API 호출
    url = "http://localhost:8001/transcribe/"
    
    # 간단한 테스트용 오디오 파일 생성
    try:
        from create_test_audio import create_test_audio
        audio_file_path = "test_transcript_id.wav"
        create_test_audio(audio_file_path, duration_seconds=5)
        print(f"✅ 테스트 오디오 파일 생성: {audio_file_path}")
        
        # STT 요청
        with open(audio_file_path, 'rb') as f:
            files = {'file': ('test_transcript_id.wav', f, 'audio/wav')}
            params = {
                'service': 'assemblyai',
                'fallback': 'true',
                'summarization': 'false'
            }
            
            print("🚀 STT 처리 시작...")
            response = requests.post(url, files=files, params=params)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ STT 처리 성공")
                print(f"📝 변환된 텍스트: {result.get('transcribed_text', '')[:100]}...")
                print(f"🔍 Request ID: {result.get('request_id')}")
                print(f"🔍 Response RID: {result.get('response_rid')}")
                
                # 데이터베이스에서 확인
                request_id = result.get('request_id')
                if request_id:
                    check_database_record(request_id)
                    
            else:
                print(f"❌ STT 처리 실패: {response.status_code}")
                print(f"오류 내용: {response.text}")
                
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def check_database_record(request_id):
    """데이터베이스에서 해당 요청의 response_rid 확인"""
    try:
        db = next(get_db())
        
        # transcription_requests 테이블에서 확인
        result = db.execute(text("""
            SELECT id, filename, response_rid, status 
            FROM transcription_requests 
            WHERE id = :request_id
        """), {"request_id": request_id})
        
        record = result.fetchone()
        if record:
            print(f"\n📊 데이터베이스 레코드:")
            print(f"   ID: {record[0]}")
            print(f"   파일명: {record[1]}")
            print(f"   Response RID: {record[2]}")
            print(f"   상태: {record[3]}")
            
            if record[2]:  # response_rid가 있으면
                print(f"✅ Response RID가 성공적으로 저장됨: {record[2]}")
            else:
                print(f"❌ Response RID가 저장되지 않음")
        else:
            print(f"❌ 데이터베이스에서 레코드를 찾을 수 없음: {request_id}")
            
        db.close()
        
    except Exception as e:
        print(f"❌ 데이터베이스 확인 실패: {e}")

if __name__ == "__main__":
    test_stt_and_check_transcript_id()