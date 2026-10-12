from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.persistence.models.asistencia_model import AsistenciaModel
from app.infrastructure.persistence.models.clase_model import ClaseModel


class SqlAlchemyAsistenciaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_clase(self, clase_id: str):
        result = await self.session.execute(
            select(AsistenciaModel).where(AsistenciaModel.clase_id == clase_id)
        )
        return list(result.scalars().all())

    async def upsert(self, clase_id: str, estudiante_id: str, estado: str, justificacion: str | None):
        result = await self.session.execute(
            select(AsistenciaModel).where(
                AsistenciaModel.clase_id == clase_id, AsistenciaModel.estudiante_id == estudiante_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.estado = estado
            existing.justificacion = justificacion
            await self.session.flush()
            return existing
        model = AsistenciaModel(
            clase_id=clase_id, estudiante_id=estudiante_id, estado=estado, justificacion=justificacion
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model
