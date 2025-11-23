import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def debug_db():
    print("--- Debugging DB Content ---")
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        
        print("\n[USERS]")
        cursor.execute("SELECT * FROM users")
        for r in cursor.fetchall():
            print(r)
            
        print("\n[WATCHLIST_NAMES]")
        cursor.execute("SELECT * FROM watchlist_names")
        for r in cursor.fetchall():
            print(r)

        print("\n[PORTFOLIO_NAMES]")
        cursor.execute("SELECT * FROM portfolio_names")
        for r in cursor.fetchall():
            print(r)
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_db()
