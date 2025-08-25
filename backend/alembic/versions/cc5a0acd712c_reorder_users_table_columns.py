"""reorder_users_table_columns

Revision ID: cc5a0acd712c
Revises: 5cb265589888
Create Date: 2025-08-22 15:28:54.119851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc5a0acd712c'
down_revision: Union[str, None] = '5cb265589888'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users 테이블의 컬럼 순서를 database.py에 정의된 순서대로 변경
    # PostgreSQL에서는 컬럼 순서 변경을 위해 테이블을 재생성해야 함
    
    # 1. 임시 테이블 생성 (올바른 컬럼 순서로)
    op.execute("""
        CREATE TABLE users_new (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(100) UNIQUE NOT NULL,
            user_uuid VARCHAR(36) UNIQUE NOT NULL,
            email VARCHAR(255) NOT NULL,
            name VARCHAR(100) NOT NULL,
            user_type VARCHAR(20) NOT NULL,
            phone_number VARCHAR(20),
            password_hash VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)
    
    # 2. 기존 데이터를 새 테이블로 복사 (올바른 순서로)
    op.execute("""
        INSERT INTO users_new (
            id, user_id, user_uuid, email, name, user_type, 
            phone_number, password_hash, is_active, created_at, updated_at
        )
        SELECT 
            id, user_id, user_uuid, email, name, user_type,
            phone_number, password_hash, is_active, created_at, updated_at
        FROM users
    """)
    
    # 3. 기존 테이블 삭제 (CASCADE로 외래 키도 함께 삭제)
    op.execute("DROP TABLE users CASCADE")
    
    # 4. 새 테이블을 원래 이름으로 변경
    op.execute("ALTER TABLE users_new RENAME TO users")
    
    # 5. 인덱스 재생성
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_user_id', 'users', ['user_id'])
    op.create_index('ix_users_user_uuid', 'users', ['user_uuid'])
    
    # 6. 외래 키 제약 조건 재생성 (service_tokens 테이블만)
    op.execute("""
        ALTER TABLE service_tokens 
        ADD CONSTRAINT service_tokens_user_uuid_fkey 
        FOREIGN KEY (user_uuid) REFERENCES users(user_uuid)
    """)
    
    # 7. 테이블 코멘트 추가
    op.execute("COMMENT ON TABLE users IS '사용자 정보를 관리하는 테이블'")
    
    # 8. 컬럼 코멘트 추가
    op.execute("COMMENT ON COLUMN users.id IS '사용자일련번호'")
    op.execute("COMMENT ON COLUMN users.user_id IS '사용자아이디'")
    op.execute("COMMENT ON COLUMN users.user_uuid IS '사용자고유식별자'")
    op.execute("COMMENT ON COLUMN users.email IS '이메일주소'")
    op.execute("COMMENT ON COLUMN users.name IS '사용자명'")
    op.execute("COMMENT ON COLUMN users.user_type IS '사용자유형'")
    op.execute("COMMENT ON COLUMN users.phone_number IS '전화번호'")
    op.execute("COMMENT ON COLUMN users.password_hash IS '비밀번호해시'")
    op.execute("COMMENT ON COLUMN users.is_active IS '활성화상태'")
    op.execute("COMMENT ON COLUMN users.created_at IS '생성일시'")
    op.execute("COMMENT ON COLUMN users.updated_at IS '수정일시'")


def downgrade() -> None:
    # 롤백 시에는 원래 순서로 되돌림 (필요시 구현)
    pass
