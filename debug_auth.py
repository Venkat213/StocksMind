import database as db
import bcrypt
from sqlalchemy import text

def debug_auth():
    print("--- Debugging Auth ---")
    
    # 1. List all users
    with db.engine.connect() as conn:
        users = conn.execute(text("SELECT id, username, mobile_number, password_hash FROM users")).mappings().fetchall()
        
    print(f"Found {len(users)} users:")
    for u in users:
        print(f"ID: {u['id']}, User: {u['username']}, Mobile: {u['mobile_number']}, Hash: {u['password_hash']}")
        
        # Check specific mobile
        if u['mobile_number'] == '9655967501':
            print(f"\n--- DIAGNOSIS FOR 9655967501 ---")
            if not u['password_hash']:
                print("ISSUE: User has NO PASSWORD set (likely created via OTP only).")
            else:
                test_pass = "venky"
                is_match = bcrypt.checkpw(test_pass.encode('utf-8'), u['password_hash'].encode('utf-8'))
                print(f"Has Password Hash: Yes")
                print(f"Does password 'venky' match? {is_match}")

    # 2. Test Bcrypt Mechanism
    print("\n--- Testing Bcrypt Mechanism ---")
    password = "testpassword"
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    print(f"Generated Hash: {hashed}")
    
    check = bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    print(f"Verification Result: {check}")

if __name__ == "__main__":
    debug_auth()
