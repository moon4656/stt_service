import pyttsx3
import os
import time

def create_real_voice_file(text="안녕하세요. 이것은 음성 인식 테스트입니다. 한국어로 말하고 있습니다.", filename="real_voice_test.wav"):
    """
    실제 TTS를 사용해서 음성 파일 생성
    """
    try:
        # TTS 엔진 초기화
        engine = pyttsx3.init()
        
        # 음성 설정
        voices = engine.getProperty('voices')
        
        # 한국어 음성 찾기 (없으면 기본 음성 사용)
        korean_voice = None
        for voice in voices:
            if 'korean' in voice.name.lower() or 'ko' in voice.id.lower():
                korean_voice = voice
                break
        
        if korean_voice:
            engine.setProperty('voice', korean_voice.id)
            print(f"✅ 한국어 음성 사용: {korean_voice.name}")
        else:
            print(f"⚠️ 한국어 음성을 찾을 수 없어 기본 음성 사용")
        
        # 속도와 볼륨 설정
        engine.setProperty('rate', 150)  # 말하기 속도
        engine.setProperty('volume', 0.9)  # 볼륨
        
        # 음성 파일로 저장
        engine.save_to_file(text, filename)
        engine.runAndWait()
        
        # 파일이 생성될 때까지 잠시 대기
        time.sleep(2)
        
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            print(f"✅ 음성 파일 생성 완료: {filename}")
            print(f"   - 텍스트: {text}")
            print(f"   - 파일 크기: {file_size} bytes")
            return filename
        else:
            print(f"❌ 음성 파일 생성 실패: {filename}")
            return None
            
    except Exception as e:
        print(f"❌ TTS 오류: {e}")
        return None

def create_multiple_voice_files():
    """
    여러 언어와 텍스트로 음성 파일 생성
    """
    
    test_cases = [
        {
            "text": "Hello, this is a voice recognition test in English.",
            "filename": "english_voice_test.wav",
            "description": "영어 음성 테스트"
        },
        {
            "text": "안녕하세요. 한국어 음성 인식 테스트입니다. 잘 들리시나요?",
            "filename": "korean_voice_test.wav",
            "description": "한국어 음성 테스트"
        },
        {
            "text": "One two three four five. Testing numbers and simple words.",
            "filename": "simple_english_test.wav",
            "description": "간단한 영어 단어 테스트"
        }
    ]
    
    print("🎤 여러 음성 파일 생성 중...")
    print("=" * 50)
    
    created_files = []
    
    for test_case in test_cases:
        print(f"\n📝 {test_case['description']}")
        result = create_real_voice_file(test_case['text'], test_case['filename'])
        if result:
            created_files.append(result)
    
    print(f"\n✅ 총 {len(created_files)}개 파일 생성 완료!")
    for file in created_files:
        print(f"   - {file}")
    
    return created_files

if __name__ == "__main__":
    try:
        # pyttsx3 설치 확인
        import pyttsx3
        print("✅ pyttsx3 모듈 확인됨")
        
        # 여러 음성 파일 생성
        create_multiple_voice_files()
        
    except ImportError:
        print("❌ pyttsx3 모듈이 설치되지 않았습니다.")
        print("다음 명령어로 설치하세요: pip install pyttsx3")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()