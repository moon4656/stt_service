from database import engine
from sqlalchemy import text

print("=== 최신 3개 레코드 확인 ===")
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT id, audio_duration_minutes, tokens_used, duration, service_provider, created_at 
        FROM transcription_responses 
        ORDER BY id DESC 
        LIMIT 3
    '''))
    
    for row in result:
        print(f"ID: {row[0]}")
        print(f"  audio_duration_minutes: {row[1]}")
        print(f"  tokens_used: {row[2]}")
        print(f"  duration: {row[3]}")
        print(f"  service_provider: {row[4]}")
        print(f"  created_at: {row[5]}")
        print("-" * 40)