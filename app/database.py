import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Use DATABASE_URL from environment if available (Neon on Render)
# Fall back to local SQLite for development
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Neon PostgreSQL on Render
    engine = create_engine(DATABASE_URL)
    DATABASE_PATH = None
else:
    # Local SQLite for development
    DATABASE_PATH = "./jobscribe.db"
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def run_migrations():
    """Only runs for SQLite local development."""
    if DATABASE_PATH is None:
        return  # PostgreSQL handles schema automatically

    import sqlite3
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(jobs)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    if "readiness_score" not in existing_columns:
        cursor.execute("ALTER TABLE jobs ADD COLUMN readiness_score INTEGER")
    conn.commit()
    conn.close()