from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:password@localhost:3306/auth_py"
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:password@host.docker.internal:3306/auth_py"


engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()