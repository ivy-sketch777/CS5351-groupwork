from sqlalchemy import Column, Date, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./medleave.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class CaseDB(Base):
    __tablename__ = "cases"

    case_id = Column(String, primary_key=True, index=True)
    student_id = Column(String, nullable=False)
    course_id = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason_text = Column(Text, nullable=False)
    attachment_url = Column(String, nullable=True)
    status = Column(String, nullable=False, default="draft")
    decision_reason = Column(Text, nullable=True)
    extraction_json = Column(Text, nullable=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
