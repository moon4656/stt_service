import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 데이터베이스 연결
DATABASE_URL = "postgresql://postgres:1234@localhost:5432/stt_db"
engine = create_engine(DATABASE_URL, connect_args={"client_encoding": "utf8"})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_specific_request():
    db = SessionLocal()
    try:
        # 특정 request_id 확인
        request_id = "20250815-051218-4212540c"
        
        print(f"🔍 Request ID '{request_id}' 상세 확인:")
        
        # 1. 요청 정보 확인 (SQL 직접 사용)
        request_query = text("""
            SELECT id, request_id, status, filename, created_at, updated_at, response_rid
            FROM transcription_requests 
            WHERE request_id = :request_id
        """)
        request_result = db.execute(request_query, {"request_id": request_id}).fetchone()
        
        if request_result:
            print(f"✅ 요청 발견:")
            print(f"   - ID: {request_result[0]}")
            print(f"   - Request ID: {request_result[1]}")
            print(f"   - Status: {request_result[2]}")
            print(f"   - Filename: {request_result[3]}")
            print(f"   - Created: {request_result[4]}")
            print(f"   - Updated: {request_result[5]}")
            print(f"   - Response RID: {request_result[6]}")
        else:
            print(f"❌ 요청을 찾을 수 없습니다.")
            return
        
        # 2. 응답 정보 확인 (SQL 직접 사용)
        response_query = text("""
            SELECT id, request_id, service_provider, created_at, 
                   LEFT(transcribed_text, 100) as text_preview
            FROM transcription_responses 
            WHERE request_id = :request_id
        """)
        response_result = db.execute(response_query, {"request_id": request_id}).fetchone()
        
        if response_result:
            print(f"\n✅ 응답 발견:")
            print(f"   - ID: {response_result[0]}")
            print(f"   - Request ID: {response_result[1]}")
            print(f"   - Service Provider: {response_result[2]}")
            print(f"   - Created: {response_result[3]}")
            print(f"   - Text Preview: {response_result[4]}...")
        else:
            print(f"\n❌ 응답을 찾을 수 없습니다.")
        
        # 3. response_rid로 응답 찾기 시도
        if request_result[6]:  # response_rid가 있는 경우
            print(f"\n🔍 Response RID '{request_result[6]}'로 응답 찾기:")
            response_by_rid_query = text("""
                SELECT id, request_id, transcript_id, service_provider
                FROM transcription_responses 
                WHERE transcript_id = :transcript_id
            """)
            response_by_rid_result = db.execute(response_by_rid_query, {"transcript_id": request_result[6]}).fetchone()
            
            if response_by_rid_result:
                print(f"✅ Response RID로 응답 발견:")
                print(f"   - ID: {response_by_rid_result[0]}")
                print(f"   - Request ID: {response_by_rid_result[1]}")
                print(f"   - Transcript ID: {response_by_rid_result[2]}")
                print(f"   - Service Provider: {response_by_rid_result[3]}")
            else:
                print(f"❌ Response RID로 응답을 찾을 수 없습니다.")
        
        # 4. 최근 생성된 응답들 확인 (시간 기준)
        print(f"\n📅 최근 10분 내 생성된 응답들:")
        recent_responses_query = text("""
            SELECT id, request_id, service_provider, created_at, transcript_id
            FROM transcription_responses 
            WHERE created_at >= NOW() - INTERVAL '10 minutes'
            ORDER BY created_at DESC
        """)
        recent_responses = db.execute(recent_responses_query).fetchall()
        
        if recent_responses:
            for resp in recent_responses:
                print(f"   - ID: {resp[0]}, Request ID: {resp[1]}, Service: {resp[2]}, Created: {resp[3]}, Transcript ID: {resp[4]}")
        else:
            print("   ❌ 최근 10분 내 생성된 응답이 없습니다.")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_specific_request()