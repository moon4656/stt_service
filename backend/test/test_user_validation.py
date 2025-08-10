import requests
import json

def test_user_validation():
    """사용자 생성 API 검증 테스트"""
    url = "http://localhost:8001/users/"
    
    # 테스트 데이터 1: 잘못된 사용구분
    invalid_user_type = {
        "user_id": "test_invalid_type",
        "email": "invalid@example.com",
        "name": "잘못된타입",
        "user_type": "기업",  # 잘못된 값 ("개인" 또는 "조직"만 허용)
        "phone_number": "010-1111-2222"
    }
    
    # 테스트 데이터 2: 중복된 사용자 ID
    duplicate_user = {
        "user_id": "test_user_personal_001",  # 이미 존재하는 ID
        "email": "duplicate@example.com",
        "name": "중복사용자",
        "user_type": "개인",
        "phone_number": "010-3333-4444"
    }
    
    # 테스트 데이터 3: 필수 필드 누락
    missing_field = {
        "user_id": "test_missing_field",
        "email": "missing@example.com",
        "name": "필드누락"
        # user_type 누락
    }
    
    test_cases = [
        ("잘못된 사용구분", invalid_user_type),
        ("중복된 사용자 ID", duplicate_user),
        ("필수 필드 누락", missing_field)
    ]
    
    for test_name, user_data in test_cases:
        print(f"\n=== {test_name} 테스트 ===")
        print(f"요청 데이터: {json.dumps(user_data, ensure_ascii=False, indent=2)}")
        
        try:
            response = requests.post(
                url,
                json=user_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"응답 상태 코드: {response.status_code}")
            print(f"응답 내용: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
            
            if response.status_code != 200:
                print("✅ 예상대로 검증 실패!")
            else:
                print("❌ 검증이 제대로 작동하지 않음")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 요청 오류: {e}")
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")

if __name__ == "__main__":
    test_user_validation()