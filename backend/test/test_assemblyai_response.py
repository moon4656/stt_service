import requests
import json
from assemblyai_service import AssemblyAIService
from create_test_audio import create_test_audio
import os

def test_assemblyai_actual_response():
    """AssemblyAI의 실제 응답에서 transcript_id 형태 확인"""
    
    try:
        # 1. 테스트 오디오 파일 생성
        test_file = "test_assemblyai_id.wav"
        create_test_audio(test_file, duration_seconds=3)
        print(f"✅ 테스트 오디오 파일 생성: {test_file}")
        
        # 2. AssemblyAI 서비스 초기화
        service = AssemblyAIService()
        
        # 3. 파일 읽기
        with open(test_file, 'rb') as f:
            file_content = f.read()
        
        print("🚀 AssemblyAI 직접 호출 시작...")
        
        # 4. AssemblyAI 서비스 직접 호출
        result = service.transcribe_file(
            file_content=file_content,
            filename=test_file,
            language_code="ko"
        )
        
        print("📊 AssemblyAI 응답 분석:")
        print(f"   transcript_id: {result.get('transcript_id')}")
        print(f"   transcript_id 타입: {type(result.get('transcript_id'))}")
        print(f"   transcript_id 길이: {len(str(result.get('transcript_id')))}")
        
        # transcript_id가 UUID 형태인지 확인
        transcript_id = result.get('transcript_id')
        if transcript_id:
            # UUID 형태 확인 (8-4-4-4-12 패턴)
            import re
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            is_uuid = bool(re.match(uuid_pattern, str(transcript_id), re.IGNORECASE))
            print(f"   UUID 형태인가? {is_uuid}")
            
            if not is_uuid:
                print(f"   ✅ 실제 AssemblyAI transcript_id (문자열): {transcript_id}")
            else:
                print(f"   ⚠️ UUID 형태로 변환됨: {transcript_id}")
        
        # 5. full_response에서 원본 응답 확인
        full_response = result.get('full_response', {})
        if full_response:
            original_id = full_response.get('id')
            print(f"\n📋 원본 AssemblyAI 응답:")
            print(f"   원본 ID: {original_id}")
            print(f"   원본 ID 타입: {type(original_id)}")
            if original_id:
                import re
                uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                is_uuid = bool(re.match(uuid_pattern, str(original_id), re.IGNORECASE))
                print(f"   원본 ID가 UUID 형태인가? {is_uuid}")
        
        # 6. 파일 정리
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"\n🗑️ 테스트 파일 삭제: {test_file}")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_assemblyai_actual_response()