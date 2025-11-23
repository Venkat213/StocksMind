import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    print("Starting migration...")
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()
        
        # Add user_id to watchlist_names
        try:
            print("Adding user_id to watchlist_names...")
            cursor.execute("ALTER TABLE watchlist_names ADD COLUMN user_id INT")
            cursor.execute("ALTER TABLE watchlist_names ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
            cursor.execute("ALTER TABLE watchlist_names ADD UNIQUE KEY unique_wl_name (user_id, name)")
            print("Success.")
        except Exception as e:
            print(f"Watchlist migration note: {e}")

        # Add user_id to portfolio_names
        try:
            print("Adding user_id to portfolio_names...")
            cursor.execute("ALTER TABLE portfolio_names ADD COLUMN user_id INT")
            cursor.execute("ALTER TABLE portfolio_names ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
            cursor.execute("ALTER TABLE portfolio_names ADD UNIQUE KEY unique_pf_name (user_id, name)")
            print("Success.")
        except Exception as e:
            print(f"Portfolio migration note: {e}")
            
        conn.commit()
        cursor.close()
        conn.close()
        print("Migration complete.")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    migrate()
