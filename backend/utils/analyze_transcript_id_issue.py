from database import get_db
from sqlalchemy import text
import json

def analyze_transcript_id_issue():
    """transcript_id 저장 문제 분석"""
    
    try:
        db = next(get_db())
        
        # RID가 있는 레코드와 없는 레코드 비교
        print("📊 RID가 있는 레코드와 없는 레코드 분석")
        print("=" * 50)
        
        # RID가 있는 레코드 (ID 10)
        result = db.execute(text("""
            SELECT tr.id, tr.filename, tr.response_rid, tr.status, tr.created_at,
                   tres.transcribed_text, tres.service_provider, tres.response_data
            FROM transcription_requests tr
            LEFT JOIN transcription_responses tres ON tr.id = tres.request_id
            WHERE tr.id = 10
        """))
        
        record_with_rid = result.fetchone()
        if record_with_rid:
            print("\n✅ RID가 있는 레코드 (ID 10):")
            print(f"   파일명: {record_with_rid[1]}")
            print(f"   Response RID: {record_with_rid[2]}")
            print(f"   상태: {record_with_rid[3]}")
            print(f"   변환 텍스트 길이: {len(record_with_rid[5]) if record_with_rid[5] else 0}")
            print(f"   서비스 제공업체: {record_with_rid[6]}")
            
            # response_data에서 transcript_id 확인
            if record_with_rid[7]:
                try:
                    response_data = json.loads(record_with_rid[7])
                    transcript_id = response_data.get('transcript_id')
                    print(f"   Response Data의 transcript_id: {transcript_id}")
                except:
                    print(f"   Response Data 파싱 실패")
        
        # RID가 없는 레코드 (ID 11)
        result = db.execute(text("""
            SELECT tr.id, tr.filename, tr.response_rid, tr.status, tr.created_at,
                   tres.transcribed_text, tres.service_provider, tres.response_data
            FROM transcription_requests tr
            LEFT JOIN transcription_responses tres ON tr.id = tres.request_id
            WHERE tr.id = 11
        """))
        
        record_without_rid = result.fetchone()
        if record_without_rid:
            print("\n❌ RID가 없는 레코드 (ID 11):")
            print(f"   파일명: {record_without_rid[1]}")
            print(f"   Response RID: {record_without_rid[2]}")
            print(f"   상태: {record_without_rid[3]}")
            print(f"   변환 텍스트 길이: {len(record_without_rid[5]) if record_without_rid[5] else 0}")
            print(f"   서비스 제공업체: {record_without_rid[6]}")
            
            # response_data에서 transcript_id 확인
            if record_without_rid[7]:
                try:
                    response_data = json.loads(record_without_rid[7])
                    transcript_id = response_data.get('transcript_id')
                    print(f"   Response Data의 transcript_id: {transcript_id}")
                    
                    # 전체 response_data 구조 확인
                    print(f"   Response Data 키들: {list(response_data.keys())}")
                    
                except Exception as e:
                    print(f"   Response Data 파싱 실패: {e}")
            else:
                print(f"   Response Data가 없음")
        
        # 최근 5개 레코드의 transcript_id 상태 확인
        print("\n📊 최근 5개 레코드의 transcript_id 상태:")
        print("=" * 50)
        
        result = db.execute(text("""
            SELECT tr.id, tr.filename, tr.response_rid, tr.status,
                   tres.service_provider, tres.response_data
            FROM transcription_requests tr
            LEFT JOIN transcription_responses tres ON tr.id = tres.request_id
            ORDER BY tr.created_at DESC
            LIMIT 5
        """))
        
        records = result.fetchall()
        for record in records:
            print(f"\nID {record[0]}:")
            print(f"   파일: {record[1]}")
            print(f"   RID: {record[2]}")
            print(f"   상태: {record[3]}")
            print(f"   서비스: {record[4]}")
            
            if record[5]:  # response_data가 있으면
                try:
                    response_data = json.loads(record[5])
                    transcript_id = response_data.get('transcript_id')
                    print(f"   Response Data의 transcript_id: {transcript_id}")
                    
                    # transcript_id가 있는데 RID가 None인 경우 문제 상황
                    if transcript_id and not record[2]:
                        print(f"   ⚠️ 문제: transcript_id는 있지만 RID가 저장되지 않음!")
                        
                except Exception as e:
                    print(f"   Response Data 파싱 실패: {e}")
            else:
                print(f"   Response Data 없음")
        
        db.close()
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_transcript_id_issue()