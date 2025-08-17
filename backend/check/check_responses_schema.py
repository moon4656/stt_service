from sqlalchemy import inspect
from database import engine

def check_responses_schema():
    inspector = inspect(engine)
    
    # transcription_responses 테이블 스키마 확인
    print("transcription_responses 테이블 컬럼:")
    columns = inspector.get_columns('transcription_responses')
    for column in columns:
        print(f"  {column['name']}: {column['type']} - nullable: {column['nullable']}")

if __name__ == "__main__":
    check_responses_schema()