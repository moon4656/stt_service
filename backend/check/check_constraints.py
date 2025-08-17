from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT conname, pg_get_constraintdef(oid) as definition FROM pg_constraint WHERE conrelid = (SELECT oid FROM pg_class WHERE relname = 'transcription_requests') AND contype = 'c';"))
    print('체크 제약 조건:')
    for row in result:
        print(f'  {row[0]}: {row[1]}')