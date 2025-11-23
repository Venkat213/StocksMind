import database as db
import os
from sqlalchemy import text

print("Initializing Cloud Database...")
print(f"Target: {os.getenv('DATABASE_URL').split('@')[1] if '@' in os.getenv('DATABASE_URL') else 'Local'}")

try:
    # Create tables
    db.init_db()
    print("[SUCCESS] Database tables created successfully!")
    
    # Verify connection
    with db.engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("[SUCCESS] Connection verified!")
        
except Exception as e:
    print(f"[ERROR] Error initializing database: {e}")
