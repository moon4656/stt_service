import requests
import sys

def check_server_status():
    """서버 실행 상태 확인"""
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print("✅ 서버가 정상적으로 실행 중입니다.")
            return True
        else:
            print(f"⚠️ 서버 응답 이상: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
        return False
    except requests.exceptions.Timeout:
        print("❌ 서버 응답 시간 초과")
        return False
    except Exception as e:
        print(f"❌ 서버 상태 확인 오류: {e}")
        return False

if __name__ == "__main__":
    if check_server_status():
        print("서버가 실행 중이므로 계정 잠금 테스트를 진행할 수 있습니다.")
    else:
        print("먼저 서버를 실행해주세요: python app.py")
        sys.exit(1)