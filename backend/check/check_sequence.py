from database import engine
from sqlalchemy import text

def check_sequence_status():
    conn = engine.connect()
    
    try:
        # 현재 시퀀스 값 확인
        result = conn.execute(text("""
            SELECT last_value, is_called 
            FROM transcription_responses_id_seq
        """))
        
        seq_info = result.fetchone()
        print(f"시퀀스 현재 값: {seq_info[0]}")
        print(f"시퀀스 호출됨: {seq_info[1]}")
        
        # 테이블의 최대 ID 확인
        result2 = conn.execute(text("""
            SELECT MAX(id) as max_id, COUNT(*) as total_count
            FROM transcription_responses
        """))
        
        table_info = result2.fetchone()
        print(f"테이블 최대 ID: {table_info[0]}")
        print(f"테이블 레코드 수: {table_info[1]}")
        
        # 시퀀스와 테이블 ID 불일치 확인
        if seq_info[0] <= table_info[0]:
            print("\n⚠️ 문제 발견: 시퀀스 값이 테이블 최대 ID보다 작거나 같습니다!")
            print("시퀀스를 재설정해야 합니다.")
            
            # 시퀀스 재설정
            new_seq_value = table_info[0] + 1
            conn.execute(text(f"""
                SELECT setval('transcription_responses_id_seq', {new_seq_value}, false)
            """))
            conn.commit()
            print(f"✅ 시퀀스를 {new_seq_value}로 재설정했습니다.")
        else:
            print("\n✅ 시퀀스 상태가 정상입니다.")
            
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_sequence_status()