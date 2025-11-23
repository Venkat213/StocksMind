import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

print(f"Attempting to connect to:")
print(f"Host: {os.getenv('DB_HOST')}")
print(f"User: {os.getenv('DB_USER')}")
print(f"Database: {os.getenv('DB_NAME')}")

try:
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    print("SUCCESS: Connection established!")
    conn.close()
except mysql.connector.Error as err:
    print(f"ERROR: {err}")
except Exception as e:
    print(f"EXCEPTION: {e}")
