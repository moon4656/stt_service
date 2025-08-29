#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국어 논리명 주석 확인 스크립트

이 스크립트는 데이터베이스의 모든 테이블과 컬럼에 한국어 주석이 
올바르게 추가되었는지 확인합니다.
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# 환경 변수에서 데이터베이스 연결 정보 가져오기
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:1234@localhost:5432/stt_service"
)

def verify_korean_comments():
    """
    데이터베이스의 모든 테이블과 컬럼에 한국어 주석이 추가되었는지 확인합니다.
    """
    print("🚀 한국어 논리명 주석 확인 스크립트 시작")
    print("🔍 데이터베이스 테이블과 컬럼 주석 확인 중...")
    print("=" * 80)
    
    try:
        # 데이터베이스 연결 (인코딩 문제 우회)
        engine = create_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True
        )
        
        # Inspector를 사용하여 메타데이터 조회
        inspector = inspect(engine)
        
        # 모든 테이블 목록 가져오기
        table_names = inspector.get_table_names()
        
        print(f"📋 발견된 테이블 수: {len(table_names)}")
        print("\n📊 테이블별 컬럼 정보:")
        
        total_tables = len(table_names)
        total_columns = 0
        tables_with_comments = 0
        columns_with_comments = 0
        
        for table_name in sorted(table_names):
            print(f"\n  📋 테이블: {table_name}")
            
            try:
                # 테이블의 컬럼 정보 가져오기
                columns = inspector.get_columns(table_name)
                total_columns += len(columns)
                
                table_has_comment = False
                
                for column in columns:
                    column_name = column['name']
                    column_type = str(column['type'])
                    comment = column.get('comment', '')
                    
                    if comment:
                        print(f"    ✅ {column_name} ({column_type}): {comment}")
                        columns_with_comments += 1
                        table_has_comment = True
                    else:
                        print(f"    ❌ {column_name} ({column_type}): 주석 없음")
                
                if table_has_comment:
                    tables_with_comments += 1
                    
            except Exception as e:
                print(f"    ⚠️ 테이블 {table_name} 조회 중 오류: {str(e)}")
        
        # 결과 요약
        print("\n" + "=" * 80)
        print("📊 검증 결과 요약:")
        print(f"  • 전체 테이블 수: {total_tables}")
        print(f"  • 주석이 있는 테이블 수: {tables_with_comments}")
        print(f"  • 전체 컬럼 수: {total_columns}")
        print(f"  • 주석이 있는 컬럼 수: {columns_with_comments}")
        
        if total_columns > 0:
            coverage = (columns_with_comments / total_columns) * 100
            print(f"  • 컬럼 주석 적용률: {coverage:.1f}%")
        
        if columns_with_comments == total_columns and total_columns > 0:
            print("\n🎉 모든 컬럼에 한국어 주석이 성공적으로 추가되었습니다!")
            return True
        elif columns_with_comments > 0:
            missing_comments = total_columns - columns_with_comments
            print(f"\n⚠️ {missing_comments}개 컬럼에 주석이 누락되었습니다.")
            return False
        else:
            print("\n❌ 주석이 추가된 컬럼이 없습니다.")
            return False
            
    except SQLAlchemyError as e:
        print(f"❌ 데이터베이스 오류: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        return False

if __name__ == "__main__":
    success = verify_korean_comments()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ 검증 성공")
        sys.exit(0)
    else:
        print("❌ 검증 실패")
        sys.exit(1)