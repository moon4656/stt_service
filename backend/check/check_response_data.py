from database import engine
from sqlalchemy import text

# 현재 테이블 구조 확인
with engine.connect() as conn:
    # 모든 컬럼 정보 확인
    columns_result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'transcription_responses' ORDER BY ordinal_position"))
    print('transcription_responses 테이블의 모든 컬럼들:')
    columns = []
    for col in columns_result:
        columns.append(col[0])
        print(f'- {col[0]}')
    
    # 전체 레코드 수와 response_data 데이터 확인
    result = conn.execute(text('SELECT COUNT(*) as total, COUNT(response_data) as with_data FROM transcription_responses'))
    row = result.fetchone()
    print(f'\n전체 레코드: {row[0]}, response_data가 있는 레코드: {row[1]}')
    
    # 기본 컬럼들만으로 최근 레코드 확인
    recent_result = conn.execute(text('SELECT id, response_data FROM transcription_responses ORDER BY id DESC LIMIT 3'))
    print('\n최근 3개 레코드의 response_data 상태:')
    for sample_row in recent_result:
        data_preview = sample_row[1][:50] if sample_row[1] else 'NULL'
        print(f'ID: {sample_row[0]}, response_data: {data_preview}...')