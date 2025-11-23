import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def fix_schema():
    print("Fixing schema constraints...")
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()
        
        # 1. Fix Watchlist Names
        print("Dropping unique constraint on watchlist_names.name...")
        try:
            # Try dropping the index named 'name' (default for inline unique)
            cursor.execute("ALTER TABLE watchlist_names DROP INDEX name")
            print("Dropped index 'name'.")
        except Exception as e:
            print(f"Could not drop index 'name': {e}")
            
        # 2. Fix Portfolio Names
        print("Dropping unique constraint on portfolio_names.name...")
        try:
            cursor.execute("ALTER TABLE portfolio_names DROP INDEX name")
            print("Dropped index 'name'.")
        except Exception as e:
            print(f"Could not drop index 'name': {e}")

        conn.commit()
        cursor.close()
        conn.close()
        print("Schema fix complete.")
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    fix_schema()
