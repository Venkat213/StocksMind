import database as db
import bcrypt
from sqlalchemy import text

def reset_password():
    username = "venky"
    new_password = "venky"
    
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    with db.engine.begin() as conn:
        result = conn.execute(
            text("UPDATE users SET password_hash = :hash WHERE username = :user"),
            {"hash": hashed, "user": username}
        )
        print(f"Password reset for '{username}'. Rows affected: {result.rowcount}")

if __name__ == "__main__":
    reset_password()
