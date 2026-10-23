from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.persistence.models.ficha_model import FichaModel


class SqlAlchemyFichaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, ficha_id: str):
        result = await self.session.execute(
            select(FichaModel)
            .options(
                selectinload(FichaModel.horarios),
                selectinload(FichaModel.estudiantes),
                selectinload(FichaModel.clases),
            )
            .where(FichaModel.id == ficha_id)
        )
        return result.scalar_one_or_none()

    async def find_by_id_and_instructor(self, ficha_id: str, instructor_id: str):
        result = await self.session.execute(
            select(FichaModel)
            .options(
                selectinload(FichaModel.horarios),
                selectinload(FichaModel.estudiantes),
                selectinload(FichaModel.clases),
            )
            .where(FichaModel.id == ficha_id, FichaModel.instructor_id == instructor_id)
        )
        return result.scalar_one_or_none()

    async def find_by_instructor(self, instructor_id: str, archivada: bool):
        result = await self.session.execute(
            select(FichaModel)
            .options(
                selectinload(FichaModel.horarios),
                selectinload(FichaModel.estudiantes),
                selectinload(FichaModel.clases),
            )
            .where(FichaModel.instructor_id == instructor_id, FichaModel.archivada == archivada)
            .order_by(FichaModel.fecha_inicio.desc())
        )
        return list(result.scalars().all())

    async def find_by_unique(self, instructor_id: str, codigo: str, fecha_inicio):
        result = await self.session.execute(
            select(FichaModel).where(
                FichaModel.instructor_id == instructor_id,
                FichaModel.codigo == codigo,
                FichaModel.fecha_inicio == fecha_inicio,
            )
        )
        return result.scalar_one_or_none()

    async def save(self, ficha: FichaModel) -> FichaModel:
        self.session.add(ficha)
        await self.session.flush()
        return ficha

    async def delete(self, ficha: FichaModel):
        await self.session.delete(ficha)
        await self.session.flush()
