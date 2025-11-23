import database as db
import bcrypt
from sqlalchemy import text
from datetime import datetime

def create_test_user():
    username = "venky"
    password = "venky"
    mobile = "9655967501"
    
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    try:
        with db.engine.begin() as conn:
            # Check if exists first
            existing = conn.execute(text("SELECT * FROM users WHERE username = :u OR mobile_number = :m"), {"u": username, "m": mobile}).fetchone()
            if existing:
                print("User already exists. Updating password...")
                conn.execute(
                    text("UPDATE users SET password_hash = :h, mobile_number = :m WHERE username = :u"),
                    {"h": hashed, "m": mobile, "u": username}
                )
            else:
                print("Creating new user...")
                conn.execute(
                    text("INSERT INTO users (username, password_hash, mobile_number, created_at) VALUES (:u, :h, :m, :d)"),
                    {"u": username, "h": hashed, "m": mobile, "d": datetime.now()}
                )
        print("User 'venky' created/updated successfully!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_test_user()
