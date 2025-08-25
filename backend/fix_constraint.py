import psycopg2
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 데이터베이스 연결 정보
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/stt_service')

def fix_service_tokens_constraint():
    """service_tokens 테이블의 체크 제약 조건을 수정합니다."""
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # 기존 제약 조건 확인
            print("현재 제약 조건 확인 중...")
            result = conn.execute(text("""
                SELECT conname, pg_get_constraintdef(oid) as definition
                FROM pg_constraint 
                WHERE conrelid = 'service_tokens'::regclass
                AND contype = 'c'
            """))
            
            constraints = result.fetchall()
            print(f"발견된 체크 제약 조건: {len(constraints)}개")
            
            for constraint in constraints:
                print(f"제약 조건명: {constraint[0]}")
                print(f"정의: {constraint[1]}")
                print("---")
            
            # check_status_valid 제약 조건 삭제
            print("기존 check_status_valid 제약 조건 삭제 중...")
            conn.execute(text("""
                ALTER TABLE service_tokens 
                DROP CONSTRAINT IF EXISTS check_status_valid
            """))
            
            # 새로운 제약 조건 추가
            print("새로운 제약 조건 추가 중...")
            conn.execute(text("""
                ALTER TABLE service_tokens 
                ADD CONSTRAINT check_status_valid 
                CHECK (status IN ('active', 'expired', 'suspended'))
            """))
            
            # 변경사항 커밋
            conn.commit()
            print("✅ 제약 조건이 성공적으로 수정되었습니다.")
            
            # 수정된 제약 조건 확인
            print("\n수정된 제약 조건 확인:")
            result = conn.execute(text("""
                SELECT conname, pg_get_constraintdef(oid) as definition
                FROM pg_constraint 
                WHERE conrelid = 'service_tokens'::regclass
                AND contype = 'c'
                AND conname = 'check_status_valid'
            """))
            
            updated_constraint = result.fetchone()
            if updated_constraint:
                print(f"제약 조건명: {updated_constraint[0]}")
                print(f"정의: {updated_constraint[1]}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_service_tokens_constraint()