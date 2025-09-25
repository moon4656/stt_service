#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
올바른 패스워드로 로그인 테스트
"""

import sys
import os
import requests
import json

# core 디렉토리를 sys.path에 추가
core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core')
sys.path.insert(0, core_path)

def test_correct_login():
    print("🔐 올바른 패스워드로 로그인 테스트")
    print("=" * 50)
    
    # 로그인 데이터
    login_data = {
        "email": "test_lock@example.com",
        "password": "correct_password"
    }
    
    try:
        # 로그인 요청
        response = requests.post(
            "http://localhost:8000/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"응답 상태 코드: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 로그인 성공!")
            print(f"응답 데이터: {json.dumps(result, indent=2, ensure_ascii=False)}")
            if 'access_token' in result:
                print(f"🎉 JWT 토큰 발급됨: {result['access_token'][:50]}...")
        else:
            print(f"❌ 로그인 실패")
            try:
                error_data = response.json()
                print(f"에러 응답: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"에러 응답 (텍스트): {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_correct_login()