import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base


class AsistenciaModel(Base):
    __tablename__ = "asistencias"
    __table_args__ = (
        UniqueConstraint("clase_id", "estudiante_id", name="uq_asistencia_clase_estudiante"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    clase_id: Mapped[str] = mapped_column(String(36), ForeignKey("clases.id", ondelete="CASCADE"), nullable=False, index=True)
    estudiante_id: Mapped[str] = mapped_column(String(36), ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    justificacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    clase: Mapped["ClaseModel"] = relationship(back_populates="asistencias")
    estudiante: Mapped["EstudianteModel"] = relationship(back_populates="asistencias")
