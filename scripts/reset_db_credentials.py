import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

from bridge_app.database import get_db
from bridge_app.models import Credentials
from sqlalchemy import delete

# Load env to ensure DB connection works
load_dotenv()

async def reset_credentials():
    print("Resetting Credentials Table...")
    
    async for session in get_db():
        try:
            # Delete all rows from credentials table
            stmt = delete(Credentials)
            result = await session.execute(stmt)
            await session.commit()
            print(f"Success! Deleted {result.rowcount} credential records.")
        except Exception as e:
            print(f"Error resetting credentials: {e}")
            await session.rollback()
        break

if __name__ == "__main__":
    confirm = input("⚠️  Are you sure you want to DELETE ALL stored credentials from the database? (y/n): ")
    if confirm.lower() == 'y':
        asyncio.run(reset_credentials())
    else:
        print("Cancelled.")
