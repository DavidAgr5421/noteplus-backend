from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.clase_model import ClaseModel
from app.infrastructure.persistence.models.ficha_model import FichaModel


class SqlAlchemyClaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, clase_id: str):
        return await self.session.get(ClaseModel, clase_id)

    async def find_by_ficha(self, ficha_id: str):
        result = await self.session.execute(
            select(ClaseModel).where(ClaseModel.ficha_id == ficha_id).order_by(ClaseModel.fecha, ClaseModel.hora)
        )
        return list(result.scalars().all())

    async def find_by_instructor_range(self, instructor_id: str, from_date: date | None, to_date: date | None):
        # Only active fichas
        query = (
            select(ClaseModel)
            .join(FichaModel, ClaseModel.ficha_id == FichaModel.id)
            .where(FichaModel.instructor_id == instructor_id, FichaModel.archivada == False)  # noqa: E712
        )
        if from_date:
            query = query.where(ClaseModel.fecha >= from_date)
        if to_date:
            query = query.where(ClaseModel.fecha <= to_date)
        query = query.order_by(ClaseModel.fecha, ClaseModel.hora)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def find_today(self, instructor_id: str, today: date):
        query = (
            select(ClaseModel)
            .join(FichaModel, ClaseModel.ficha_id == FichaModel.id)
            .where(
                FichaModel.instructor_id == instructor_id,
                FichaModel.archivada == False,  # noqa: E712
                ClaseModel.fecha == today,
            )
            .order_by(ClaseModel.hora)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def save(self, clase: ClaseModel):
        self.session.add(clase)
        await self.session.flush()
        await self.session.refresh(clase)
        return clase
