# src/database/models.py
import datetime
from sqlalchemy import String, func, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Video(Base):
    __tablename__ = "videos_to_watch"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500)) # (Мы можем добавить заголовок позже)

    status: Mapped[str] = mapped_column(String(50), default="unwatched") # unwatched, watched, deleted

    added_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"Video(id={self.id!r}, url={self.url!r}, status={self.status!r})"


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(primary_key=True)
    credentials_json: Mapped[str | None] = mapped_column(String, nullable=True)

    def __repr__(self) -> str:
        return f"User(telegram_id={self.telegram_id!r})"
