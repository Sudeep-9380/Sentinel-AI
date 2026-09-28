import asyncio
import sys
import os

# Add the parent directory to sys.path so 'app' can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AsyncSessionFactory
from sqlalchemy import text

async def main():
    try:
        async with AsyncSessionFactory() as session:
            # TRUNCATE TABLE is the postgresql command to empty a table
            await session.execute(text("TRUNCATE TABLE incidents CASCADE;"))
            await session.commit()
            print("Successfully truncated the incident table.")
    except Exception as e:
        print(f"Error truncating incident table: {e}")

if __name__ == "__main__":
    asyncio.run(main())
