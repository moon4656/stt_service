from database import engine
from sqlalchemy import text
from db_service import TranscriptionService
from sqlalchemy.orm import sessionmaker
import json

def test_processing_time_duration():
    print("=== processing_time이 duration 컬럼에 저장되는지 테스트 ===")
    
    # 데이터베이스 세션 생성
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # TranscriptionService 인스턴스 생성
        transcription_service = TranscriptionService(db)
        
        # 테스트용 요청 생성
        request_record = transcription_service.create_request(
            filename="test_processing_time.wav",
            file_size=2048,
            service_requested="daglo",
            fallback_enabled=True
        )
        
        print(f"✅ 테스트 요청 생성 완료 - ID: {request_record.id}")
        
        # 테스트용 processing_time 값
        test_processing_time = 5.75  # 5.75초
        
        print(f"📊 테스트 processing_time: {test_processing_time}초")
        
        # 응답 저장 (duration에 processing_time 전달)
        response_record = transcription_service.create_response(
            request_id=request_record.id,
            transcription_text="안녕하세요. 이것은 processing_time 테스트입니다.",
            summary_text="테스트 요약입니다.",
            service_used="Daglo",
            processing_time=test_processing_time,
            duration=test_processing_time,  # processing_time을 duration에 저장
            success=True,
            error_message=None,
            service_provider="Daglo",
            audio_duration_minutes=0.10,
            tokens_used=0.10,
            response_data=json.dumps({"test": "data"}, ensure_ascii=False),
            confidence_score=0.92,
            language_detected="ko-KR"
        )
        
        print(f"✅ 응답 저장 완료 - ID: {response_record.id}")
        
        # 저장된 데이터 확인
        with engine.connect() as conn:
            result = conn.execute(text('''
                SELECT id, duration, service_provider, audio_duration_minutes, 
                       tokens_used, confidence_score, language_detected
                FROM transcription_responses 
                WHERE id = :response_id
            '''), {"response_id": response_record.id})
            
            row = result.fetchone()
            if row:
                print(f"\n=== 저장된 데이터 확인 ===")
                print(f"ID: {row[0]}")
                print(f"duration (processing_time): {row[1]}")
                print(f"service_provider: {row[2]}")
                print(f"audio_duration_minutes: {row[3]}")
                print(f"tokens_used: {row[4]}")
                print(f"confidence_score: {row[5]}")
                print(f"language_detected: {row[6]}")
                
                # 검증
                if row[1] == test_processing_time:
                    print(f"\n✅ 테스트 성공! processing_time({test_processing_time})이 duration 컬럼에 올바르게 저장되었습니다.")
                else:
                    print(f"\n❌ 테스트 실패! 예상값과 다릅니다.")
                    print(f"   예상: duration={test_processing_time}")
                    print(f"   실제: duration={row[1]}")
            else:
                print(f"❌ 저장된 데이터를 찾을 수 없습니다.")
                
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_processing_time_duration()