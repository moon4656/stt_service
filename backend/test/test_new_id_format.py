import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import generate_request_id, get_db
from db_service import TranscriptionService
from datetime import datetime

def test_new_id_generation():
    """새로운 ID 생성 형태 테스트"""
    print("🔍 새로운 ID 생성 테스트")
    
    # 1. generate_request_id 함수 직접 테스트
    print("\n1. generate_request_id() 함수 테스트:")
    for i in range(3):
        new_id = generate_request_id()
        print(f"   생성된 ID {i+1}: {new_id}")
        print(f"   길이: {len(new_id)}")
        
        # ID 형태 검증
        parts = new_id.split('-')
        if len(parts) == 3:
            date_part = parts[0]
            time_part = parts[1]
            uuid_part = parts[2]
            
            print(f"   날짜 부분: {date_part} (길이: {len(date_part)})")
            print(f"   시간 부분: {time_part} (길이: {len(time_part)})")
            print(f"   UUID 부분: {uuid_part} (길이: {len(uuid_part)})")
            
            # 형태 검증
            if len(date_part) == 8 and len(time_part) == 6 and len(uuid_part) == 8:
                print("   ✅ 올바른 형태입니다!")
            else:
                print("   ❌ 잘못된 형태입니다!")
        else:
            print("   ❌ 잘못된 형태입니다! (구분자 개수가 맞지 않음)")
        print()
    
    # 2. 실제 DB 서비스를 통한 요청 생성 테스트
    print("\n2. TranscriptionService를 통한 실제 요청 생성 테스트:")
    try:
        # DB 세션 생성
        db = next(get_db())
        service = TranscriptionService(db)
        
        # 테스트 요청 생성
        request_record = service.create_request(
            filename="test_new_id_format.wav",
            file_size=1024,
            service_requested="assemblyai"
        )
        
        print(f"   생성된 요청 ID: {request_record.request_id}")
        print(f"   파일명: {request_record.filename}")
        print(f"   파일 크기: {request_record.file_size}")
        print(f"   상태: {request_record.status}")
        print(f"   생성시간: {request_record.created_at}")
        
        # ID 형태 검증
        parts = request_record.request_id.split('-')
        if len(parts) == 3:
            print("   ✅ 새로운 ID 형태가 올바르게 적용되었습니다!")
        else:
            print("   ❌ ID 형태가 올바르지 않습니다!")
            
        # DB 세션 정리
        db.close()
            
    except Exception as e:
        print(f"   ❌ 오류 발생: {e}")

if __name__ == "__main__":
    test_new_id_generation()