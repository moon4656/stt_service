import sys
sys.path.append('.')
from auth import TokenManager
from database import get_db
import time
import requests

def test_new_api_key():
    """새로운 API 키 생성 및 테스트"""
    print("=== 새로운 API 키 생성 및 테스트 ===")
    
    # 데이터베이스 연결
    db = next(get_db())
    
    try:
        # 새 API 키 생성
        unique_id = f'test_{int(time.time())}'
        result = TokenManager.generate_api_key(
            '77cc0d1d-5975-4f02-b3ed-30563cc5c93c', 
            unique_id, 
            'Test API key', 
            db
        )
        
        print(f"생성된 API 키: {result['api_key']}")
        print(f"API 키 해시: {result['api_key_hash']}")
        
        # API 키로 검증 테스트
        api_key = result['api_key']
        print(f"\n검증 테스트 중... API 키: {api_key[:20]}...")
        
        response = requests.get(
            'http://localhost:8001/tokens/verify',
            headers={'Authorization': f'Bearer {api_key}'}
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ API 키 검증 성공: {response.json()}")
        else:
            print(f"❌ API 키 검증 실패: {response.text}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_new_api_key()