import requests
import json

# 서버 URL
base_url = "http://localhost:8000"

# 테스트 케이스들
test_cases = [
    {
        "name": "개인 타입 테스트",
        "data": {
            "user_id": "test_personal_kr",
            "email": "personal_kr@example.com",
            "name": "김개인",
            "user_type": "개인",
            "phone_number": "010-1111-2222"
        },
        "expected_user_type": "A01"
    },
    {
        "name": "조직 타입 테스트",
        "data": {
            "user_id": "test_org_kr",
            "email": "org_kr@example.com",
            "name": "테스트조직",
            "user_type": "조직",
            "phone_number": "02-2222-3333"
        },
        "expected_user_type": "A02"
    },
    {
        "name": "A01 코드 직접 입력 테스트",
        "data": {
            "user_id": "test_a01_direct",
            "email": "a01_direct@example.com",
            "name": "A01직접입력",
            "user_type": "A01",
            "phone_number": "010-3333-4444"
        },
        "expected_user_type": "A01"
    },
    {
        "name": "A02 코드 직접 입력 테스트",
        "data": {
            "user_id": "test_a02_direct",
            "email": "a02_direct@example.com",
            "name": "A02직접입력",
            "user_type": "A02",
            "phone_number": "02-4444-5555"
        },
        "expected_user_type": "A02"
    }
]

print("🧪 사용자 타입 변환 테스트 시작\n")

for i, test_case in enumerate(test_cases, 1):
    print(f"{i}. {test_case['name']}")
    print(f"   입력 user_type: {test_case['data']['user_type']}")
    print(f"   예상 결과: {test_case['expected_user_type']}")
    
    try:
        response = requests.post(f"{base_url}/users/", json=test_case['data'])
        
        if response.status_code == 200:
            result = response.json()
            actual_user_type = result['user']['user_type']
            
            if actual_user_type == test_case['expected_user_type']:
                print(f"   ✅ 성공: {actual_user_type}")
            else:
                print(f"   ❌ 실패: 예상 {test_case['expected_user_type']}, 실제 {actual_user_type}")
        else:
            print(f"   ❌ API 오류: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"   ❌ 요청 실패: {e}")
    
    print()

print("🏁 테스트 완료")