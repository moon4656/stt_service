import json
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from database import engine, TranscriptionResponse

def migrate_response_data():
    """기존 레코드들의 response_data를 채우는 마이그레이션"""
    
    # 데이터베이스 연결
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 모든 레코드 조회 (유니코드 이스케이프 문제 해결을 위해)
        records = db.query(TranscriptionResponse).all()
        
        print(f"response_data가 NULL인 레코드 수: {len(records)}")
        
        updated_count = 0
        for record in records:
            # 기존 데이터를 기반으로 response_data 생성
            response_data = {
                "transcription": record.transcribed_text or "",
                "service_used": record.service_provider or "unknown",
                "duration": record.duration or 0,
                "confidence_score": record.confidence_score or 0.0,
                "language_detected": record.language_detected or "unknown",
                "word_count": record.word_count or 0,
                "processing_time": getattr(record, 'processing_time', 0) or 0,
                "success": True,
                "created_at": record.created_at.isoformat() if record.created_at else None
            }
            
            # JSON 문자열로 변환하여 저장
            record.response_data = json.dumps(response_data, ensure_ascii=False)
            updated_count += 1
            
            if updated_count % 5 == 0:
                print(f"진행 상황: {updated_count}/{len(records)} 레코드 업데이트됨")
        
        # 변경사항 커밋
        db.commit()
        print(f"✅ 마이그레이션 완료: {updated_count}개 레코드의 response_data가 업데이트되었습니다.")
        
        # 결과 확인
        total_records = db.query(TranscriptionResponse).count()
        records_with_data = db.query(TranscriptionResponse).filter(
            TranscriptionResponse.response_data.isnot(None)
        ).count()
        
        print(f"전체 레코드: {total_records}")
        print(f"response_data가 있는 레코드: {records_with_data}")
        
        # 샘플 데이터 확인
        sample_record = db.query(TranscriptionResponse).filter(
            TranscriptionResponse.response_data.isnot(None)
        ).first()
        
        if sample_record:
            print(f"\n샘플 response_data (ID: {sample_record.id}):")
            print(sample_record.response_data[:200] + "..." if len(sample_record.response_data) > 200 else sample_record.response_data)
        
    except Exception as e:
        print(f"❌ 마이그레이션 중 오류 발생: {str(e)}")
        db.rollback()
        
    finally:
        db.close()

if __name__ == "__main__":
    migrate_response_data()