from pydantic import Field

from kiln_ai.datamodel.basemodel import NAME_FIELD, KilnBaseModel


class Eval(KilnBaseModel):
    name: str = NAME_FIELD
    description: str | None = Field(
        default=None, description="The description of the eval"
    )
