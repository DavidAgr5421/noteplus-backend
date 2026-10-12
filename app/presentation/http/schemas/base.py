from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base schema: accepts snake_case AND camelCase, serializes camelCase.

    Lets the React frontend (camelCase) talk to Python models (snake_case)
    without breaking existing snake_case clients or tests.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="ignore",
    )
