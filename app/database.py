from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# Use /tmp for Render's ephemeral filesystem
# For local development it still creates jobscribe.db in project root
if os.getenv("RENDER"):
    DATABASE_PATH = "/tmp/jobscribe.db"
else:
    DATABASE_PATH = "./jobscribe.db"

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
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
    """
    Checks for missing columns and adds them automatically.
    This runs on every startup — safe to call multiple times.
    Handles the case where old V1 database exists on Render.
    """
    import sqlite3

    # Get the actual database file path
    db_path = DATABASE_PATH

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get existing columns in jobs table
    cursor.execute("PRAGMA table_info(jobs)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    # Add readiness_score if missing
    if "readiness_score" not in existing_columns:
        cursor.execute(
            "ALTER TABLE jobs ADD COLUMN readiness_score INTEGER"
        )
        print("Migration: added readiness_score column to jobs table")

    conn.commit()
    conn.close()