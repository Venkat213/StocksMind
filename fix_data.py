import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def fix_orphans():
    print("Fixing orphan data...")
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()
        
        # Assign NULL user_id records to user 1
        print("Updating watchlists...")
        cursor.execute("UPDATE watchlist_names SET user_id = 1 WHERE user_id IS NULL")
        
        print("Updating portfolios...")
        cursor.execute("UPDATE portfolio_names SET user_id = 1 WHERE user_id IS NULL")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_orphans()
