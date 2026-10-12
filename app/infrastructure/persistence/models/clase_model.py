import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base


class ClaseModel(Base):
    __tablename__ = "clases"
    __table_args__ = (
        UniqueConstraint("ficha_id", "fecha", "hora", name="uq_clase_ficha_fecha_hora"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ficha_id: Mapped[str] = mapped_column(String(36), ForeignKey("fichas.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora: Mapped[str] = mapped_column(String(5), nullable=False)
    modalidad: Mapped[str] = mapped_column(String(20), default="PRESENCIAL", nullable=False)
    realizada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    observacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    ficha: Mapped["FichaModel"] = relationship(back_populates="clases")
    asistencias: Mapped[list["AsistenciaModel"]] = relationship(back_populates="clase", cascade="all, delete-orphan")
