from database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
print('transcription_requests 테이블 컬럼:')
for col in inspector.get_columns('transcription_requests'):
    print(f'  {col["name"]}: {col["type"]} - nullable: {col["nullable"]}')