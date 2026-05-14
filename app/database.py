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