import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base


class HorarioFichaModel(Base):
    __tablename__ = "horarios_ficha"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ficha_id: Mapped[str] = mapped_column(String(36), ForeignKey("fichas.id", ondelete="CASCADE"), nullable=False, index=True)
    dia_semana: Mapped[int] = mapped_column(Integer, nullable=False)
    hora: Mapped[str] = mapped_column(String(5), nullable=False)
    duracion_minutos: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    ficha: Mapped["FichaModel"] = relationship(back_populates="horarios")
