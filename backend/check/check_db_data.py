import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db
from sqlalchemy import text
from datetime import datetime

def check_database_data():
    try:
        db = next(get_db())
        
        # transcription_requests 테이블 확인
        print("=== transcription_requests 테이블 ====")
        result = db.execute(text("SELECT COUNT(*) FROM transcription_requests"))
        count = result.scalar()
        print(f"총 레코드 수: {count}")
        
        if count > 0:
            result = db.execute(text("SELECT * FROM transcription_requests ORDER BY created_at DESC LIMIT 5"))
            records = result.fetchall()
            
            # 컬럼명 가져오기
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'transcription_requests' 
                ORDER BY ordinal_position
            """))
            columns = [row[0] for row in result.fetchall()]
            print(f"컬럼: {columns}")
            
            print("\n최근 5개 레코드:")
            for record in records:
                print(record)
        
        # transcription_responses 테이블 확인
        print("\n=== transcription_responses 테이블 ====")
        result = db.execute(text("SELECT COUNT(*) FROM transcription_responses"))
        count = result.scalar()
        print(f"총 레코드 수: {count}")
        
        if count > 0:
            result = db.execute(text("SELECT * FROM transcription_responses ORDER BY created_at DESC LIMIT 5"))
            records = result.fetchall()
            
            # 컬럼명 가져오기
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'transcription_responses' 
                ORDER BY ordinal_position
            """))
            columns = [row[0] for row in result.fetchall()]
            print(f"컬럼: {columns}")
            
            print("\n최근 5개 레코드:")
            for record in records:
                print(record)
        
        db.close()
        
    except Exception as e:
        print(f"❌ 데이터베이스 확인 중 오류 발생: {e}")
        print(f"오류 타입: {type(e).__name__}")

if __name__ == "__main__":
    check_database_data()