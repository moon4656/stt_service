import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from sqlalchemy import text

def check_transcription_responses():
    db = next(get_db())
    
    # 테이블 레코드 수 확인
    result = db.execute(text('SELECT COUNT(*) FROM transcription_responses'))
    count = result.scalar()
    print(f'transcription_responses 테이블 레코드 수: {count}')
    
    # 최근 5개 레코드의 새 컬럼들 확인
    result2 = db.execute(text('SELECT id, service_provider, audio_duration_minutes, tokens_used FROM transcription_responses ORDER BY id DESC LIMIT 5'))
    rows = result2.fetchall()
    
    print('\n최근 5개 레코드의 새 컬럼들:')
    for row in rows:
        print(f'ID: {row[0]}, service_provider: {row[1]}, audio_duration_minutes: {row[2]}, tokens_used: {row[3]}')
    
    db.close()

if __name__ == '__main__':
    check_transcription_responses()