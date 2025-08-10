import requests
import json

def test_user_creation_with_password():
    """패스워드가 포함된 사용자 생성 테스트"""
    url = "http://localhost:8001/users/"
    
    # 테스트 사용자 데이터
    user_data = {
        "user_id": "test_password_user",
        "email": "test_password@example.com",
        "name": "패스워드 테스트 사용자",
        "user_type": "A01",
        "phone_number": "010-1234-5678",
        "password": "mySecretPassword123"
    }
    
    try:
        response = requests.post(url, json=user_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ 패스워드가 포함된 사용자 생성 성공!")
        else:
            print("❌ 사용자 생성 실패")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def test_user_creation_without_password():
    """패스워드 없이 사용자 생성 시도 (실패해야 함)"""
    url = "http://localhost:8001/users/"
    
    # 패스워드가 없는 테스트 데이터
    user_data = {
        "user_id": "test_no_password_user",
        "email": "test_no_password@example.com",
        "name": "패스워드 없는 사용자",
        "user_type": "A02",
        "phone_number": "010-9876-5432"
        # password 필드 없음
    }
    
    try:
        response = requests.post(url, json=user_data)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 422:  # Validation Error
            print("✅ 패스워드 없이 사용자 생성 시 올바르게 실패함!")
        else:
            print("❌ 패스워드 없이도 사용자가 생성됨 (문제 있음)")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    print("=== 패스워드 암호화 기능 테스트 ===")
    
    print("\n1. 패스워드가 포함된 사용자 생성 테스트")
    test_user_creation_with_password()
    
    print("\n2. 패스워드 없이 사용자 생성 테스트 (실패해야 함)")
    test_user_creation_without_password()
    
    print("\n=== 테스트 완료 ===")