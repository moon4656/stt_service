import requests
import json

def test_create_user():
    """새로운 사용자 생성 API 테스트"""
    url = "http://localhost:8001/users/"
    
    # 테스트 데이터 1: 개인 사용자
    user_data_1 = {
        "user_id": "test_user_personal_001",
        "email": "personal@example.com",
        "name": "김개인",
        "user_type": "개인",
        "phone_number": "010-1234-5678"
    }
    
    # 테스트 데이터 2: 조직 사용자
    user_data_2 = {
        "user_id": "test_user_org_001",
        "email": "org@company.com",
        "name": "ABC 회사",
        "user_type": "조직",
        "phone_number": "02-1234-5678"
    }
    
    # 테스트 데이터 3: 전화번호 없는 사용자
    user_data_3 = {
        "user_id": "test_user_no_phone_001",
        "email": "nophone@example.com",
        "name": "전화번호없음",
        "user_type": "개인"
    }
    
    test_cases = [
        ("개인 사용자 (전화번호 포함)", user_data_1),
        ("조직 사용자 (전화번호 포함)", user_data_2),
        ("개인 사용자 (전화번호 없음)", user_data_3)
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
            
            if response.status_code == 200:
                print("✅ 사용자 생성 성공!")
            else:
                print("❌ 사용자 생성 실패")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 요청 오류: {e}")
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")

if __name__ == "__main__":
    test_create_user()