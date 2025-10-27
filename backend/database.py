from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- IMPORTANT ---
# Replace 'YOUR_POSTGRES_PASSWORD' with the password you set during installation.
# The format is: "postgresql://<user>:<password>@<host>/<database_name>"
DATABASE_URL = "postgresql://postgres:neoaspect777@localhost/courtready_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
