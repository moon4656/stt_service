from database import engine
from sqlalchemy import text

def check_response_data_column():
    conn = engine.connect()
    
    # response_data 컬럼의 상세 정보 확인
    result = conn.execute(text("""
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'transcription_responses' 
        AND column_name = 'response_data'
    """))
    
    print("response_data 컬럼 정보:")
    for row in result:
        print(f"컬럼명: {row[0]}")
        print(f"데이터 타입: {row[1]}")
        print(f"최대 길이: {row[2]}")
        print(f"NULL 허용: {row[3]}")
    
    # 전체 테이블 컬럼 확인
    result2 = conn.execute(text("""
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns 
        WHERE table_name = 'transcription_responses'
        ORDER BY ordinal_position
    """))
    
    print("\n전체 transcription_responses 테이블 컬럼:")
    for row in result2:
        print(f"{row[0]:25} | {row[1]:20} | 최대길이: {row[2]}")
    
    conn.close()

if __name__ == "__main__":
    check_response_data_column()