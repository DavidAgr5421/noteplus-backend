import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base


class FichaModel(Base):
    __tablename__ = "fichas"
    __table_args__ = (
        UniqueConstraint("instructor_id", "codigo", "fecha_inicio", name="uq_ficha_instructor_codigo_fecha"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    instructor_id: Mapped[str] = mapped_column(String(36), ForeignKey("instructores.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    trimestre: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    total_clases: Mapped[int] = mapped_column(Integer, nullable=False)
    nota_minima_aprobacion: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)
    archivada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    finalizada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    instructor: Mapped["InstructorModel"] = relationship(back_populates="fichas")
    horarios: Mapped[list["HorarioFichaModel"]] = relationship(back_populates="ficha", cascade="all, delete-orphan")
    clases: Mapped[list["ClaseModel"]] = relationship(back_populates="ficha", cascade="all, delete-orphan")
    estudiantes: Mapped[list["EstudianteModel"]] = relationship(back_populates="ficha", cascade="all, delete-orphan")
    actividades: Mapped[list["ActividadModel"]] = relationship(back_populates="ficha", cascade="all, delete-orphan")
