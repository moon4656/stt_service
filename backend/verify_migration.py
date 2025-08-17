#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db
from sqlalchemy import text

def verify_migration():
    """마이그레이션 결과 검증"""
    print("=== user_id -> user_uuid 마이그레이션 검증 ===")
    db = next(get_db())
    
    try:
        # 각 테이블의 컬럼 정보 확인
        tables = ['transcription_requests', 'api_usage_logs', 'login_logs', 'api_tokens']
        
        for table_name in tables:
            print(f"\n🔍 테이블: {table_name}")
            
            # 컬럼 정보 조회
            result = db.execute(text(f"""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}' 
                AND column_name IN ('user_id', 'user_uuid')
                ORDER BY column_name
            """))
            
            columns = result.fetchall()
            
            if not columns:
                print("   ❌ user_id 또는 user_uuid 컬럼을 찾을 수 없음")
                continue
            
            has_user_id = False
            has_user_uuid = False
            
            for column in columns:
                column_name, data_type, is_nullable = column
                if column_name == 'user_id':
                    has_user_id = True
                    print(f"   ❌ user_id 컬럼이 아직 존재: {data_type}, nullable: {is_nullable}")
                elif column_name == 'user_uuid':
                    has_user_uuid = True
                    print(f"   ✅ user_uuid 컬럼 존재: {data_type}, nullable: {is_nullable}")
            
            if not has_user_id and has_user_uuid:
                print(f"   ✅ {table_name}: 마이그레이션 성공 (user_id 제거, user_uuid 추가)")
            elif has_user_id and has_user_uuid:
                print(f"   ⚠️ {table_name}: 부분 마이그레이션 (둘 다 존재)")
            elif has_user_id and not has_user_uuid:
                print(f"   ❌ {table_name}: 마이그레이션 실패 (user_id만 존재)")
            else:
                print(f"   ❌ {table_name}: 예상치 못한 상태")
        
        # 데이터 매핑 확인
        print("\n📊 데이터 매핑 확인:")
        for table_name in tables:
            try:
                result = db.execute(text(f"""
                    SELECT COUNT(*) as total_count,
                           COUNT(user_uuid) as uuid_count,
                           COUNT(CASE WHEN user_uuid IS NOT NULL THEN 1 END) as non_null_uuid_count
                    FROM {table_name}
                """))
                
                row = result.fetchone()
                total, uuid_count, non_null_uuid = row
                
                print(f"   {table_name}: 총 {total}개, user_uuid 있음 {uuid_count}개, NULL 아님 {non_null_uuid}개")
                
            except Exception as e:
                print(f"   {table_name}: 데이터 확인 실패 - {e}")
        
        print("\n=== 검증 완료 ===")
        
    except Exception as e:
        print(f"❌ 검증 중 오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_migration()