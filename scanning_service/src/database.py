from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Get DB credentials from env (same names as backend docker-compose)
DB_ENGINE = os.getenv("DB_ENGINE", "mssql")
DB_NAME = os.getenv("DB_NAME", "texcore_db")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "StrongP@ssw0rd")
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "1433")
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

# Construct connection string
# mssql+pyodbc://sa:password@db:1433/texcore_db?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
SQLALCHEMY_DATABASE_URL = (
    f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?driver={DB_DRIVER.replace(' ', '+')}&TrustServerCertificate=yes"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
