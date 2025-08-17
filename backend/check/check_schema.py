#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db
from sqlalchemy import text, inspect

def check_transcription_responses_schema():
    """transcription_responses 테이블의 실제 스키마 확인"""
    print("=== transcription_responses 테이블 스키마 확인 ===")
    db = next(get_db())
    
    try:
        # SQLAlchemy Inspector를 사용해서 테이블 구조 확인
        inspector = inspect(db.bind)
        
        # transcription_responses 테이블의 컬럼 정보 가져오기
        columns = inspector.get_columns('transcription_responses')
        
        print("\n📋 transcription_responses 테이블 컬럼 목록:")
        for i, column in enumerate(columns, 1):
            print(f"{i:2d}. {column['name']:25} | {str(column['type']):20} | nullable: {column['nullable']}")
        
        # user_uuid 컬럼이 있는지 확인
        column_names = [col['name'] for col in columns]
        if 'user_uuid' in column_names:
            print("\n✅ user_uuid 컬럼이 존재합니다.")
        else:
            print("\n❌ user_uuid 컬럼이 존재하지 않습니다.")
        
        # transcription_requests 테이블도 확인
        print("\n=== transcription_requests 테이블 스키마 확인 ===")
        req_columns = inspector.get_columns('transcription_requests')
        
        print("\n📋 transcription_requests 테이블 컬럼 목록:")
        for i, column in enumerate(req_columns, 1):
            print(f"{i:2d}. {column['name']:25} | {str(column['type']):20} | nullable: {column['nullable']}")
        
        req_column_names = [col['name'] for col in req_columns]
        if 'user_uuid' in req_column_names:
            print("\n✅ transcription_requests에 user_uuid 컬럼이 존재합니다.")
        else:
            print("\n❌ transcription_requests에 user_uuid 컬럼이 존재하지 않습니다.")
        
    except Exception as e:
        print(f"❌ 스키마 확인 중 오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_transcription_responses_schema()