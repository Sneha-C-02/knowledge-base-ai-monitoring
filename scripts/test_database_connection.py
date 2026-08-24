import asyncio
import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()

async def test_connection():
    try:
        import asyncpg
    except ImportError:
        print("asyncpg is not installed. Please install it.")
        sys.exit(1)
        
    db_url = os.environ.get("DATABASE_CONNECTION_URL")
    if not db_url:
        print("DATABASE_CONNECTION_URL is not set in .env")
        sys.exit(1)
        
    # asyncpg expects postgres:// or postgresql://, not postgresql+asyncpg:// for direct connection
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        
    print(f"Attempting to connect to: {db_url.split('@')[-1]}")
    
    try:
        # connect
        conn = await asyncpg.connect(db_url)
        print("Successfully connected to the database!")
        
        # Test query
        version = await conn.fetchval('SELECT version();')
        print(f"Database version: {version}")
        
        await conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_connection())
