#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database import get_db, APIToken
from sqlalchemy import inspect

def check_api_tokens_table():
    """api_tokens 테이블 구조 확인"""
    print("=== api_tokens 테이블 구조 확인 ===")
    
    db = next(get_db())
    inspector = inspect(db.bind)
    
    # 테이블 존재 확인
    tables = inspector.get_table_names()
    print(f"데이터베이스 테이블 목록: {tables}")
    
    if 'api_tokens' in tables:
        print("\napi_tokens 테이블이 존재합니다.")
        
        # 컬럼 정보 확인
        columns = inspector.get_columns('api_tokens')
        print("\napi_tokens 테이블 컬럼:")
        for col in columns:
            print(f"- {col['name']}: {col['type']}")
        
        # 실제 데이터 확인
        tokens = db.query(APIToken).all()
        print(f"\n현재 저장된 토큰 개수: {len(tokens)}")
        
        if tokens:
            print("\n저장된 토큰 정보:")
            for token in tokens[:5]:  # 최대 5개만 표시
                print(f"- ID: {token.id}, user_uuid: {token.user_uuid}, token_name: {token.token_name}")
    else:
        print("\napi_tokens 테이블이 존재하지 않습니다.")
    
    db.close()

if __name__ == "__main__":
    check_api_tokens_table()