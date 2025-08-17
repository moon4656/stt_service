#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db, TranscriptionRequest, TranscriptionResponse
from sqlalchemy import text, desc
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

def check_request_ids():
    """최근 생성된 request_id들을 확인합니다"""
    print("=== STT 요청 ID 확인 ===")
    db = next(get_db())
    
    try:
        # 특정 request_id 확인
        target_request_id = "20250815-052931-485223f2"
        print(f"🔍 특정 Request ID '{target_request_id}' 확인:")
        
        target_request = db.query(TranscriptionRequest).filter(
            TranscriptionRequest.request_id == target_request_id
        ).first()
        
        if target_request:
            print(f"✅ 요청 발견:")
            print(f"  - Request ID: {target_request.request_id}")
            print(f"  - Filename: {target_request.filename}")
            print(f"  - Status: {target_request.status}")
            print(f"  - Created: {target_request.created_at}")
            # print(f"  - Updated: {target_request.updated_at}")  # updated_at 속성이 없음
            print(f"  - Response RID: {getattr(target_request, 'response_rid', 'N/A')}")
            
            # 해당 request_id에 대한 응답 확인
            target_response = db.query(TranscriptionResponse).filter(
                TranscriptionResponse.request_id == target_request_id
            ).first()
            
            if target_response:
                print(f"\n✅ 응답도 발견:")
                print(f"  - Response ID: {target_response.id}")
                print(f"  - Service Provider: {target_response.service_provider}")
                print(f"  - Created: {target_response.created_at}")
                print(f"  - Transcript ID: {getattr(target_response, 'transcript_id', 'N/A')}")
            else:
                print(f"\n❌ 해당 request_id에 대한 응답이 없습니다.")
                
                # response_rid가 있는지 확인
                if hasattr(target_request, 'response_rid') and target_request.response_rid:
                    print(f"\n🔍 Response RID '{target_request.response_rid}'가 있지만 해당 응답이 없습니다.")
                    print(f"  - 이는 응답 생성 과정에서 문제가 발생했음을 의미합니다.")
                    
                    # 최근 생성된 모든 응답 확인
                    print(f"\n📅 최근 1시간 내 생성된 모든 응답들:")
                    one_hour_ago = datetime.now() - timedelta(hours=1)
                    recent_responses = db.query(TranscriptionResponse).filter(
                        TranscriptionResponse.created_at >= one_hour_ago
                    ).order_by(TranscriptionResponse.created_at.desc()).all()
                    
                    if recent_responses:
                        for resp in recent_responses:
                            print(f"  - Response ID: {resp.id}, Request ID: {resp.request_id}")
                            print(f"    Service: {resp.service_provider}, Created: {resp.created_at}")
                            if resp.transcribed_text:
                                print(f"    Text Preview: {resp.transcribed_text[:50]}...")
                            print("    ---")
                    else:
                        print(f"  ❌ 최근 1시간 내 생성된 응답이 없습니다.")
                else:
                    print(f"\n❌ Response RID도 없습니다. 응답 생성이 전혀 시도되지 않았습니다.")
        else:
            print(f"❌ 해당 request_id를 찾을 수 없습니다.")
        
        # 1. 최근 24시간 내 transcription_requests 확인
        print("\n📋 최근 24시간 내 transcription_requests:")
        yesterday = datetime.now() - timedelta(days=1)
        
        recent_requests = db.query(TranscriptionRequest).filter(
            TranscriptionRequest.created_at >= yesterday
        ).order_by(desc(TranscriptionRequest.created_at)).limit(10).all()
        
        if recent_requests:
            for i, req in enumerate(recent_requests, 1):
                print(f"{i:2d}. request_id: {req.request_id}")
                print(f"    filename: {req.filename}")
                print(f"    status: {req.status}")
                print(f"    created_at: {req.created_at}")
                print(f"    user_uuid: {req.user_uuid}")
                print("    ---")
        else:
            print("    ❌ 최근 24시간 내 요청이 없습니다.")
        
        # Check all recent requests (last 10)
        print("\n=== Recent Transcription Requests (last 10) ===")
        all_recent_requests = db.query(TranscriptionRequest).order_by(TranscriptionRequest.created_at.desc()).limit(10).all()
        for req in all_recent_requests:
            print(f"Request ID: {req.request_id}, Status: {req.status}, Created: {req.created_at}, Filename: {req.filename}")

        print("\n=== Recent Transcription Responses (last 10) ===")
        all_recent_responses = db.query(TranscriptionResponse).order_by(TranscriptionResponse.created_at.desc()).limit(10).all()
        for resp in all_recent_responses:
            print(f"Response ID: {resp.id}, Request ID: {resp.request_id}, Created: {resp.created_at}, Service: {resp.service_provider}")
        
        # 2. 최근 24시간 내 transcription_responses 확인
        print("\n📊 최근 24시간 내 transcription_responses:")
        
        recent_responses = db.query(TranscriptionResponse).filter(
            TranscriptionResponse.created_at >= yesterday
        ).order_by(desc(TranscriptionResponse.created_at)).limit(10).all()
        
        if recent_responses:
            for i, resp in enumerate(recent_responses, 1):
                print(f"{i:2d}. id: {resp.id}")
                print(f"    request_id: {resp.request_id}")
                print(f"    service_provider: {resp.service_provider}")
                print(f"    created_at: {resp.created_at}")
                print(f"    transcribed_text: {resp.transcribed_text[:50] if resp.transcribed_text else 'None'}...")
                print("    ---")
        else:
            print("    ❌ 최근 24시간 내 응답이 없습니다.")
        
        # 3. 전체 테이블 레코드 수 확인
        print("\n📈 전체 테이블 레코드 수:")
        total_requests = db.query(TranscriptionRequest).count()
        total_responses = db.query(TranscriptionResponse).count()
        print(f"    transcription_requests: {total_requests}개")
        print(f"    transcription_responses: {total_responses}개")
        
        # 4. 매칭되지 않는 request_id 확인
        print("\n🔍 매칭되지 않는 request_id 확인:")
        
        # requests에는 있지만 responses에는 없는 경우
        unmatched_requests = db.execute(text("""
            SELECT tr.request_id, tr.filename, tr.status, tr.created_at
            FROM transcription_requests tr
            LEFT JOIN transcription_responses tres ON tr.request_id = tres.request_id
            WHERE tres.request_id IS NULL
            ORDER BY tr.created_at DESC
            LIMIT 10
        """)).fetchall()
        
        if unmatched_requests:
            print("    📋 응답이 없는 요청들:")
            for i, row in enumerate(unmatched_requests, 1):
                print(f"    {i:2d}. {row[0]} | {row[1]} | {row[2]} | {row[3]}")
        else:
            print("    ✅ 모든 요청에 응답이 있습니다.")
        
        # responses에는 있지만 requests에는 없는 경우
        orphaned_responses = db.execute(text("""
            SELECT tres.id, tres.request_id, tres.created_at
            FROM transcription_responses tres
            LEFT JOIN transcription_requests tr ON tres.request_id = tr.request_id
            WHERE tr.request_id IS NULL
            ORDER BY tres.created_at DESC
            LIMIT 10
        """)).fetchall()
        
        if orphaned_responses:
            print("    📊 요청이 없는 응답들:")
            for i, row in enumerate(orphaned_responses, 1):
                print(f"    {i:2d}. response_id: {row[0]} | request_id: {row[1]} | {row[2]}")
        else:
            print("    ✅ 모든 응답에 해당하는 요청이 있습니다.")
        
    except Exception as e:
        print(f"❌ 확인 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_request_ids()