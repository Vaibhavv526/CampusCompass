import backend.models

from backend.database.base import Base
from backend.database.session import engine


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


if __name__ == "__main__":
    init_db()