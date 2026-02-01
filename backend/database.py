from sqlmodel import SQLModel, create_engine, Session
from backend.core.config import settings

sqlite_url = settings.SQLALCHEMY_DATABASE_URI

# check_same_thread=False 是 SQLite 在多线程环境(FastAPI)下的必要配置
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session