import requests
import hashlib

# 서버 URL
BASE_URL = "http://localhost:8001"

def test_api_key_verification():
    """API 키 검증 테스트"""
    print("=== API 키 검증 디버깅 ===")
    
    # 테스트할 API 키들 (실제 키가 아닌 예시)
    test_keys = [
        "moontech_api_key_example",  # 실제 키로 교체 필요
        "invalid_key_test"
    ]
    
    for api_key in test_keys:
        print(f"\n테스트 API 키: {api_key[:20]}...")
        
        # API 키 해시 계산
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        print(f"API 키 해시: {api_key_hash[:20]}...")
        
        # API 키로 검증 요청
        headers = {"Authorization": f"Bearer {api_key}"}
        
        try:
            response = requests.get(f"{BASE_URL}/tokens/verify", headers=headers)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ API 키 검증 성공")
                print(f"응답: {response.json()}")
            else:
                print("❌ API 키 검증 실패")
                print(f"오류: {response.json()}")
                
        except Exception as e:
            print(f"❌ 요청 중 오류: {e}")

def test_protected_endpoint():
    """보호된 엔드포인트 테스트"""
    print("\n=== 보호된 엔드포인트 테스트 ===")
    
    # 잘못된 API 키로 테스트
    headers = {"Authorization": "Bearer invalid_api_key"}
    
    try:
        response = requests.post(f"{BASE_URL}/transcribe/protected/", headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"응답: {response.json()}")
        
    except Exception as e:
        print(f"❌ 요청 중 오류: {e}")

if __name__ == "__main__":
    test_api_key_verification()
    test_protected_endpoint()