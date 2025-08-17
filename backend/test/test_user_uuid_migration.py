#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db, User, TranscriptionRequest, APIUsageLog, LoginLog, APIToken
from sqlalchemy import text

def test_user_uuid_migration():
    """user_id에서 user_uuid로 마이그레이션 테스트"""
    print("=== user_id -> user_uuid 마이그레이션 테스트 ===")
    db = next(get_db())
    
    try:
        # 1. 모든 테이블에서 user_uuid 컬럼 존재 확인
        print("\n1. 테이블별 user_uuid 컬럼 확인:")
        
        # TranscriptionRequest 테이블
        transcription_requests = db.query(TranscriptionRequest).limit(5).all()
        print(f"   - transcription_requests: {len(transcription_requests)}개 레코드")
        for req in transcription_requests:
            print(f"     ID: {req.id}, user_uuid: {req.user_uuid}, filename: {req.filename}")
        
        # APIUsageLog 테이블
        api_usage_logs = db.query(APIUsageLog).limit(5).all()
        print(f"   - api_usage_logs: {len(api_usage_logs)}개 레코드")
        for log in api_usage_logs:
            print(f"     ID: {log.id}, user_uuid: {log.user_uuid}, endpoint: {log.endpoint}")
        
        # LoginLog 테이블
        login_logs = db.query(LoginLog).limit(5).all()
        print(f"   - login_logs: {len(login_logs)}개 레코드")
        for log in login_logs:
            print(f"     ID: {log.id}, user_uuid: {log.user_uuid}, success: {log.success}")
        
        # APIToken 테이블
        api_tokens = db.query(APIToken).limit(5).all()
        print(f"   - api_tokens: {len(api_tokens)}개 레코드")
        for token in api_tokens:
            print(f"     ID: {token.id}, user_uuid: {token.user_uuid}, token_name: {token.token_name}")
        
        # 2. user_uuid와 users 테이블의 매핑 확인
        print("\n2. user_uuid 매핑 검증:")
        
        # users 테이블의 모든 user_uuid 가져오기
        users = db.query(User).all()
        valid_uuids = {user.user_uuid for user in users}
        print(f"   - 유효한 user_uuid 개수: {len(valid_uuids)}")
        
        # 각 테이블의 user_uuid가 users 테이블에 존재하는지 확인
        tables_to_check = [
            ('transcription_requests', TranscriptionRequest),
            ('api_usage_logs', APIUsageLog),
            ('login_logs', LoginLog),
            ('api_tokens', APIToken)
        ]
        
        for table_name, model_class in tables_to_check:
            records = db.query(model_class).all()
            invalid_count = 0
            for record in records:
                if record.user_uuid and record.user_uuid not in valid_uuids:
                    invalid_count += 1
                    print(f"     ❌ {table_name}: 잘못된 user_uuid {record.user_uuid} (ID: {record.id})")
            
            if invalid_count == 0:
                print(f"     ✅ {table_name}: 모든 user_uuid가 유효함 ({len(records)}개 레코드)")
            else:
                print(f"     ❌ {table_name}: {invalid_count}개의 잘못된 user_uuid 발견")
        
        # 3. 기존 user_id 컬럼이 제거되었는지 확인
        print("\n3. 기존 user_id 컬럼 제거 확인:")
        
        tables_to_check_columns = [
            'transcription_requests',
            'api_usage_logs', 
            'login_logs',
            'api_tokens'
        ]
        
        for table_name in tables_to_check_columns:
            try:
                result = db.execute(text(f"SELECT user_id FROM {table_name} LIMIT 1"))
                print(f"     ❌ {table_name}: user_id 컬럼이 아직 존재함")
            except Exception as e:
                if "does not exist" in str(e) or "column" in str(e).lower():
                    print(f"     ✅ {table_name}: user_id 컬럼이 성공적으로 제거됨")
                else:
                    print(f"     ⚠️ {table_name}: 확인 중 오류 - {e}")
        
        print("\n=== 마이그레이션 테스트 완료 ===")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_user_uuid_migration()