import requests
import json
from database import get_db
from sqlalchemy import text

def test_voice_audio():
    """음성 유사 오디오로 STT 테스트"""
    
    # 테스트할 오디오 파일들
    audio_files = [
        "voice_like_test.wav",
        "speech_pattern_test.wav"
    ]
    
    for audio_file in audio_files:
        print(f"\n🎤 테스트 중: {audio_file}")
        print("=" * 50)
        
        try:
            # STT API 호출
            with open(audio_file, 'rb') as f:
                files = {'file': (audio_file, f, 'audio/wav')}
                response = requests.post(
                    'http://localhost:8001/transcribe/',
                    files=files,
                    params={
                        'service': 'assemblyai',
                        'fallback': True,
                        'summarization': False
                    }
                )
            
            print(f"📊 응답 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ STT 처리 성공!")
                print(f"   변환된 텍스트: '{result.get('transcribed_text', '')}'")  
                print(f"   신뢰도: {result.get('confidence_score', 0)}")
                print(f"   언어: {result.get('language_detected', '')}")
                print(f"   서비스: {result.get('service_provider', '')}")
                print(f"   요청 ID: {result.get('request_id', '')}")
                
                # 데이터베이스에서 해당 요청 확인
                request_id = result.get('request_id')
                if request_id:
                    check_database_record(request_id, audio_file)
                    
            else:
                print(f"❌ STT 처리 실패: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"오류 내용: {error_detail}")
                except:
                    print(f"오류 내용: {response.text}")
                    
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()

def check_database_record(request_id, filename):
    """데이터베이스 레코드 확인"""
    try:
        db = next(get_db())
        
        # 요청 레코드 확인
        result = db.execute(text("""
            SELECT tr.id, tr.filename, tr.response_rid, tr.status, tr.created_at,
                   tres.transcribed_text, tres.service_provider, tres.response_data
            FROM transcription_requests tr
            LEFT JOIN transcription_responses tres ON tr.id = tres.request_id
            WHERE tr.id = :request_id
        """), {"request_id": request_id})
        
        record = result.fetchone()
        if record:
            print(f"\n📊 데이터베이스 레코드 (ID: {request_id}):")
            print(f"   파일명: {record[1]}")
            print(f"   Response RID: {record[2]}")
            print(f"   상태: {record[3]}")
            print(f"   변환 텍스트: '{record[5] or ''}'")
            print(f"   서비스 제공업체: {record[6]}")
            
            # response_data에서 transcript_id 확인
            if record[7]:
                try:
                    response_data = json.loads(record[7])
                    transcript_id = response_data.get('transcript_id')
                    print(f"   Response Data의 transcript_id: {transcript_id}")
                    
                    # transcript_id와 response_rid 비교
                    if transcript_id and record[2]:
                        if transcript_id == record[2]:
                            print(f"   ✅ transcript_id와 response_rid가 일치함")
                        else:
                            print(f"   ⚠️ transcript_id와 response_rid가 다름!")
                    elif transcript_id and not record[2]:
                        print(f"   ❌ transcript_id는 있지만 response_rid가 None!")
                    elif not transcript_id and record[2]:
                        print(f"   ❌ response_rid는 있지만 transcript_id가 None!")
                    else:
                        print(f"   ❌ transcript_id와 response_rid 모두 None!")
                        
                except Exception as e:
                    print(f"   Response Data 파싱 실패: {e}")
            else:
                print(f"   Response Data 없음")
        else:
            print(f"\n❌ 데이터베이스에서 레코드를 찾을 수 없음 (ID: {request_id})")
            
        db.close()
        
    except Exception as e:
        print(f"❌ 데이터베이스 확인 실패: {e}")

if __name__ == "__main__":
    test_voice_audio()