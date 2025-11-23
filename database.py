import os
# from dotenv import load_dotenv # Removed to avoid UnicodeDecodeError
from datetime import datetime
import bcrypt
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, DECIMAL

# load_dotenv() # Replaced with robust loader below

def load_config():
    """Manually load .env file with encoding fallback"""
    env_path = ".env"
    if not os.path.exists(env_path):
        return

    content = None
    # Try UTF-8 first
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        # Fallback to UTF-16 (PowerShell default)
        try:
            with open(env_path, "r", encoding="utf-16") as f:
                content = f.read()
        except Exception:
            pass
            
    if content:
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

load_config()

# Database Configuration
# Database Configuration
# Priority: st.secrets (Cloud) > DATABASE_URL (Env) > Local SQLite
import streamlit as st

DATABASE_URL = None

# Check Streamlit secrets first (for Cloud)
if hasattr(st, "secrets") and "DATABASE_URL" in st.secrets:
    DATABASE_URL = st.secrets["DATABASE_URL"]

# Check Environment variable
if not DATABASE_URL:
    DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback to local SQLite
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///stock_market.db"
elif DATABASE_URL.startswith("postgres://"):
    # Fix for SQLAlchemy expecting postgresql://
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
metadata = MetaData()

# --- Table Definitions (SQLAlchemy Core) ---
# --- Table Definitions (SQLAlchemy Core) ---
users = Table('users', metadata,
    Column('id', Integer, primary_key=True),
    Column('username', String(50), unique=True, nullable=True),
    Column('password_hash', String(255), nullable=True),
    Column('mobile_number', String(15), unique=True, nullable=True),
    Column('created_at', DateTime)
)

watchlist_names = Table('watchlist_names', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE')),
    Column('name', String(50)),
    Column('created_at', DateTime),
    UniqueConstraint('user_id', 'name', name='unique_wl_name')
)

watchlist_items = Table('watchlist_items', metadata,
    Column('id', Integer, primary_key=True),
    Column('watchlist_id', Integer, ForeignKey('watchlist_names.id', ondelete='CASCADE')),
    Column('symbol', String(20)),
    Column('added_at', DateTime),
    UniqueConstraint('watchlist_id', 'symbol', name='unique_stock')
)

portfolio_names = Table('portfolio_names', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE')),
    Column('name', String(50)),
    Column('created_at', DateTime),
    UniqueConstraint('user_id', 'name', name='unique_pf_name')
)

portfolio_holdings = Table('portfolio_holdings', metadata,
    Column('id', Integer, primary_key=True),
    Column('portfolio_id', Integer, ForeignKey('portfolio_names.id', ondelete='CASCADE')),
    Column('symbol', String(20)),
    Column('quantity', Integer),
    Column('avg_price', DECIMAL(10, 2)),
    UniqueConstraint('portfolio_id', 'symbol', name='unique_holding')
)

transactions = Table('transactions', metadata,
    Column('id', Integer, primary_key=True),
    Column('portfolio_id', Integer, ForeignKey('portfolio_names.id', ondelete='CASCADE')),
    Column('symbol', String(20)),
    Column('type', String(10)),
    Column('quantity', Integer),
    Column('price', DECIMAL(10, 2)),
    Column('date', DateTime)
)

def get_connection():
    return engine.connect()

def init_db():
    try:
        metadata.create_all(engine)
        print("Database initialized successfully.")
    except Exception as e:
        print(f"DB Init Error: {e}")

# --- Auth Functions ---

# 1. Username/Password Auth
# 1. Username/Password Auth
def register_user(username, password, mobile):
    try:
        # Check for existing user
        with engine.connect() as conn:
            existing = conn.execute(
                text("SELECT username, mobile_number FROM users WHERE username = :u OR mobile_number = :m"),
                {"u": username, "m": mobile}
            ).fetchone()
            
        if existing:
            if existing.username == username:
                return False, "Username already taken. Please choose another."
            if existing.mobile_number == mobile:
                return False, "Mobile number already registered. Please login."

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users (username, password_hash, mobile_number, created_at) VALUES (:username, :password_hash, :mobile, :created_at)"),
                {"username": username, "password_hash": hashed, "mobile": mobile, "created_at": datetime.now()}
            )
        return True, "User created successfully!"
    except Exception as e:
        return False, f"Error: {str(e)}"

def login_user(identifier, password):
    """Login with Username OR Mobile Number"""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM users WHERE username = :identifier OR mobile_number = :identifier"),
            {"identifier": identifier}
        ).mappings().fetchone()
    
    if result and result['password_hash']:
        if bcrypt.checkpw(password.encode('utf-8'), result['password_hash'].encode('utf-8')):
            return dict(result)
            
    return None

# 2. Mobile OTP Auth
def get_user_by_mobile(mobile):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM users WHERE mobile_number = :mobile"),
            {"mobile": mobile}
        ).mappings().fetchone()
    return dict(result) if result else None

def create_user_by_mobile(mobile):
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users (mobile_number, created_at) VALUES (:mobile, :created_at)"),
                {"mobile": mobile, "created_at": datetime.now()}
            )
        return True, "User created successfully!"
    except Exception as e:
        return False, f"Error: {str(e)}"

# --- Watchlist Management ---
def get_watchlists(user_id):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM watchlist_names WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).mappings().fetchall()
    return [dict(row) for row in result]

def create_watchlist(name, user_id):
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO watchlist_names (name, user_id, created_at) VALUES (:name, :user_id, :created_at)"),
                {"name": name, "user_id": user_id, "created_at": datetime.now()}
            )
        return True
    except:
        return False

def delete_watchlist(watchlist_id):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM watchlist_names WHERE id = :id"),
            {"id": watchlist_id}
        )

def get_watchlist_items(watchlist_id):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT symbol FROM watchlist_items WHERE watchlist_id = :watchlist_id"),
            {"watchlist_id": watchlist_id}
        ).fetchall()
    return [row[0] for row in result]

def add_to_watchlist(watchlist_id, symbol):
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO watchlist_items (watchlist_id, symbol, added_at) VALUES (:watchlist_id, :symbol, :added_at)"),
                {"watchlist_id": watchlist_id, "symbol": symbol, "added_at": datetime.now()}
            )
        return True
    except:
        return False

def remove_from_watchlist(watchlist_id, symbol):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM watchlist_items WHERE watchlist_id = :watchlist_id AND symbol = :symbol"),
            {"watchlist_id": watchlist_id, "symbol": symbol}
        )

# --- Portfolio Management ---
def get_portfolios(user_id):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM portfolio_names WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).mappings().fetchall()
    return [dict(row) for row in result]

def create_portfolio(name, user_id):
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO portfolio_names (name, user_id, created_at) VALUES (:name, :user_id, :created_at)"),
                {"name": name, "user_id": user_id, "created_at": datetime.now()}
            )
        return True
    except:
        return False

def delete_portfolio(portfolio_id):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM portfolio_names WHERE id = :id"),
            {"id": portfolio_id}
        )

def get_portfolio_holdings(portfolio_id):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT symbol, quantity, avg_price FROM portfolio_holdings WHERE portfolio_id = :portfolio_id"),
            {"portfolio_id": portfolio_id}
        ).mappings().fetchall()
    return [dict(row) for row in result]

def update_portfolio_holding(portfolio_id, symbol, quantity, avg_price):
    with engine.begin() as conn:
        if quantity <= 0:
            conn.execute(
                text("DELETE FROM portfolio_holdings WHERE portfolio_id = :portfolio_id AND symbol = :symbol"),
                {"portfolio_id": portfolio_id, "symbol": symbol}
            )
        else:
            # Check if exists to decide INSERT or UPDATE (SQLite doesn't support ON DUPLICATE KEY UPDATE same as MySQL)
            # Using a simple check-then-act approach for broad compatibility
            existing = conn.execute(
                text("SELECT 1 FROM portfolio_holdings WHERE portfolio_id = :portfolio_id AND symbol = :symbol"),
                {"portfolio_id": portfolio_id, "symbol": symbol}
            ).fetchone()
            
            if existing:
                conn.execute(
                    text("UPDATE portfolio_holdings SET quantity = :quantity, avg_price = :avg_price WHERE portfolio_id = :portfolio_id AND symbol = :symbol"),
                    {"quantity": quantity, "avg_price": avg_price, "portfolio_id": portfolio_id, "symbol": symbol}
                )
            else:
                conn.execute(
                    text("INSERT INTO portfolio_holdings (portfolio_id, symbol, quantity, avg_price) VALUES (:portfolio_id, :symbol, :quantity, :avg_price)"),
                    {"portfolio_id": portfolio_id, "symbol": symbol, "quantity": quantity, "avg_price": avg_price}
                )

# --- Transaction Operations ---
def add_transaction(portfolio_id, symbol, type, quantity, price, date):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO transactions (portfolio_id, symbol, type, quantity, price, date) VALUES (:portfolio_id, :symbol, :type, :quantity, :price, :date)"),
            {"portfolio_id": portfolio_id, "symbol": symbol, "type": type, "quantity": quantity, "price": price, "date": date}
        )

def get_transactions(portfolio_id=None, limit=50):
    with engine.connect() as conn:
        if portfolio_id:
            result = conn.execute(
                text("SELECT * FROM transactions WHERE portfolio_id = :portfolio_id ORDER BY date DESC LIMIT :limit"),
                {"portfolio_id": portfolio_id, "limit": limit}
            ).mappings().fetchall()
        else:
            result = conn.execute(
                text("SELECT * FROM transactions ORDER BY date DESC LIMIT :limit"),
                {"limit": limit}
            ).mappings().fetchall()
    return [dict(row) for row in result]
