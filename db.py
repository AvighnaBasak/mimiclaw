import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Text, Integer, Date, DateTime, ForeignKey, String
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "mimiclaw.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Text, primary_key=True)
    course_id = Column(Text)
    course_name = Column(Text)
    title = Column(Text)
    description = Column(Text)
    due_date = Column(Date, nullable=True)
    status = Column(Text, default="pending")
    drive_folder_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_pinged_at = Column(DateTime, nullable=True)
    files = relationship("CompletedFile", back_populates="assignment")


class CompletedFile(Base):
    __tablename__ = "completed_files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Text, ForeignKey("assignments.id"))
    filename = Column(Text)
    drive_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    assignment = relationship("Assignment", back_populates="files")


class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(Text)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()


def insert_assignment(session, data: dict):
    a = Assignment(**data)
    session.add(a)
    session.commit()
    return a


def get_assignment(session, assignment_id: str):
    return session.query(Assignment).filter_by(id=assignment_id).first()


def update_assignment_status(session, assignment_id: str, status: str, **kwargs):
    a = session.query(Assignment).filter_by(id=assignment_id).first()
    if a:
        a.status = status
        for k, v in kwargs.items():
            setattr(a, k, v)
        session.commit()
    return a


def add_completed_file(session, assignment_id: str, filename: str, drive_url: str):
    f = CompletedFile(assignment_id=assignment_id, filename=filename, drive_url=drive_url)
    session.add(f)
    session.commit()
    return f


def get_pending_assignments(session):
    return (
        session.query(Assignment)
        .filter(Assignment.status.in_(["pending", "notified"]))
        .order_by(Assignment.due_date)
        .all()
    )


def get_all_assignments(session):
    return session.query(Assignment).order_by(Assignment.created_at.desc()).all()


def get_completed_assignments(session, limit=10):
    return (
        session.query(Assignment)
        .filter_by(status="completed")
        .order_by(Assignment.created_at.desc())
        .limit(limit)
        .all()
    )


def get_recent_files(session, limit=5):
    return (
        session.query(CompletedFile)
        .order_by(CompletedFile.created_at.desc())
        .limit(limit)
        .all()
    )


def add_reminder(session, text: str):
    r = Reminder(text=text)
    session.add(r)
    session.commit()
    return r


def get_reminders(session):
    return session.query(Reminder).order_by(Reminder.created_at.desc()).all()


def add_chat_message(session, role: str, content: str):
    m = ChatHistory(role=role, content=content)
    session.add(m)
    session.commit()
    return m


def get_chat_history(session, limit=10):
    rows = (
        session.query(ChatHistory)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))


def assignment_id_exists(session, assignment_id: str) -> bool:
    return session.query(Assignment).filter_by(id=assignment_id).count() > 0
