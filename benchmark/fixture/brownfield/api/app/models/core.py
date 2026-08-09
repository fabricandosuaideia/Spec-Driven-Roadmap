from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


class Agenda(Base):
    __tablename__ = "agendas"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int]
    title: Mapped[str]
    state: Mapped[str] = mapped_column(default="draft")
    meets_at: Mapped[datetime]


class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    agenda_id: Mapped[int]
    author_id: Mapped[int]
    title: Mapped[str]
    minutes: Mapped[int] = mapped_column(default=10)
