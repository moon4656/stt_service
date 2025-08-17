from database import get_db, TranscriptionResponse
from sqlalchemy.orm import Session

def check_latest_record():
    """최근 레코드 확인"""
    db = next(get_db())
    result = db.query(TranscriptionResponse).order_by(TranscriptionResponse.id.desc()).first()
    
    if result:
        print(f"최근 레코드 정보:")
        print(f"  - ID: {result.id}")
        print(f"  - Request ID: {result.request_id}")
        print(f"  - Transcribed Text: '{result.transcribed_text}' (길이: {len(result.transcribed_text) if result.transcribed_text else 0})")
        print(f"  - Summary Text: '{result.summary_text}' (길이: {len(result.summary_text) if result.summary_text else 0})")
        print(f"  - Service Provider: '{result.service_provider}'")
        print(f"  - Created At: {result.created_at}")
        
        # 수정 전후 비교
        if result.transcribed_text and result.transcribed_text.strip():
            print("\n🎉 transcribed_text가 올바르게 저장되었습니다!")
        else:
            print("\n⚠️ transcribed_text가 비어있습니다.")
            
        if result.service_provider and result.service_provider.strip():
            print("🎉 service_provider가 올바르게 저장되었습니다!")
        else:
            print("⚠️ service_provider가 비어있습니다.")
    else:
        print("❌ 레코드를 찾을 수 없습니다.")
    
    db.close()

if __name__ == "__main__":
    check_latest_record()