#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
음성파일 duration 기능 테스트 스크립트
"""

import os
import sys
from audio_utils import get_audio_duration, format_duration
from db_service import TranscriptionService
from database import get_db, create_tables, TranscriptionRequest
from sqlalchemy.orm import Session

def test_audio_duration():
    """audio_utils의 duration 계산 기능을 테스트합니다."""
    print("=== Audio Duration 기능 테스트 ===")
    
    # 테스트용 더미 파일 데이터 (실제로는 업로드된 파일 내용)
    test_files = [
        ("test.wav", b"RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xAC\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x08\x00\x00"),
        ("test.mp3", b"ID3\x03\x00\x00\x00\x00\x00\x00\x00"),
        ("test.unknown", b"unknown format")
    ]
    
    for filename, file_content in test_files:
        print(f"\n📁 파일: {filename}")
        duration = get_audio_duration(file_content, filename)
        
        if duration:
            print(f"   ⏱️ 재생 시간: {duration:.2f}초 ({format_duration(duration)})")
        else:
            print(f"   ❌ 재생 시간을 계산할 수 없습니다")

def test_database_integration():
    """데이터베이스와의 통합을 테스트합니다."""
    print("\n=== 데이터베이스 통합 테스트 ===")
    
    try:
        # 데이터베이스 연결
        db_gen = get_db()
        db = next(db_gen)
        
        # TranscriptionService 생성
        service = TranscriptionService(db)
        
        # 테스트 요청 생성 (duration 포함)
        print("\n📝 duration이 포함된 요청 생성 테스트...")
        request_record = service.create_request(
            filename="test_audio.wav",
            file_size=1024,
            duration=125.5  # 2분 5.5초
        )
        
        print(f"✅ 요청 생성 성공!")
        print(f"   - Request ID: {request_record.request_id}")
        print(f"   - 파일명: {request_record.filename}")
        print(f"   - 파일 크기: {request_record.file_size} bytes")
        print(f"   - 재생 시간: {request_record.duration}초 ({format_duration(request_record.duration)})")
        print(f"   - 상태: {request_record.status}")
        print(f"   - 생성 시간: {request_record.created_at}")
        
        # 데이터베이스에서 조회해서 확인
        print("\n🔍 데이터베이스에서 조회 확인...")
        retrieved_record = db.query(TranscriptionRequest).filter(
            TranscriptionRequest.request_id == request_record.request_id
        ).first()
        
        if retrieved_record:
            print(f"✅ 조회 성공!")
            print(f"   - Duration: {retrieved_record.duration}초")
            if retrieved_record.duration:
                print(f"   - 포맷된 시간: {format_duration(retrieved_record.duration)}")
        else:
            print(f"❌ 조회 실패")
            
        db.close()
        
    except Exception as e:
        print(f"❌ 데이터베이스 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🎵 Duration 기능 통합 테스트 시작\n")
    
    # 1. Audio duration 계산 테스트
    test_audio_duration()
    
    # 2. 데이터베이스 통합 테스트
    test_database_integration()
    
    print("\n🎉 테스트 완료!")