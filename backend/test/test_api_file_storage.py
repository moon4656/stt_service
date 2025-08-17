#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STT API 파일 저장 기능 테스트 스크립트
"""

import requests
import io
import os

def test_stt_api_file_storage():
    """
    STT API를 통한 파일 저장 기능을 테스트합니다.
    """
    print("🧪 STT API 파일 저장 기능 테스트 시작")
    
    # 테스트용 가짜 음성 파일 생성
    fake_audio_content = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    
    # 파일 객체 생성
    audio_file = io.BytesIO(fake_audio_content)
    audio_file.name = "test_upload.wav"
    
    try:
        # STT API 호출
        print("📡 STT API 호출 중...")
        
        files = {
            'file': ('test_upload.wav', audio_file, 'audio/wav')
        }
        
        data = {
            'service': 'assemblyai',
            'fallback': 'true'
        }
        
        response = requests.post(
            'http://localhost:8001/transcribe/',
            files=files,
            data=data,
            timeout=30
        )
        
        print(f"📊 응답 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ STT API 호출 성공")
            print(f"📝 요청 ID: {result.get('request_id', 'N/A')}")
            print(f"🎯 서비스 사용: {result.get('service_used', 'N/A')}")
            
            # 파일이 저장되었는지 확인
            request_id = result.get('request_id')
            if request_id:
                print(f"🔍 저장된 파일 확인 중...")
                # 저장 경로는 /stt_storage/{user_uuid}/일별/{request_id}/음성파일 형태
                # 실제 저장된 파일을 찾기 위해 stt_storage 디렉토리를 확인
                storage_base = "C:\\Users\\moon4\\stt_project\\backend\\stt_storage"
                if os.path.exists(storage_base):
                    print(f"📁 저장소 디렉토리 존재 확인")
                    # 새로 생성된 파일 찾기
                    for root, dirs, files in os.walk(storage_base):
                        for file in files:
                            if file == "test_upload.wav":
                                file_path = os.path.join(root, file)
                                print(f"✅ 업로드된 파일 발견: {file_path}")
                                return True
                else:
                    print(f"❌ 저장소 디렉토리가 존재하지 않음")
        else:
            print(f"❌ STT API 호출 실패: {response.text}")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        
    return False

if __name__ == "__main__":
    success = test_stt_api_file_storage()
    if success:
        print(f"🎉 STT API 파일 저장 기능 테스트 성공")
    else:
        print(f"💥 STT API 파일 저장 기능 테스트 실패")