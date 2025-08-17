#!/usr/bin/env python3
"""
데이터베이스 구조 및 데이터 확인 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db
from sqlalchemy import text

def check_database_structure():
    """데이터베이스 구조 확인"""
    try:
        db = next(get_db())
        
        print("=== 데이터베이스 구조 확인 ===")
        
        # transcription_requests 테이블 구조 확인
        print("\n📊 transcription_requests 테이블 구조:")
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'transcription_requests'
            ORDER BY ordinal_position
        """))
        
        for row in result:
            print(f"   {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]})")
        
        # transcription_responses 테이블 구조 확인
        print("\n📊 transcription_responses 테이블 구조:")
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'transcription_responses'
            ORDER BY ordinal_position
        """))
        
        for row in result:
            print(f"   {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]})")
        
        # 기본 키 확인
        print("\n🔑 transcription_requests 기본 키:")
        result = db.execute(text("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = 'transcription_requests'::regclass AND i.indisprimary
        """))
        
        for row in result:
            print(f"   Primary Key: {row[0]}")
        
        # 데이터 샘플 확인
        print("\n📋 transcription_requests 데이터 샘플:")
        result = db.execute(text("""
            SELECT request_id, filename, status, created_at
            FROM transcription_requests 
            ORDER BY created_at DESC 
            LIMIT 5
        """))
        
        for row in result:
            print(f"   ID: {row[0]}, 파일: {row[1]}, 상태: {row[2]}, 생성일: {row[3]}")
        
        print("\n📋 transcription_responses 데이터 샘플:")
        result = db.execute(text("""
            SELECT id, request_id, service_provider, created_at
            FROM transcription_responses 
            ORDER BY created_at DESC 
            LIMIT 5
        """))
        
        for row in result:
            print(f"   ID: {row[0]}, Request ID: {row[1]}, 서비스: {row[2]}, 생성일: {row[3]}")
        
        db.close()
        print("\n✅ 데이터베이스 구조 확인 완료")
        
    except Exception as e:
        print(f"❌ 데이터베이스 확인 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database_structure()