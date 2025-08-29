import os
import time
import subprocess
import webbrowser
from pathlib import Path

def print_header(text):
    """헤더 텍스트를 출력합니다."""
    print("\n" + "=" * 60)
    print(f" {text} ")
    print("=" * 60)

def run_command(command, description=None):
    """명령어를 실행하고 결과를 출력합니다."""
    if description:
        print(f"\n> {description}")
    
    print(f"실행 명령어: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.stdout:
        print("\n출력:")
        print(result.stdout)
    
    if result.returncode != 0:
        print(f"\n오류 발생 (코드 {result.returncode}):")
        print(result.stderr)
        return False, result.stderr
    
    return True, result.stdout

def main():
    print_header("가상 회의록 생성 및 STT 서비스 데모")
    
    # 1. 가상 회의록 생성
    print_header("1. 가상 회의록 생성")
    success, output = run_command(["python", "generate_meeting_audio.py"], 
                                "가상의 3자 대면 회의록을 생성합니다.")
    if not success:
        print("회의록 생성에 실패했습니다. 프로그램을 종료합니다.")
        return
    
    # 생성된 회의록 파일 경로 찾기
    meeting_scripts_dir = Path("meeting_scripts")
    if not meeting_scripts_dir.exists():
        print(f"'{meeting_scripts_dir}' 디렉토리를 찾을 수 없습니다. 프로그램을 종료합니다.")
        return
    
    txt_files = list(meeting_scripts_dir.glob("*.txt"))
    if not txt_files:
        print(f"'{meeting_scripts_dir}' 디렉토리에 텍스트 파일이 없습니다. 프로그램을 종료합니다.")
        return
    
    # 가장 최근 파일 선택
    latest_txt_file = max(txt_files, key=lambda p: p.stat().st_mtime)
    print(f"\n생성된 회의록 파일: {latest_txt_file}")
    
    # 2. 텍스트를 음성으로 변환
    print_header("2. 텍스트를 음성으로 변환")
    success, output = run_command(["python", "text_to_speech.py", str(latest_txt_file)],
                                "회의록 텍스트를 음성으로 변환합니다.")
    if not success:
        print("음성 변환에 실패했습니다. 프로그램을 종료합니다.")
        return
    
    # 생성된 음성 파일 경로 찾기
    audio_dir = Path("meeting_audios")
    if not audio_dir.exists():
        print(f"'{audio_dir}' 디렉토리를 찾을 수 없습니다. 프로그램을 종료합니다.")
        return
    
    audio_files = list(audio_dir.glob("*.*"))
    if not audio_files:
        print(f"'{audio_dir}' 디렉토리에 오디오 파일이 없습니다. 프로그램을 종료합니다.")
        return
    
    # 가장 최근 파일 선택
    latest_audio_file = max(audio_files, key=lambda p: p.stat().st_mtime)
    print(f"\n생성된 파일: {latest_audio_file}")
    
    # 생성된 파일 열기 (텍스트 파일이므로 텍스트 에디터로 열기)
    print("\n[중요] 생성된 파일은 실제 음성 파일이 아닌 텍스트 파일입니다.")
    print("      이 파일을 확인하시겠습니까? (y/n)")
    user_input = input("> ")
    
    if user_input.lower() == 'y':
        try:
            # 텍스트 에디터로 파일 열기 (Windows의 기본 메모장 사용)
            subprocess.run(["notepad.exe", str(latest_audio_file)])
            print("파일이 메모장에서 열렸습니다.")
        except Exception as e:
            print(f"파일을 열 수 없습니다: {str(e)}")
            print(f"직접 파일을 열어보세요: {latest_audio_file}")
    else:
        print("파일 확인을 건너뜁니다.")
    
    # 3. STT 서비스 실행
    print_header("3. STT 서비스 실행")
    print("STT 서비스를 시작합니다. 서버가 실행되면 브라우저가 자동으로 열립니다.")
    print("서버를 종료하려면 Ctrl+C를 누르세요.")
    
    # 비동기로 서버 실행
    server_process = subprocess.Popen(["python", "app.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE, 
                                    text=True)
    
    # 서버가 시작될 때까지 잠시 대기
    print("서버 시작 중...", end="")
    for _ in range(5):
        time.sleep(1)
        print(".", end="", flush=True)
    print("\n")
    
    # 브라우저에서 Swagger UI 열기
    swagger_url = "http://localhost:8000/docs"
    print(f"브라우저에서 {swagger_url} 페이지를 엽니다.")
    webbrowser.open(swagger_url)
    
    print("\n이제 Swagger UI에서 /transcribe/ 엔드포인트를 사용하여 생성된 음성 파일을 업로드하세요.")
    print(f"업로드할 파일 경로: {latest_audio_file}")
    print("\n서버를 종료하려면 이 창에서 Ctrl+C를 누르세요.")
    
    try:
        # 사용자가 Ctrl+C를 누를 때까지 서버 실행 유지
        server_process.wait()
    except KeyboardInterrupt:
        print("\n사용자에 의해 서버가 종료되었습니다.")
    finally:
        if server_process.poll() is None:
            server_process.terminate()
            print("서버가 종료되었습니다.")
    
    print_header("데모 완료")
    print("전체 워크플로우 데모가 완료되었습니다.")
    print("1. 가상 회의록 생성: 완료")
    print("2. 텍스트를 음성으로 변환: 완료")
    print("3. STT 서비스 실행 및 테스트: 완료")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n사용자에 의해 프로그램이 종료되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")