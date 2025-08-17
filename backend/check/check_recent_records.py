import sqlite3
from datetime import datetime

def check_recent_records():
    """최근 레코드들을 자세히 확인"""
    conn = sqlite3.connect('stt_service.db')
    cursor = conn.cursor()
    
    print("📊 최근 10개 레코드 상세 정보")
    print("=" * 80)
    
    # 최근 10개 레코드 조회
    cursor.execute("""
        SELECT id, filename, status, transcribed_text, response_rid, 
               created_at, response_data
        FROM transcription_requests 
        ORDER BY id DESC 
        LIMIT 10
    """)
    
    records = cursor.fetchall()
    
    for record in records:
        id, filename, status, text, response_rid, created_at, response_data = record
        print(f"\n🔍 레코드 ID: {id}")
        print(f"   파일명: {filename}")
        print(f"   상태: {status}")
        print(f"   텍스트: '{text[:50]}...' (길이: {len(text) if text else 0})")
        print(f"   Response RID: {response_rid}")
        print(f"   생성시간: {created_at}")
        
        # response_data에서 transcript_id 확인
        if response_data:
            import json
            try:
                data = json.loads(response_data)
                transcript_id = data.get('transcript_id')
                print(f"   Response Data의 transcript_id: {transcript_id}")
                
                # transcript_id가 있는데 response_rid가 None인 경우 표시
                if transcript_id and not response_rid:
                    print(f"   ⚠️ transcript_id는 있지만 response_rid가 None!")
            except:
                print(f"   Response Data 파싱 실패")
        else:
            print(f"   Response Data: None")
    
    conn.close()

if __name__ == "__main__":
    check_recent_records()