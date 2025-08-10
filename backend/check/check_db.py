import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def check_postgresql_db():
    database_url = os.getenv('DATABASE_URL')
    print(f"데이터베이스 URL: {database_url}")
    
    try:
        # SQLAlchemy 엔진 생성
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # 테이블별 레코드 수 확인
            for table in ['transcription_requests', 'transcription_responses', 'api_usage_logs']:
                try:
                    result = conn.execute(text(f'SELECT COUNT(*) FROM {table}'))
                    count = result.scalar()
                    print(f'📊 {table}: {count}개 레코드')
                    
                    # 최근 레코드 확인
                    if count > 0:
                        result = conn.execute(text(f'SELECT * FROM {table} ORDER BY created_at DESC LIMIT 3'))
                        recent_records = result.fetchall()
                        print(f'   최근 레코드들:')
                        for i, record in enumerate(recent_records, 1):
                            print(f'   {i}. {record}')
                        print()
                        
                except Exception as e:
                    print(f'❌ 테이블 {table} 조회 오류: {e}')
        
        print('✅ PostgreSQL 데이터베이스 조회 완료')
        
    except Exception as e:
        print(f'❌ PostgreSQL 데이터베이스 연결 오류: {e}')
        print(f'오류 타입: {type(e).__name__}')

if __name__ == "__main__":
    print(f"현재 작업 디렉토리: {os.getcwd()}")
    print(f"시간: {datetime.now()}")
    print("=" * 50)
    check_postgresql_db()