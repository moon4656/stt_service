import requests
import json
from database import get_db
from sqlalchemy import text
import os

def test_real_voice_files():
    """실제 음성 파일로 STT 테스트"""
    
    # 테스트할 실제 음성 파일들
    audio_files = [
        "english_voice_test.wav",
        "korean_voice_test.wav", 
        "simple_english_test.wav"
    ]
    
    for audio_file in audio_files:
        if not os.path.exists(audio_file):
            print(f"❌ 파일을 찾을 수 없음: {audio_file}")
            continue
            
        print(f"\n🎤 실제 음성 테스트: {audio_file}")
        print("=" * 60)
        
        try:
            # 파일 크기 확인
            file_size = os.path.getsize(audio_file)
            print(f"📁 파일 크기: {file_size} bytes")
            
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
                print(f"   처리 시간: {result.get('processing_time', 0)}초")
                
                # 데이터베이스에서 해당 요청 확인
                request_id = result.get('request_id')
                if request_id:
                    check_database_record(request_id, audio_file)
                else:
                    print(f"⚠️ request_id가 반환되지 않음")
                    
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
    """데이터베이스 레코드 확인 및 transcript_id 검증"""
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
            print(f"\n📊 데이터베이스 레코드 검증 (ID: {request_id}):")
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
                            print(f"   ✅ SUCCESS: transcript_id와 response_rid가 일치함!")
                        else:
                            print(f"   ❌ MISMATCH: transcript_id({transcript_id})와 response_rid({record[2]})가 다름!")
                    elif transcript_id and not record[2]:
                        print(f"   ❌ ISSUE: transcript_id는 있지만 response_rid가 None!")
                        print(f"   🔍 이것이 우리가 찾던 문제입니다!")
                    elif not transcript_id and record[2]:
                        print(f"   ❌ ISSUE: response_rid는 있지만 transcript_id가 None!")
                    else:
                        print(f"   ❌ ISSUE: transcript_id와 response_rid 모두 None!")
                        
                    # 추가 정보 출력
                    print(f"   📋 Response Data 키들: {list(response_data.keys())}")
                    print(f"   🔧 서비스명: {response_data.get('service_name', 'N/A')}")
                    print(f"   ⏱️ 처리시간: {response_data.get('processing_time', 'N/A')}초")
                    
                except Exception as e:
                    print(f"   ❌ Response Data 파싱 실패: {e}")
            else:
                print(f"   ❌ Response Data 없음")
        else:
            print(f"\n❌ 데이터베이스에서 레코드를 찾을 수 없음 (ID: {request_id})")
            
        db.close()
        
    except Exception as e:
        print(f"❌ 데이터베이스 확인 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🎤 실제 음성 파일로 STT 및 transcript_id 저장 테스트")
    print("=" * 70)
    test_real_voice_files()
    
    print("\n📊 테스트 완료! 결과를 확인하세요.")