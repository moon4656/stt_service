from database import engine
from sqlalchemy import text
from db_service import TranscriptionService
from sqlalchemy.orm import sessionmaker
import json

def test_confidence_language_storage():
    print("=== confidence_score와 language_detected 저장 테스트 ===")
    
    # 데이터베이스 세션 생성
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # TranscriptionService 인스턴스 생성
        transcription_service = TranscriptionService(db)
        
        # 테스트용 요청 생성
        request_record = transcription_service.create_request(
            filename="test_confidence.wav",
            file_size=1024,
            service_requested="daglo",
            fallback_enabled=True
        )
        
        print(f"✅ 테스트 요청 생성 완료 - ID: {request_record.id}")
        
        # 테스트용 STT 결과 데이터 (confidence와 language_code 포함)
        test_transcription_result = {
            "text": "안녕하세요. 이것은 테스트 음성입니다.",
            "confidence": 0.95,
            "language_code": "ko-KR",
            "service_name": "Daglo",
            "processing_time": 2.5,
            "audio_duration": 10.0
        }
        
        # confidence와 language_code 추출
        confidence_score = test_transcription_result.get('confidence')
        language_detected = test_transcription_result.get('language_code')
        
        print(f"📊 추출된 값:")
        print(f"  - confidence_score: {confidence_score}")
        print(f"  - language_detected: {language_detected}")
        
        # 응답 저장 (새로운 파라미터 포함)
        response_record = transcription_service.create_response(
            request_id=request_record.id,
            transcription_text=test_transcription_result.get('text', ''),
            summary_text="테스트 요약입니다.",
            service_used="Daglo",
            processing_time=2.5,
            duration=10.0,
            success=True,
            error_message=None,
            service_provider="Daglo",
            audio_duration_minutes=0.17,  # 10초 = 0.17분
            tokens_used=0.17,
            response_data=json.dumps(test_transcription_result, ensure_ascii=False),
            confidence_score=confidence_score,
            language_detected=language_detected
        )
        
        print(f"✅ 응답 저장 완료 - ID: {response_record.id}")
        
        # 저장된 데이터 확인
        with engine.connect() as conn:
            result = conn.execute(text('''
                SELECT id, transcribed_text, confidence_score, language_detected, 
                       service_provider, audio_duration_minutes, tokens_used
                FROM transcription_responses 
                WHERE id = :response_id
            '''), {"response_id": response_record.id})
            
            row = result.fetchone()
            if row:
                print(f"\n=== 저장된 데이터 확인 ===")
                print(f"ID: {row[0]}")
                print(f"transcribed_text: {row[1]}")
                print(f"confidence_score: {row[2]}")
                print(f"language_detected: {row[3]}")
                print(f"service_provider: {row[4]}")
                print(f"audio_duration_minutes: {row[5]}")
                print(f"tokens_used: {row[6]}")
                
                # 검증
                if row[2] == 0.95 and row[3] == "ko-KR":
                    print(f"\n✅ 테스트 성공! confidence_score와 language_detected가 올바르게 저장되었습니다.")
                else:
                    print(f"\n❌ 테스트 실패! 예상값과 다릅니다.")
                    print(f"   예상: confidence_score=0.95, language_detected='ko-KR'")
                    print(f"   실제: confidence_score={row[2]}, language_detected='{row[3]}'")
            else:
                print(f"❌ 저장된 데이터를 찾을 수 없습니다.")
                
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_confidence_language_storage()