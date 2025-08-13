import os
import json
import argparse
from pathlib import Path
import requests
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 기본 TTS API 설정 (Daglo TTS API)
# 실제 사용 시에는 해당 API 키를 .env 파일에 설정해야 합니다.
TTS_API_URL = "https://apis.daglo.ai/tts/v1/sync/audios"  # Daglo TTS API URL
TTS_API_KEY = os.getenv("TTS_API_KEY", "")

def text_to_speech(text, output_path, voice_type="ko_KR_Jimin"):
    """
    텍스트를 음성으로 변환합니다. (Daglo TTS API 호출)
    
    참고: 이 함수는 Daglo TTS API를 호출하는 코드입니다.
    사용 가능한 voice_type:
    - ko_KR_Jimin: 지민, 성인, 여성, 차분
    - en_US_Olivia: 올리비아, 성인, 여성, 친근
    """
    try:
        # API 요청 헤더
        headers = {
            "Authorization": f"Bearer {TTS_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # API 요청 데이터
        data = {
            "text": text
            # voice 파라미터는 기본값으로 설정됨 (Daglo API는 요청에서 voice를 지정하지 않음)
        }
        
        # API 호출
        response = requests.post(TTS_API_URL, headers=headers, json=data)
        
        # 응답 확인
        if response.status_code == 200:
            # 음성 파일 저장
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"[Daglo TTS] '{output_path}'에 음성 파일이 저장되었습니다.")
            return True, output_path
        else:
            return False, f"API 오류: {response.status_code} - {response.text}"
    
    except Exception as e:
        return False, f"오류 발생: {str(e)}"

def mock_text_to_speech(text, output_path, voice_type="ko_KR_Jimin"):
    """
    실제 API 호출 없이 텍스트를 음성으로 변환했다고 가정하는 모의 함수입니다.
    실제 Daglo TTS API가 없을 때 테스트용으로 사용할 수 있습니다.
    
    사용 가능한 voice_type:
    - ko_KR_Jimin: 지민, 성인, 여성, 차분
    - en_US_Olivia: 올리비아, 성인, 여성, 친근
    """
    try:
        # 출력 디렉토리 확인 및 생성
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 파일 확장자 확인 및 수정 (mp3 확장자로 저장하되 실제로는 텍스트 파일)
        if not output_path.lower().endswith('.txt'):
            # 원래 확장자를 유지하되 내부는 텍스트로 저장
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"[이 파일은 실제 음성 파일이 아닌 Daglo TTS API 변환 시뮬레이션 파일입니다]\n\n")
                f.write(f"음성 유형: {voice_type}\n\n")
                f.write(text)
        
        print(f"[모의 Daglo TTS] '{output_path}'에 텍스트가 저장되었습니다.")
        print(f"[참고] 실제 Daglo TTS API를 사용하려면 .env 파일에 TTS_API_KEY를 설정하고 --use-real-api 옵션을 사용하세요.")
        print(f"[중요] 이 파일은 실제 음성 파일이 아니므로 일반 미디어 플레이어로 재생되지 않습니다.")
        print(f"      텍스트 에디터로 열어서 내용을 확인할 수 있습니다.")
        
        return True, output_path
    
    except Exception as e:
        return False, f"오류 발생: {str(e)}"

def process_meeting_script(script_path, output_dir="meeting_audios", use_mock=True, voice_type="ko_KR_Jimin"):
    """
    회의 스크립트를 처리하여 각 발언을 음성으로 변환합니다.
    
    Args:
        script_path (str): 회의 스크립트 파일 경로 (.txt 또는 .json)
        output_dir (str): 출력 디렉토리 (기본값: meeting_audios)
        use_mock (bool): 모의 TTS 사용 여부 (True: 모의 TTS, False: 실제 Daglo TTS API)
        voice_type (str): 음성 유형 (ko_KR_Jimin 또는 en_US_Olivia)
    """
    # 출력 디렉토리 생성
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # 스크립트 파일 확장자 확인 및 로드
    script_path = Path(script_path)
    if script_path.suffix.lower() == ".json":
        # JSON 파일 로드
        with open(script_path, "r", encoding="utf-8") as f:
            meeting_data = json.load(f)
        script_lines = meeting_data.get("script", [])
    else:
        # 텍스트 파일 로드
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 회의 내용 부분만 추출
        if "회의 내용:" in content:
            script_part = content.split("회의 내용:")[1].strip()
            script_lines = script_part.split("\n")
        else:
            script_lines = content.split("\n")
    
    # 전체 스크립트를 하나의 파일로 변환
    full_script = "\n".join(script_lines)
    output_filename = f"{script_path.stem}_full.mp3"
    full_output_path = output_path / output_filename
    
    # TTS 변환 (실제 또는 모의)
    if use_mock:
        success, result = mock_text_to_speech(full_script, str(full_output_path), voice_type)
    else:
        success, result = text_to_speech(full_script, str(full_output_path), voice_type)
    
    if success:
        print(f"회의록 음성 파일이 생성되었습니다: {result}")
        return result
    else:
        print(f"음성 변환 실패: {result}")
        return None

def main():
    parser = argparse.ArgumentParser(description="회의 스크립트를 음성으로 변환합니다.")
    parser.add_argument("script_path", help="회의 스크립트 파일 경로 (.txt 또는 .json)")
    parser.add_argument("--output-dir", "-o", default="meeting_audios", help="출력 디렉토리 (기본값: meeting_audios)")
    parser.add_argument("--use-real-api", action="store_true", help="실제 Daglo TTS API 사용 (기본값: 모의 TTS 사용)")
    parser.add_argument("--voice", default="ko_KR_Jimin", choices=["ko_KR_Jimin", "en_US_Olivia"], 
                      help="음성 유형 선택 (ko_KR_Jimin: 지민, en_US_Olivia: 올리비아)")
    
    args = parser.parse_args()
    
    # API 키 확인
    if args.use_real_api and not TTS_API_KEY:
        print("[오류] 실제 Daglo TTS API를 사용하려면 .env 파일에 TTS_API_KEY를 설정해야 합니다.")
        print("      .env.example 파일을 참고하여 .env 파일을 생성하고 API 키를 설정하세요.")
        return
    
    # 스크립트 처리 및 음성 변환
    audio_path = process_meeting_script(args.script_path, args.output_dir, not args.use_real_api, args.voice)
    
    if audio_path:
        if args.use_real_api:
            print("\n이제 생성된 음성 파일을 STT(Speech-to-Text) 서비스에 업로드하여 텍스트로 다시 변환할 수 있습니다.")
            print(f"STT 서비스 사용 예시: python app.py (서버 실행 후 http://localhost:8000/docs에서 /transcribe/ 엔드포인트 사용)")
        else:
            print("\n[참고] 현재 모의 TTS 모드를 사용 중입니다. 실제 음성 파일을 생성하려면 --use-real-api 옵션을 사용하세요.")
            print(f"      예: python {os.path.basename(__file__)} {args.script_path} --use-real-api")

if __name__ == "__main__":
    main()