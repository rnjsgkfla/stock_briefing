from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))

    watchlist_items: Mapped[list[WatchlistItem]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Stock(TimestampMixin, Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    market: Mapped[str] = mapped_column(String(20), default="NASDAQ")
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    watchlist_items: Mapped[list[WatchlistItem]] = relationship(back_populates="stock")


class WatchlistItem(TimestampMixin, Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("user_id", "stock_id", name="uq_watchlist_user_stock"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"))

    user: Mapped[User] = relationship(back_populates="watchlist_items")
    stock: Mapped[Stock] = relationship(back_populates="watchlist_items", lazy="joined")
