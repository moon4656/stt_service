import requests
import json

# 서버 URL
base_url = "http://localhost:8001"

# 테스트 데이터 - A02 user_type 사용
test_user = {
    "user_id": "test_02",
    "email": "test_02@sample.com",
    "name": "테스트조직",
    "user_type": "A02",
    "phone_number": "02-1234-5678"
}

print("Testing user creation with A02 user_type...")
print(f"Request data: {json.dumps(test_user, ensure_ascii=False, indent=2)}")

try:
    response = requests.post(f"{base_url}/users/", json=test_user)
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Success! User created successfully")
        print(f"Response: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    else:
        print("❌ Error occurred")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Request failed: {e}")