import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

def check_database_schema():
    """PostgreSQL 데이터베이스 스키마 정보를 확인합니다."""
    database_url = os.getenv('DATABASE_URL')
    print(f"데이터베이스 URL: {database_url}")
    print("=" * 80)
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # 1. 테이블 목록 조회
            print("📋 PostgreSQL 테이블 목록:")
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = conn.execute(tables_query).fetchall()
            for table in tables:
                print(f"  - {table[0]}")
            print()
            
            # 2. 각 테이블의 컬럼 정보 조회
            for table in tables:
                table_name = table[0]
                print(f"🔍 테이블: {table_name}")
                
                columns_query = text("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name
                    ORDER BY ordinal_position;
                """)
                
                columns = conn.execute(columns_query, {"table_name": table_name}).fetchall()
                
                for col in columns:
                    col_name, data_type, is_nullable, default_val, max_length = col
                    nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
                    length_info = f"({max_length})" if max_length else ""
                    default_info = f" DEFAULT {default_val}" if default_val else ""
                    
                    print(f"    {col_name:<25} {data_type}{length_info:<15} {nullable:<10}{default_info}")
                
                # 테이블 레코드 수 확인
                count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                count = conn.execute(count_query).scalar()
                print(f"    📊 레코드 수: {count}")
                print()
                
    except Exception as e:
        print(f"❌ 데이터베이스 연결 오류: {e}")
        print(f"오류 타입: {type(e).__name__}")

if __name__ == "__main__":
    check_database_schema()