#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
파일 저장 기능 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from file_storage import save_uploaded_file, get_stored_file_path, file_storage_manager
import uuid

def test_file_storage():
    """
    파일 저장 기능을 테스트합니다.
    """
    print("🧪 파일 저장 기능 테스트 시작")
    
    # 테스트 데이터 준비
    user_uuid = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    filename = "test_audio.wav"
    test_content = b"test audio content for file storage test"
    
    try:
        # 파일 저장 테스트
        print(f"📁 테스트 파일 저장 중...")
        print(f"   사용자 UUID: {user_uuid}")
        print(f"   요청 ID: {request_id}")
        print(f"   파일명: {filename}")
        
        stored_path = save_uploaded_file(
            user_uuid=user_uuid,
            request_id=request_id,
            filename=filename,
            file_content=test_content
        )
        
        print(f"✅ 파일 저장 성공: {stored_path}")
        
        # 파일 존재 확인
        if os.path.exists(stored_path):
            print(f"✅ 저장된 파일 확인됨")
            
            # 파일 내용 확인
            with open(stored_path, 'rb') as f:
                saved_content = f.read()
                if saved_content == test_content:
                    print(f"✅ 파일 내용 일치 확인")
                else:
                    print(f"❌ 파일 내용 불일치")
        else:
            print(f"❌ 저장된 파일을 찾을 수 없음")
            
        # 경로 조회 테스트
        retrieved_path = get_stored_file_path(user_uuid, request_id, filename)
        if retrieved_path == stored_path:
            print(f"✅ 파일 경로 조회 성공")
        else:
            print(f"❌ 파일 경로 조회 실패")
            
        # 저장소 정보 조회
        storage_info = file_storage_manager.get_user_storage_info(user_uuid)
        print(f"📊 사용자 저장소 정보: {storage_info}")
        
        print(f"🎉 파일 저장 기능 테스트 완료")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_file_storage()