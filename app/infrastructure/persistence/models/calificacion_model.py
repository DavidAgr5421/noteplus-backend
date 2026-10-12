import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base


class CalificacionModel(Base):
    __tablename__ = "calificaciones"
    __table_args__ = (
        UniqueConstraint("actividad_id", "estudiante_id", name="uq_calificacion_actividad_estudiante"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actividad_id: Mapped[str] = mapped_column(String(36), ForeignKey("actividades.id", ondelete="CASCADE"), nullable=False, index=True)
    estudiante_id: Mapped[str] = mapped_column(String(36), ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False, index=True)
    nota: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    actividad: Mapped["ActividadModel"] = relationship(back_populates="calificaciones")
    estudiante: Mapped["EstudianteModel"] = relationship(back_populates="calificaciones")
