from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.instructor_model import InstructorModel


class SqlAlchemyInstructorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, instructor_id: str):
        result = await self.session.get(InstructorModel, instructor_id)
        return result

    async def find_by_email(self, email: str):
        result = await self.session.execute(
            select(InstructorModel).where(InstructorModel.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def save(self, instructor: InstructorModel) -> InstructorModel:
        self.session.add(instructor)
        await self.session.flush()
        return instructor

    async def create(self, nombre: str, email: str, password_hash: str) -> InstructorModel:
        model = InstructorModel(nombre=nombre, email=email.lower(), password_hash=password_hash)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model
