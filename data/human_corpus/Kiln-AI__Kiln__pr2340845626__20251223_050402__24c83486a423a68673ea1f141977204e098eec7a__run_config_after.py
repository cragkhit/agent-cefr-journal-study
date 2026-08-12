from typing import TYPE_CHECKING, Union

from pydantic import Field, model_validator
from typing_extensions import Self

from kiln_ai.datamodel.basemodel import NAME_FIELD, KilnParentedModel

if TYPE_CHECKING:
    from kiln_ai.datamodel.task import RunConfig, Task


class TaskRunConfig(KilnParentedModel):
    """
    A Kiln model for persisting a run config in a Kiln Project, nested under a task.

    Typically used to save a method of running a task for evaluation.

    A run config includes everything needed to run a task, except the input. Running the same RunConfig with the same input should make identical calls to the model (output may vary as models are non-deterministic).
    """

    name: str = NAME_FIELD
    description: str | None = Field(
        default=None, description="The description of the task run config."
    )
    run_config: "RunConfig" = Field(
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
