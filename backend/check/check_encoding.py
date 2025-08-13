from database import engine
from sqlalchemy import text
import json

# response_data의 인코딩 상태 확인
with engine.connect() as conn:
    result = conn.execute(text('SELECT id, response_data FROM transcription_responses ORDER BY id DESC LIMIT 3'))
    
    for row in result:
        print(f"ID: {row[0]}")
        print(f"Raw response_data: {row[1][:200]}...")
        
        # JSON 파싱 시도
        try:
            parsed_data = json.loads(row[1])
            print(f"Parsed transcription: {parsed_data.get('transcription', '')[:100]}...")
        except Exception as e:
            print(f"JSON 파싱 오류: {e}")
        
        print("-" * 50)