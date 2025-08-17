import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 데이터베이스 연결
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

print("🔍 transcription_requests 테이블 스키마 확인")
print("=" * 50)

# 테이블 컬럼 정보 조회
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'transcription_requests'
        ORDER BY ordinal_position;
    """))
    
    columns = result.fetchall()
    
    print("📋 컬럼 정보:")
    for col in columns:
        print(f"   {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
    
    print("\n🎵 duration 컬럼 확인:")
    duration_exists = any(col[0] == 'duration' for col in columns)
    if duration_exists:
        print("   ✅ duration 컬럼이 성공적으로 추가되었습니다!")
    else:
        print("   ❌ duration 컬럼이 없습니다.")
    
    # 샘플 데이터에서 duration 값 확인
    print("\n📊 샘플 데이터의 duration 값:")
    result = conn.execute(text("""
        SELECT request_id, filename, duration
        FROM transcription_requests 
        ORDER BY created_at DESC 
        LIMIT 5;
    """))
    
    rows = result.fetchall()
    for row in rows:
        print(f"   ID: {row[0]}, 파일: {row[1]}, 재생시간: {row[2]}초")

print("\n✅ duration 컬럼 확인 완료")