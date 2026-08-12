from pydantic import Field

from kiln_ai.datamodel.basemodel import NAME_FIELD, KilnParentedModel


class Prompt(KilnParentedModel):
    """
    A prompt for a task.
    """

    name: str = NAME_FIELD
    prompt: str = Field(
        description="The prompt for the task.",
        min_length=1,
    )
    chain_of_thought_instructions: str | None = Field(
        default=None,
        description="Instructions for the model 'thinking' about the requirement prior to answering. Used for chain of thought style prompting. COT will not be used unless this is provided.",
    )
