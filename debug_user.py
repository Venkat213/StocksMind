import mysql.connector
import os
from dotenv import load_dotenv
import datetime

load_dotenv()

def debug_user_data():
    print("--- Debugging User Data ---")
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor(dictionary=True)
        
        # 1. Get User ID for 'test'
        print("\n[Checking User 'test']")
        cursor.execute("SELECT * FROM users WHERE username = 'test'")
        user = cursor.fetchone()
        if not user:
            print("User 'test' not found!")
            return
        
        user_id = user['id']
        print(f"User found: {user}")
        
        # 2. Check Watchlists
        print(f"\n[Checking Watchlists for user_id={user_id}]")
        cursor.execute("SELECT * FROM watchlist_names WHERE user_id = %s", (user_id,))
        wls = cursor.fetchall()
        print(f"Watchlists found: {len(wls)}")
        for w in wls:
            print(w)
            
        # 3. Try Creating Default Watchlist if missing
        if not wls:
            print("\n[Attempting to create 'Default Watchlist']")
            try:
                cursor.execute("INSERT INTO watchlist_names (name, user_id, created_at) VALUES (%s, %s, %s)", 
                               ("Default Watchlist", user_id, datetime.datetime.now()))
                conn.commit()
                print("Success: Created Default Watchlist")
            except Exception as e:
                print(f"Error creating watchlist: {e}")

        # 4. Check Portfolios
        print(f"\n[Checking Portfolios for user_id={user_id}]")
        cursor.execute("SELECT * FROM portfolio_names WHERE user_id = %s", (user_id,))
        pfs = cursor.fetchall()
        print(f"Portfolios found: {len(pfs)}")
        for p in pfs:
            print(p)

        if not pfs:
            print("\n[Attempting to create 'Default Portfolio']")
            try:
                cursor.execute("INSERT INTO portfolio_names (name, user_id, created_at) VALUES (%s, %s, %s)", 
                               ("Default Portfolio", user_id, datetime.datetime.now()))
                conn.commit()
                print("Success: Created Default Portfolio")
            except Exception as e:
                print(f"Error creating portfolio: {e}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    debug_user_data()
