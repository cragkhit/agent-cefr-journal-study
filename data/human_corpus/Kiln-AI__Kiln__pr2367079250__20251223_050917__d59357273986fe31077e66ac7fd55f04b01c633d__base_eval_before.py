import json
from abc import abstractmethod
from typing import Dict

from kiln_ai.adapters.adapter_registry import adapter_for_task
from kiln_ai.adapters.ml_model_list import ModelProviderName
from kiln_ai.adapters.model_adapters.base_adapter import AdapterConfig
from kiln_ai.datamodel.eval import EvalConfig
from kiln_ai.datamodel.json_schema import string_to_json_key, validate_schema
from kiln_ai.datamodel.task import Task, TaskOutputRatingType, TaskRun
from kiln_ai.utils.exhaustive_error import raise_exhaustive_enum_error


class BaseEval:
    def __init__(self, eval_config: EvalConfig):
        self.eval_config = eval_config
        eval = eval_config.parent_eval()
        if not eval:
            raise ValueError("Eval config must have a parent eval")
        self.eval = eval
        task = self.eval.parent_task()
        if not task:
            raise ValueError("Eval must have a parent task")
        self.target_task = task
        self.score_schema = BaseEval.build_score_schema(task, allow_float_scores=True)

    def model_and_provider(self) -> tuple[str, ModelProviderName]:
        model_name = self.eval_config.model.properties.get("model_name")
        provider = self.eval_config.model.properties.get("model_provider")
        if (
            not model_name
            or not provider
            or not isinstance(model_name, str)
            or not isinstance(provider, str)
            or provider not in ModelProviderName.__members__
        ):
            raise ValueError(
                "Model name and provider must be set in the eval config model properties"
            )

        return model_name, ModelProviderName(provider)

    async def run(self, input: Dict | str) -> Dict[str, float]:
        run_adapter = adapter_for_task(
            self.target_task,
            # TODO: take these from evalRun
            "llama_3_1_8b",
            ModelProviderName.groq,
            base_adapter_config=AdapterConfig(allow_saving=False),
        )

        # we don't save by default here. We'll save manually after validating the output
        run_output = await run_adapter.invoke(input)

        eval_output = await self.run_eval(run_output)
        validate_schema(eval_output, self.score_schema)

        return eval_output

    @abstractmethod
    # Runs the eval on the given task run and returns a dictionary of scores which should conform to the score schema
    async def run_eval(self, task_run: TaskRun) -> Dict[str, float]:
        pass

    @classmethod
    def build_score_schema(cls, task: Task, allow_float_scores: bool = False) -> str:
        """
        Build a JSON schema for the scoring output of the task requirements

        We allow 2 modes: allow_float_scores=True and allow_float_scores=False.

        allow_float_scores=False is used for the call to the model, and forces the model into selecting into discrete rating options (int 1-5, pass-fail, etc).
        allow_float_scores=True is used after we take a g-eval weighting of the model's logprobs. For example, a pass/fail rating might return 0.75 for likely pass (as opposed to 0.99 for near certain pass), or a 1-5 score might return 3.75.
        """

        # Note: python maintains order, which is good as we want the user defined order, and overall last
        properties = {}
        for requirement in task.requirements:
            property_key = string_to_json_key(requirement.name)
            if property_key in properties or property_key == "overall_rating":
                raise ValueError(
                    f"Duplicate requirement name: {requirement.name}. Can not be used as unique JSON schema key."
                )
            if len(property_key) == 0:
                raise ValueError(
                    f"Invalid requirement name: {requirement.name}. Can not be used as JSON schema key."
                )
            property: dict[str, str | int | float | list[str] | list[int]] = {
                "title": requirement.name,
            }
            match requirement.type:
                case TaskOutputRatingType.five_star:
                    if allow_float_scores:
                        property["type"] = "number"
                        property["minimum"] = 1
                        property["maximum"] = 5
                    else:
                        property["enum"] = [1, 2, 3, 4, 5]

                    property["description"] = (
                        f"{requirement.instruction}\n\nThe rating should be between 1 and 5, with 1 being the worst and 5 being the best."
                    )
                case TaskOutputRatingType.pass_fail:
                    if allow_float_scores:
                        property["type"] = "number"
                        property["minimum"] = 0
                        property["maximum"] = 1
                        property["description"] = (
                            f"{requirement.instruction}\n\nThe rating should be between 0 and 1, with 0 being a failure and 1 being a pass."
                        )
                    else:
                        property["enum"] = ["pass", "fail"]
                        property["description"] = (
                            f"{requirement.instruction}\n\nThe rating should be either 'pass' or 'fail'."
                        )
                case TaskOutputRatingType.pass_fail_critical:
                    if allow_float_scores:
                        property["type"] = "number"
                        property["minimum"] = -1
                        property["maximum"] = 1
                        property["description"] = (
                            f"{requirement.instruction}\n\nThe rating should be between -1 and 1, with 1 being a pass, 0 being a failure, and -1 being a critical failure (very severe failure)."
                        )
                    else:
                        property["enum"] = ["pass", "fail", "critical"]
                        property["description"] = (
                            f"{requirement.instruction}\n\nThe rating should be either 'pass', 'fail', or 'critical' where critical a very severe failure."
                        )
                case TaskOutputRatingType.custom:
                    # Skip custom rating types in evals
                    continue
                case _:
                    raise_exhaustive_enum_error(requirement.type)

            properties[property_key] = property

        if allow_float_scores:
            properties["overall_rating"] = {
                "type": "number",
                "minimum": 1,
                "maximum": 5,
                "title": "Overall Rating",
                "description": "The overall rating for the task output.\n\nThe rating should be between 1 and 5, with 1 being the worst and 5 being the best.",
            }
        else:
            properties["overall_rating"] = {
                "enum": [1, 2, 3, 4, 5],
                "title": "Overall Rating",
                "description": "The overall rating for the task output.\n\nThe rating should be between 1 and 5, with 1 being the worst and 5 being the best.",
            }

        schema = {
            "type": "object",
            "properties": properties,
            "required": list(properties.keys()),
        }
        return json.dumps(schema, ensure_ascii=False)
