import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base


class ActividadModel(Base):
    __tablename__ = "actividades"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ficha_id: Mapped[str] = mapped_column(String(36), ForeignKey("fichas.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("actividades.id", ondelete="CASCADE"), nullable=True, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_limite: Mapped[date | None] = mapped_column(Date, nullable=True)
    porcentaje: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    ficha: Mapped["FichaModel"] = relationship(back_populates="actividades")
    parent: Mapped["ActividadModel | None"] = relationship(remote_side="ActividadModel.id", back_populates="subactividades")
    subactividades: Mapped[list["ActividadModel"]] = relationship(back_populates="parent", cascade="all, delete-orphan")
    calificaciones: Mapped[list["CalificacionModel"]] = relationship(back_populates="actividad", cascade="all, delete-orphan")
