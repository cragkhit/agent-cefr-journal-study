import json
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Union

from pydantic import Field, model_validator
from typing_extensions import Self

from kiln_ai.datamodel.basemodel import (
    ID_TYPE,
    NAME_FIELD,
    KilnParentedModel,
    KilnParentModel,
)
from kiln_ai.datamodel.dataset_filters import DatasetFilterId
from kiln_ai.datamodel.prompt import BasePrompt
from kiln_ai.datamodel.task_output import DataSource, DataSourceType

if TYPE_CHECKING:
    from kiln_ai.datamodel.task import Task

EvalScores = Dict[str, float]


class EvalState(str, Enum):
    enabled = "enabled"
    disabled = "disabled"


class EvalConfigType(str, Enum):
    g_eval = "g_eval"
    llm_as_judge = "llm_as_judge"


class EvalRun(KilnParentedModel):
    """
    The results of running an eval on a single dataset item, with a specific TaskRunConfig and EvalConfig.
    """

    dataset_id: ID_TYPE = Field(
        description="The ID of the dataset item that was used for this run (we only use it's input). Must belong to the same Task as this eval."
    )
    task_run_config_id: ID_TYPE = Field(
        description="The ID of the TaskRunConfig that was run. Must belong to the same Task as this eval."
    )
    # This may duplicate the dataset_id.input, but we're denormalizing intentionally.
    input: str = Field(
        description="The input to the task. JSON formatted for structured input, plaintext for unstructured input."
    )
    output: str = Field(
        description="The output of the task. JSON formatted for structured output, plaintext for unstructured output."
    )
    scores: EvalScores = Field(
        description="The scores of the evaluator (specifically the EvalConfig this object is a child of)."
    )

    def parent_eval_config(self) -> "EvalConfig":
        if self.parent is None or self.parent.__class__.__name__ != "EvalConfig":
            raise ValueError("parent must be an EvalConfig")
        return self.parent  # type: ignore


class EvalConfig(KilnParentedModel, KilnParentModel, parent_of={"runs": EvalRun}):
    """
    A configuration for running an eval. This includes anything needed to run the eval on a dataset like the prompt, model, thresholds, etc.

    A eval might have many configs, example running the same eval with 2 different models. Comparing eval results is only valid when the same eval is run with the same config.
    """

    name: str = NAME_FIELD
    model: DataSource = Field(description="The model to use for this eval config.")
    config_type: EvalConfigType = Field(
        default=EvalConfigType.g_eval,
        description="This is used to determine the type of eval to run.",
    )
    properties: dict[str, Any] = Field(
        default={},
        description="Properties to be used to execute the eval config. This is config_type specific and should serialize to a json dict.",
    )
    prompt: BasePrompt = Field(description="The prompt to use for this eval config.")

    def parent_eval(self) -> "Eval":
        if self.parent is None or self.parent.__class__.__name__ != "Eval":
            raise ValueError("parent must be an Eval")
        return self.parent  # type: ignore

    @model_validator(mode="after")
    def validate_properties(self) -> Self:
        if (
            self.config_type == EvalConfigType.g_eval
            or self.config_type == EvalConfigType.llm_as_judge
        ):
            if "eval_steps" not in self.properties or not isinstance(
                self.properties["eval_steps"], list
            ):
                raise ValueError("eval_steps is required and must be a list for g_eval")
            return self
        else:
            raise ValueError(f"Invalid eval config type: {self.config_type}")

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        if self.model.type != DataSourceType.synthetic:
            raise ValueError("model must be a synthetic model for an eval config")
        return self

    @model_validator(mode="after")
    def validate_json_serializable(self) -> "EvalConfig":
        try:
            # This will raise a TypeError if the dict contains non-JSON-serializable objects
            json.dumps(self.properties)
        except TypeError as e:
            raise ValueError(f"Properties must be JSON serializable: {str(e)}")
        return self


class Eval(KilnParentedModel, KilnParentModel, parent_of={"configs": EvalConfig}):
    name: str = NAME_FIELD
    description: str | None = Field(
        default=None, description="The description of the eval"
    )
    state: EvalState = Field(
        default=EvalState.enabled,
        description="The state of the eval: enabled or disabled.",
    )
    current_config_id: ID_TYPE = Field(
        default=None,
        description="The id of the current config to use for this eval. This can be changed over time to run the same eval with different configs.",
    )
    eval_set_filter_id: DatasetFilterId = Field(
        description="The id of the dataset filter which defines which dataset items are included when running this eval. Should be mutually exclusive with eval_configs_filter_id."
    )
    eval_configs_filter_id: DatasetFilterId = Field(
        description="The id of the dataset filter which defines which dataset items are included when comparing the quality of the eval configs under this eval. Should consist of dataset items with ratings. Should be mutually exclusive with eval_set_filter_id."
    )

    # Workaround to return typed parent without importing Task
    def parent_task(self) -> Union["Task", None]:
        if self.parent is None or self.parent.__class__.__name__ != "Task":
            return None
        return self.parent  # type: ignore

    def configs(self, readonly: bool = False) -> list[EvalConfig]:
        return super().configs(readonly=readonly)  # type: ignore
