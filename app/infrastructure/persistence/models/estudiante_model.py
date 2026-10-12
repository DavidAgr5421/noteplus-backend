import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base


class EstudianteModel(Base):
    __tablename__ = "estudiantes"
    __table_args__ = (
        UniqueConstraint("ficha_id", "identificacion", name="uq_estudiante_ficha_identificacion"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ficha_id: Mapped[str] = mapped_column(String(36), ForeignKey("fichas.id", ondelete="CASCADE"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    identificacion: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo_identificacion: Mapped[str] = mapped_column(String(10), nullable=False, default="CC", server_default="CC")
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    contacto: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    ficha: Mapped["FichaModel"] = relationship(back_populates="estudiantes")
    asistencias: Mapped[list["AsistenciaModel"]] = relationship(back_populates="estudiante", cascade="all, delete-orphan")
    calificaciones: Mapped[list["CalificacionModel"]] = relationship(back_populates="estudiante", cascade="all, delete-orphan")
