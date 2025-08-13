from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        result = conn.execute(text('SELECT * FROM alembic_version'))
        rows = list(result)
        print(f"Current alembic version: {rows}")
    except Exception as e:
        print(f"Error: {e}")
        
    # Update to correct version
    try:
        conn.execute(text("UPDATE alembic_version SET version_num = '7cf574be5041'"))
        conn.commit()
        print("Updated alembic version to 7cf574be5041")
    except Exception as e:
        print(f"Update error: {e}")