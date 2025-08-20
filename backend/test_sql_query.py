from database import get_db
from sqlalchemy import text

def test_insert_query():
    """사용자가 제공한 INSERT 쿼리를 테스트합니다."""
    db = next(get_db())
    
    # 사용자가 제공한 쿼리 (오류가 있는 버전)
    query_with_error = """
    INSERT INTO transcription_requests AS 
    SELECT filename, file_size, file_extension, status, created_at, completed_at, 
           processing_time, error_message, user_uuid, request_id, duration, 
           service_provider, client_ip, response_rid 
    FROM public.transcription_requests_20250820_001
    """
    
    # 올바른 쿼리 (수정된 버전)
    query_corrected = """
    INSERT INTO transcription_requests 
    (filename, file_size, file_extension, status, created_at, completed_at, 
     processing_time, error_message, user_uuid, request_id, duration, 
     service_provider, client_ip, response_rid)
    SELECT filename, file_size, file_extension, status, created_at, completed_at, 
           processing_time, error_message, user_uuid, request_id, duration, 
           service_provider, client_ip, response_rid 
    FROM public.transcription_requests_20250820_001
    """
    
    print("=== 오류가 있는 쿼리 테스트 ===")
    try:
        db.execute(text(query_with_error))
        print("쿼리 실행 성공")
    except Exception as e:
        print(f"오류 발생: {e}")
        print(f"오류 타입: {type(e).__name__}")
    
    print("\n=== 수정된 쿼리 테스트 ===")
    try:
        # 먼저 롤백하여 이전 트랜잭션 정리
        db.rollback()
        result = db.execute(text(query_corrected))
        db.commit()
        print(f"쿼리 실행 성공: {result.rowcount}개 행이 삽입되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
        print(f"오류 타입: {type(e).__name__}")
        db.rollback()

if __name__ == "__main__":
    test_insert_query()