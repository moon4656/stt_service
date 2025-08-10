from database import engine
from sqlalchemy import text

def add_password_column():
    """users 테이블에 password_hash 컬럼 추가"""
    try:
        with engine.connect() as conn:
            # 컬럼이 이미 존재하는지 확인
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='password_hash'
            """))
            
            if result.fetchone():
                print("password_hash 컬럼이 이미 존재합니다.")
                return
            
            # 컬럼 추가
            conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
            conn.commit()
            print("password_hash 컬럼을 성공적으로 추가했습니다.")
            
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    add_password_column()