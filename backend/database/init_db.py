from backend.database.base import Base
from backend.database.session import engine

# Import database models so SQLAlchemy registers their tables.
from backend.models.user import User


def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database tables created successfully.")