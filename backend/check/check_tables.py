import sqlite3

def check_tables():
    """데이터베이스 테이블 목록 확인"""
    conn = sqlite3.connect('stt_service.db')
    cursor = conn.cursor()
    
    print("📊 데이터베이스 테이블 목록")
    print("=" * 40)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table in tables:
        print(f"- {table[0]}")
    
    conn.close()

if __name__ == "__main__":
    check_tables()