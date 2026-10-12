from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Instructor:
    id: str
    nombre: str
    email: str  # normalized lowercase
    password_hash: str
    created_at: datetime
    updated_at: datetime
