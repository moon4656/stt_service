import pytest
import requests
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any

# 테스트 설정
BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = "test_subscription@example.com"
TEST_PASSWORD = "test123456"
TEST_PLAN_CODE = "basic_plan"
TEST_PLAN_CODE_PREMIUM = "premium_plan"

class TestSubscriptionAPI:
    """구독 관련 API 테스트 클래스"""
    
    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        self.access_token = None
        self.user_uuid = None
        self.subscription_id = None
        self.plan_id = None
        
    def get_auth_headers(self) -> Dict[str, str]:
        """인증 헤더 반환"""
        if not self.access_token:
            self._login_test_user()
        return {"Authorization": f"Bearer {self.access_token}"}
    
    def _login_test_user(self):
        """테스트 사용자 로그인"""
        # 사용자 생성 (이미 존재하면 무시)
        user_data = {
            "email": TEST_USER_EMAIL,
            "password": TEST_PASSWORD,
            "user_type": "individual"
        }
        requests.post(f"{BASE_URL}/users/", json=user_data)
        
        # 로그인
        login_data = {
            "username": TEST_USER_EMAIL,
            "password": TEST_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/token", data=login_data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.user_uuid = token_data.get("user_uuid")
    
    def _create_test_plan(self) -> str:
        """테스트용 구독 플랜 생성"""
        plan_data = {
            "plan_code": TEST_PLAN_CODE,
            "plan_name": "기본 플랜",
            "monthly_price": 10000,
            "service_tokens": 1000,
            "description": "테스트용 기본 플랜",
            "is_active": True
        }
        response = requests.post(
            f"{BASE_URL}/subscription-plans/",
            json=plan_data,
            headers=self.get_auth_headers()
        )
        if response.status_code == 200:
            return response.json()["data"]["id"]
        return None
    
    def _create_premium_plan(self) -> str:
        """테스트용 프리미엄 구독 플랜 생성"""
        plan_data = {
            "plan_code": TEST_PLAN_CODE_PREMIUM,
            "plan_name": "프리미엄 플랜",
            "monthly_price": 20000,
            "service_tokens": 3000,
            "description": "테스트용 프리미엄 플랜",
            "is_active": True
        }
        response = requests.post(
            f"{BASE_URL}/subscription-plans/",
            json=plan_data,
            headers=self.get_auth_headers()
        )
        if response.status_code == 200:
            return response.json()["data"]["id"]
        return None

    def test_create_subscription(self):
        """구독 생성 테스트"""
        # 테스트 플랜 생성
        self.plan_id = self._create_test_plan()
        assert self.plan_id is not None, "테스트 플랜 생성 실패"
        
        # 구독 생성
        subscription_data = {
            "plan_code": TEST_PLAN_CODE,
            "billing_cycle_start_date": date.today().isoformat(),
            "billing_cycle_end_date": (date.today() + timedelta(days=30)).isoformat()
        }
        
        response = requests.post(
            f"{BASE_URL}/subscriptions/",
            json=subscription_data,
            headers=self.get_auth_headers()
        )
        
        print(f"구독 생성 응답: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"구독 생성 실패: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert "subscription_id" in data["data"]
        self.subscription_id = data["data"]["subscription_id"]
    
    def test_get_user_subscription(self):
        """사용자 구독 조회 테스트"""
        # 먼저 구독 생성
        self.test_create_subscription()
        
        response = requests.get(
            f"{BASE_URL}/subscriptions/",
            headers=self.get_auth_headers()
        )
        
        print(f"구독 조회 응답: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"구독 조회 실패: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert "subscription" in data["data"]
        assert data["data"]["subscription"]["plan_code"] == TEST_PLAN_CODE
    
    def test_update_subscription(self):
        """구독 수정 테스트"""
        # 먼저 구독 생성
        self.test_create_subscription()
        
        update_data = {
            "subscription_status": "suspended",
            "auto_renewal": False
        }
        
        response = requests.put(
            f"{BASE_URL}/subscriptions/{self.subscription_id}",
            json=update_data,
            headers=self.get_auth_headers()
        )
        
        print(f"구독 수정 응답: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"구독 수정 실패: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["subscription_status"] == "suspended"
    
    def test_subscription_upgrade(self):
        """구독 업그레이드 테스트"""
        # 기본 구독 생성
        self.test_create_subscription()
        
        # 프리미엄 플랜 생성
        self._create_premium_plan()
        
        # 업그레이드 요청
        change_data = {
            "change_type": "upgrade",
            "new_plan_code": TEST_PLAN_CODE_PREMIUM,
            "change_reason": "더 많은 토큰이 필요함",
            "effective_date": date.today().isoformat()
        }
        
        response = requests.post(
            f"{BASE_URL}/subscriptions/{self.subscription_id}/change",
            json=change_data,
            headers=self.get_auth_headers()
        )
        
        print(f"구독 업그레이드 응답: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"구독 업그레이드 실패: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["change_type"] == "upgrade"
        assert data["data"]["new_plan_code"] == TEST_PLAN_CODE_PREMIUM
    
    def test_subscription_downgrade(self):
        """구독 다운그레이드 테스트"""
        # 프리미엄 구독 생성
        self.plan_id = self._create_premium_plan()
        self._create_test_plan()  # 기본 플랜도 생성
        
        subscription_data = {
            "plan_code": TEST_PLAN_CODE_PREMIUM,
            "billing_cycle_start_date": date.today().isoformat(),
            "billing_cycle_end_date": (date.today() + timedelta(days=30)).isoformat()
        }
        
        response = requests.post(
            f"{BASE_URL}/subscriptions/",
            json=subscription_data,
            headers=self.get_auth_headers()
        )
        
        assert response.status_code == 200
        self.subscription_id = response.json()["data"]["subscription_id"]
        
        # 다운그레이드 요청
        change_data = {
            "change_type": "downgrade",
            "new_plan_code": TEST_PLAN_CODE,
            "change_reason": "비용 절약",
            "effective_date": date.today().isoformat()
        }
        
        response = requests.post(
            f"{BASE_URL}/subscriptions/{self.subscription_id}/change",
            json=change_data,
            headers=self.get_auth_headers()
        )
        
        print(f"구독 다운그레이드 응답: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"구독 다운그레이드 실패: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["change_type"] == "downgrade"
        assert data["data"]["new_plan_code"] == TEST_PLAN_CODE
    
    def test_subscription_cancel(self):
        """구독 취소 테스트"""
        # 먼저 구독 생성
        self.test_create_subscription()
        
        # 취소 요청
        change_data = {
            "change_type": "cancel",
            "change_reason": "서비스 불만족",
            "effective_date": date.today().isoformat()
        }
        
        response = requests.post(
            f"{BASE_URL}/subscriptions/{self.subscription_id}/change",
            json=change_data,
            headers=self.get_auth_headers()
        )
        
        print(f"구독 취소 응답: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"구독 취소 실패: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["change_type"] == "cancel"
    
    def test_get_subscription_history(self):
        """구독 변경 이력 조회 테스트"""
        # 먼저 구독 생성 및 변경
        self.test_subscription_upgrade()
        
        response = requests.get(
            f"{BASE_URL}/subscriptions/{self.subscription_id}/history",
            headers=self.get_auth_headers()
        )
        
        print(f"구독 이력 조회 응답: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"구독 이력 조회 실패: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert "history" in data["data"]
        assert len(data["data"]["history"]) > 0
    
    def test_invalid_subscription_change(self):
        """잘못된 구독 변경 요청 테스트"""
        # 먼저 구독 생성
        self.test_create_subscription()
        
        # 잘못된 변경 요청 (존재하지 않는 플랜)
        change_data = {
            "change_type": "upgrade",
            "new_plan_code": "nonexistent_plan",
            "change_reason": "테스트",
            "effective_date": date.today().isoformat()
        }
        
        response = requests.post(
            f"{BASE_URL}/subscriptions/{self.subscription_id}/change",
            json=change_data,
            headers=self.get_auth_headers()
        )
        
        print(f"잘못된 구독 변경 응답: {response.status_code} - {response.text}")
        assert response.status_code == 404, "존재하지 않는 플랜에 대한 적절한 에러 응답이 없음"
    
    def test_proration_calculation(self):
        """비례 계산 테스트"""
        # 기본 구독 생성
        self.test_create_subscription()
        
        # 프리미엄 플랜 생성
        self._create_premium_plan()
        
        # 업그레이드 요청 (비례 계산 포함)
        change_data = {
            "change_type": "upgrade",
            "new_plan_code": TEST_PLAN_CODE_PREMIUM,
            "change_reason": "업그레이드 테스트",
            "effective_date": (date.today() + timedelta(days=15)).isoformat()  # 중간 시점
        }
        
        response = requests.post(
            f"{BASE_URL}/subscriptions/{self.subscription_id}/change",
            json=change_data,
            headers=self.get_auth_headers()
        )
        
        print(f"비례 계산 테스트 응답: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"비례 계산 테스트 실패: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        
        # 비례 계산 상세 정보 확인
        if "proration_details" in data["data"]:
            proration = data["data"]["proration_details"]
            assert "remaining_days" in proration
            assert "total_days" in proration
            assert "current_plan_daily_rate" in proration
            assert "new_plan_daily_rate" in proration
            print(f"비례 계산 상세: {proration}")


if __name__ == "__main__":
    # 개별 테스트 실행을 위한 코드
    test_instance = TestSubscriptionAPI()
    test_instance.setup_method()
    
    print("=== 구독 API 테스트 시작 ===")
    
    try:
        print("\n1. 구독 생성 테스트")
        test_instance.test_create_subscription()
        print("✅ 구독 생성 테스트 통과")
        
        print("\n2. 구독 조회 테스트")
        test_instance.test_get_user_subscription()
        print("✅ 구독 조회 테스트 통과")
        
        print("\n3. 구독 업그레이드 테스트")
        test_instance.test_subscription_upgrade()
        print("✅ 구독 업그레이드 테스트 통과")
        
        print("\n4. 구독 이력 조회 테스트")
        test_instance.test_get_subscription_history()
        print("✅ 구독 이력 조회 테스트 통과")
        
        print("\n=== 모든 테스트 완료 ===")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()