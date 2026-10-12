from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.persistence.models.estudiante_model import EstudianteModel


class SqlAlchemyEstudianteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, estudiante_id: str):
        return await self.session.get(EstudianteModel, estudiante_id)

    async def find_by_ficha(self, ficha_id: str):
        result = await self.session.execute(
            select(EstudianteModel).where(EstudianteModel.ficha_id == ficha_id).order_by(EstudianteModel.nombre)
        )
        return list(result.scalars().all())

    async def find_by_ficha_and_identificacion(self, ficha_id: str, identificacion: str):
        result = await self.session.execute(
            select(EstudianteModel).where(
                EstudianteModel.ficha_id == ficha_id, EstudianteModel.identificacion == identificacion
            )
        )
        return result.scalar_one_or_none()

    async def save(self, estudiante: EstudianteModel):
        self.session.add(estudiante)
        await self.session.flush()
        await self.session.refresh(estudiante)
        return estudiante

    async def delete(self, estudiante: EstudianteModel):
        await self.session.delete(estudiante)
        await self.session.flush()
