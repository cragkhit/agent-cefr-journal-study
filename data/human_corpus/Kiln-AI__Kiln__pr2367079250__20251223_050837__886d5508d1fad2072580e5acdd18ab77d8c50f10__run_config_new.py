from typing import TYPE_CHECKING, Union

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from kiln_ai.adapters.prompt_builders import (
    BasePromptBuilder,
    PromptGenerators,
    PromptId,
    prompt_builder_from_id,
)
from kiln_ai.datamodel.basemodel import NAME_FIELD, KilnParentedModel
from kiln_ai.datamodel.task import Task

if TYPE_CHECKING:
    from kiln_ai.datamodel.task import Task


class RunConfig(BaseModel):
    """
    A configuration for running a task.

    This includes everything needed to run a task, except the input. Running the same RunConfig with the same input should make identical calls to the model (output may vary as models are non-deterministic).

    For example: task, model, provider, prompt (ID, builder, etc), etc.
    """

    task: "Task" = Field(description="The task to run.")
    model_name: str = Field(description="The model to use for this run config.")
    model_provider_name: str = Field(
        description="The provider to use for this run config."
    )
    prompt_id: PromptId = Field(
        description="The prompt to use for this run config. Defaults to building a simple prompt from the task if not provided.",
        default=PromptGenerators.SIMPLE,
    )

    def prompt_builder(self) -> BasePromptBuilder:
        return prompt_builder_from_id(self.prompt_id, self.task)


class TaskRunConfig(RunConfig, KilnParentedModel):
    """
    A run config, parented to a Kiln Task.

    A run config includes everything needed to run a task, except the input. Running the same RunConfig with the same input should make identical calls to the model (output may vary as models are non-deterministic).

    Used for saving and sharing run configs in a Kiln Project.
    """

    name: str = NAME_FIELD
    description: str | None = Field(
        default=None, description="The description of the task run config."
    )
    run_config: RunConfig = Field(
        description="The run config to use for this task run."
    )

    # Workaround to return typed parent without importing Task
    def parent_task(self) -> Union["Task", None]:
        if self.parent is None or self.parent.__class__.__name__ != "Task":
            return None
        return self.parent  # type: ignore

    @model_validator(mode="after")
    def validate_task(self) -> Self:
        # Check that the task in the run config matches the parent task
        parent_task = self.parent_task()
        if parent_task is None:
            raise ValueError("Run config must be parented to a task")
        if self.run_config.task is None:
            raise ValueError("Run config must have a task")
        if self.run_config.task.id != parent_task.id:
            raise ValueError("Run config task must match parent task")
        return self
