from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Text, Date, Float, Boolean, DateTime, UniqueConstraint, Integer,ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id          : Mapped[int]           = mapped_column(primary_key=True, autoincrement=True)
    source      : Mapped[str]           = mapped_column(String(50))
    job_url     : Mapped[str]           = mapped_column(String(768))
    title       : Mapped[str]           = mapped_column(String(500))
    company     : Mapped[Optional[str]] = mapped_column(String(500),  nullable=True)
    location    : Mapped[Optional[str]] = mapped_column(String(500),  nullable=True)
    is_remote   : Mapped[Optional[bool]]= mapped_column(Boolean,      nullable=True)
    job_type    : Mapped[Optional[str]] = mapped_column(String(100),  nullable=True)
    job_level   : Mapped[Optional[str]] = mapped_column(String(100),  nullable=True)
    date_posted : Mapped[Optional[date]]= mapped_column(Date, nullable=True)
    min_amount  : Mapped[Optional[float]]= mapped_column(Float,       nullable=True)
    max_amount  : Mapped[Optional[float]]= mapped_column(Float,       nullable=True)
    currency    : Mapped[Optional[str]] = mapped_column(String(10),   nullable=True)
    description : Mapped[Optional[str]] = mapped_column(Text,         nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (UniqueConstraint("job_url", name="uq_job_url"),)


# Needs to be implemented
# class User(Base):
#     pass


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)                       # 这边直接就用id来代替SessionID了,UUID的大小正好是36位
    title: Mapped[str] = mapped_column(String(36), nullable=True)
    message_json: Mapped[str] = mapped_column(Text(4294967295), nullable=True)          # MySQL LONGTEXT 这边后续应该是会要改的,改成存储在数据库的形式,Phase1保持简单功能完善为主
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


