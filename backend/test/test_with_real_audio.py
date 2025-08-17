import requests
import json
import time
from database import get_db
from sqlalchemy import text
import os

def test_with_real_audio():
    """실제 오디오 파일로 STT 처리 후 transcript_id 확인"""
    
    # 실제 오디오 파일 경로 (기존에 생성된 파일 사용)
    audio_files = [
        "real_test_audio.wav",
        "meeting_audio.wav",
        "test_audio.wav"
    ]
    
    # 존재하는 오디오 파일 찾기
    audio_file_path = None
    for file in audio_files:
        if os.path.exists(file):
            audio_file_path = file
            break
    
    if not audio_file_path:
        print("❌ 테스트할 오디오 파일을 찾을 수 없습니다.")
        print("사용 가능한 파일을 생성하겠습니다...")
        
        # 더 긴 오디오 파일 생성
        from create_test_audio import create_test_audio
        audio_file_path = "longer_test_audio.wav"
        create_test_audio(audio_file_path, duration_seconds=10)
    
    print(f"✅ 테스트 오디오 파일: {audio_file_path}")
    
    # STT API 호출
    url = "http://localhost:8001/transcribe/"
    
    try:
        with open(audio_file_path, 'rb') as f:
            files = {'file': (audio_file_path, f, 'audio/wav')}
            params = {
                'service': 'assemblyai',
                'fallback': 'true',
                'summarization': 'false'
            }
            
            print("🚀 STT 처리 시작...")
            response = requests.post(url, files=files, params=params)
            
            print(f"📊 응답 상태 코드: {response.status_code}")
            
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
                
                # 실패한 경우에도 데이터베이스 확인
                print("\n📊 최근 데이터베이스 레코드 확인:")
                check_recent_records()
                
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
            SELECT id, filename, response_rid, status, created_at 
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
            print(f"   생성 시간: {record[4]}")
            
            if record[2]:  # response_rid가 있으면
                print(f"✅ Response RID가 성공적으로 저장됨: {record[2]}")
            else:
                print(f"❌ Response RID가 저장되지 않음")
        else:
            print(f"❌ 데이터베이스에서 레코드를 찾을 수 없음: {request_id}")
            
        db.close()
        
    except Exception as e:
        print(f"❌ 데이터베이스 확인 실패: {e}")

def check_recent_records():
    """최근 데이터베이스 레코드들 확인"""
    try:
        db = next(get_db())
        
        # 최근 5개 레코드 확인
        result = db.execute(text("""
            SELECT id, filename, response_rid, status, created_at 
            FROM transcription_requests 
            ORDER BY created_at DESC 
            LIMIT 5
        """))
        
        records = result.fetchall()
        if records:
            print(f"\n📊 최근 5개 레코드:")
            for record in records:
                print(f"   ID: {record[0]}, 파일: {record[1]}, RID: {record[2]}, 상태: {record[3]}")
        else:
            print(f"❌ 데이터베이스에 레코드가 없습니다.")
            
        db.close()
        
    except Exception as e:
        print(f"❌ 최근 레코드 확인 실패: {e}")

if __name__ == "__main__":
    test_with_real_audio()