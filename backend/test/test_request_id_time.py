#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import generate_request_id
from datetime import datetime, timezone, timedelta

def test_request_id_time():
    """
    request_id 생성 시간이 한국 시간으로 제대로 생성되는지 테스트합니다.
    """
    print("=== Request ID 시간 테스트 ===")
    
    # 현재 한국 시간
    kst = timezone(timedelta(hours=9))
    current_kst = datetime.now(kst)
    print(f"현재 한국 시간: {current_kst.strftime('%Y-%m-%d %H:%M:%S KST')}")
    
    # UTC 시간
    current_utc = datetime.utcnow()
    print(f"현재 UTC 시간: {current_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # request_id 생성
    request_id = generate_request_id()
    print(f"\n생성된 request_id: {request_id}")
    
    # request_id에서 시간 부분 추출
    time_part = request_id.split('-')[1]  # HHMMSS 부분
    hour = time_part[:2]
    minute = time_part[2:4]
    second = time_part[4:6]
    
    print(f"request_id 시간 부분: {hour}:{minute}:{second}")
    print(f"현재 한국 시간: {current_kst.strftime('%H:%M:%S')}")
    
    # 시간 차이 확인 (분 단위로)
    request_hour = int(hour)
    request_minute = int(minute)
    current_hour = current_kst.hour
    current_minute = current_kst.minute
    
    time_diff_minutes = abs((current_hour * 60 + current_minute) - (request_hour * 60 + request_minute))
    
    if time_diff_minutes <= 1:  # 1분 이내 차이는 정상
        print("✅ request_id가 한국 시간으로 올바르게 생성되었습니다!")
    else:
        print(f"❌ 시간 차이가 {time_diff_minutes}분입니다. 확인이 필요합니다.")
    
    # 여러 개 생성해서 확인
    print("\n=== 추가 request_id 생성 테스트 ===")
    for i in range(3):
        new_id = generate_request_id()
        print(f"{i+1}. {new_id}")

if __name__ == "__main__":
    test_request_id_time()