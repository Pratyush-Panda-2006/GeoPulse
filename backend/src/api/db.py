import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = None
SessionLocal = None
Base = declarative_base()

def init_db():
    global engine, SessionLocal
    if engine is not None:
        return engine
        
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        return None
        
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        import src.api.models
        Base.metadata.create_all(engine)
        
        return engine
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def get_db():
    init_db()
    if not SessionLocal:
        raise Exception("Database is not configured. Missing DATABASE_URL.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
