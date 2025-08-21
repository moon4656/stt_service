#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
테이블 주석 검증 스크립트

데이터베이스의 모든 테이블에 한국어 주석이 올바르게 추가되었는지 확인합니다.
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

def verify_table_comments():
    """테이블 주석 검증"""
    try:
        # 데이터베이스 연결
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
            return False
            
        engine = create_engine(DATABASE_URL)
        
        # 테이블 주석 조회 쿼리
        query = text("""
            SELECT 
                schemaname,
                tablename,
                obj_description(c.oid) as table_comment
            FROM pg_tables t
            JOIN pg_class c ON c.relname = t.tablename
            JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.schemaname
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        
        with engine.connect() as connection:
            result = connection.execute(query)
            tables = result.fetchall()
            
            print("\n🔍 테이블 주석 검증 결과:")
            print("=" * 80)
            
            success_count = 0
            total_count = 0
            
            for row in tables:
                schema, table_name, comment = row
                total_count += 1
                
                if comment and comment.strip():
                    print(f"✅ {table_name:<25} | {comment}")
                    success_count += 1
                else:
                    print(f"❌ {table_name:<25} | 주석 없음")
            
            print("=" * 80)
            print(f"📊 검증 결과: {success_count}/{total_count} 테이블에 주석이 설정되어 있습니다.")
            
            if success_count == total_count:
                print("🎉 모든 테이블에 한국어 주석이 성공적으로 추가되었습니다!")
                return True
            else:
                print(f"⚠️  {total_count - success_count}개 테이블에 주석이 누락되었습니다.")
                return False
                
    except Exception as e:
        print(f"❌ 테이블 주석 검증 중 오류 발생: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 테이블 주석 검증을 시작합니다...")
    success = verify_table_comments()
    
    if success:
        print("\n✅ 테이블 주석 검증이 성공적으로 완료되었습니다.")
    else:
        print("\n❌ 테이블 주석 검증에서 문제가 발견되었습니다.")