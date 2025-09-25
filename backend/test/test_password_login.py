import requests
import json

# 서버 URL
BASE_URL = "http://localhost:8000"

def test_login_with_correct_password():
    """올바른 패스워드로 로그인 테스트"""
    print("\n=== 올바른 패스워드로 로그인 테스트 ===")
    
    login_data = {
        "user_id": "test_01",  # 실제 존재하는 사용자 ID로 변경
        "password": "password"  # 기존 사용자들의 기본 패스워드
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 로그인 성공!")
            print(f"Access Token: {result['access_token'][:50]}...")
            print(f"Token Type: {result['token_type']}")
            print(f"User Info: {json.dumps(result['user'], indent=2, ensure_ascii=False)}")
            return result['access_token']
        else:
            print(f"❌ 로그인 실패: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 요청 중 오류 발생: {e}")
        return None

def test_login_with_wrong_password():
    """잘못된 패스워드로 로그인 테스트"""
    print("\n=== 잘못된 패스워드로 로그인 테스트 ===")
    
    login_data = {
        "user_id": "test_01",
        "password": "wrong_password"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ 잘못된 패스워드로 로그인 실패 (예상된 결과)")
            print(f"Error: {response.json()}")
        else:
            print(f"❌ 예상과 다른 응답: {response.text}")
            
    except Exception as e:
        print(f"❌ 요청 중 오류 발생: {e}")

def test_login_with_nonexistent_user():
    """존재하지 않는 사용자로 로그인 테스트"""
    print("\n=== 존재하지 않는 사용자로 로그인 테스트 ===")
    
    login_data = {
        "user_id": "nonexistent_user",
        "password": "any_password"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ 존재하지 않는 사용자로 로그인 실패 (예상된 결과)")
            print(f"Error: {response.json()}")
        else:
            print(f"❌ 예상과 다른 응답: {response.text}")
            
    except Exception as e:
        print(f"❌ 요청 중 오류 발생: {e}")

def test_login_with_new_user_password():
    """새로 생성된 사용자의 패스워드로 로그인 테스트"""
    print("\n=== 새로 생성된 사용자 패스워드로 로그인 테스트 ===")
    
    login_data = {
        "user_id": "test_password_user",
        "password": "mySecretPassword123"  # 이전에 생성한 사용자의 패스워드
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 새 사용자 패스워드로 로그인 성공!")
            print(f"Access Token: {result['access_token'][:50]}...")
            print(f"User Info: {json.dumps(result['user'], indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 로그인 실패: {response.text}")
            
    except Exception as e:
        print(f"❌ 요청 중 오류 발생: {e}")

def test_login_without_password():
    """패스워드 없이 로그인 테스트"""
    print("\n=== 패스워드 없이 로그인 테스트 ===")
    
    login_data = {
        "user_id": "test_01"
        # password 필드 누락
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 422:
            print("✅ 패스워드 없이 로그인 실패 (예상된 결과)")
            print(f"Validation Error: {response.json()}")
        else:
            print(f"❌ 예상과 다른 응답: {response.text}")
            
    except Exception as e:
        print(f"❌ 요청 중 오류 발생: {e}")

def test_multiple_existing_users():
    """여러 기존 사용자들의 로그인 테스트"""
    print("\n=== 여러 기존 사용자들의 로그인 테스트 ===")
    
    test_users = [
        "test_01",
        "test_02", 
        "test_personal_kr",
        "test_org_kr"
    ]
    
    for user_id in test_users:
        login_data = {
            "user_id": user_id,
            "password": "password"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {user_id}: 로그인 성공")
            else:
                print(f"❌ {user_id}: 로그인 실패 - {response.text}")
                
        except Exception as e:
            print(f"❌ {user_id}: 요청 중 오류 발생 - {e}")

if __name__ == "__main__":
    print("패스워드 로그인 기능 테스트 시작")
    
    # 각 테스트 실행
    test_login_with_correct_password()
    test_login_with_wrong_password()
    test_login_with_nonexistent_user()
    test_login_with_new_user_password()
    test_login_without_password()
    test_multiple_existing_users()
    
    print("\n=== 모든 테스트 완료 ===")