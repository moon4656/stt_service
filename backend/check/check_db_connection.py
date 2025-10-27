import asyncpg
import asyncio

async def test_connection():
    try:
        conn = await asyncpg.connect(
            host='192.168.0.105',
            port=5432,
            user='postgres',
            password='hibiznet',
            database='SKYBOOT.STT'
        )
        
        # 테이블 목록 조회
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        
        print("연결 성공! 테이블 목록:")
        for table in tables:
            print(f"- {table['table_name']}")
            
        await conn.close()
        
    except Exception as e:
        print(f"연결 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())