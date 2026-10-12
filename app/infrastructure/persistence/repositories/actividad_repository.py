from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.persistence.models.actividad_model import ActividadModel
from app.infrastructure.persistence.models.calificacion_model import CalificacionModel


class SqlAlchemyActividadRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, actividad_id: str):
        return await self.session.get(ActividadModel, actividad_id)

    async def find_by_ficha(self, ficha_id: str):
        result = await self.session.execute(
            select(ActividadModel).where(ActividadModel.ficha_id == ficha_id).order_by(ActividadModel.orden)
        )
        return list(result.scalars().all())

    async def find_children(self, parent_id: str):
        result = await self.session.execute(
            select(ActividadModel).where(ActividadModel.parent_id == parent_id)
        )
        return list(result.scalars().all())

    async def save(self, actividad: ActividadModel):
        self.session.add(actividad)
        await self.session.flush()
        await self.session.refresh(actividad)
        return actividad

    async def delete(self, actividad: ActividadModel):
        await self.session.delete(actividad)
        await self.session.flush()

    # calificaciones
    async def find_calificaciones_by_actividad(self, actividad_id: str):
        result = await self.session.execute(
            select(CalificacionModel).where(CalificacionModel.actividad_id == actividad_id)
        )
        return list(result.scalars().all())

    async def find_calificaciones_by_ficha(self, ficha_id: str):
        result = await self.session.execute(
            select(CalificacionModel)
            .join(ActividadModel, CalificacionModel.actividad_id == ActividadModel.id)
            .where(ActividadModel.ficha_id == ficha_id)
        )
        return list(result.scalars().all())

    async def upsert_calificacion(self, actividad_id: str, estudiante_id: str, nota: float):
        result = await self.session.execute(
            select(CalificacionModel).where(
                CalificacionModel.actividad_id == actividad_id,
                CalificacionModel.estudiante_id == estudiante_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.nota = nota
            await self.session.flush()
            return existing
        model = CalificacionModel(actividad_id=actividad_id, estudiante_id=estudiante_id, nota=nota)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def has_calificaciones_for_ficha(self, ficha_id: str) -> bool:
        result = await self.session.execute(
            select(CalificacionModel.id)
            .join(ActividadModel, CalificacionModel.actividad_id == ActividadModel.id)
            .where(ActividadModel.ficha_id == ficha_id)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
