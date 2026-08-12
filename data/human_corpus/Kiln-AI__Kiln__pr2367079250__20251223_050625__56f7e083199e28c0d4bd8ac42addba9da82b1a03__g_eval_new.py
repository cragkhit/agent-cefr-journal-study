import json
from typing import Dict

from kiln_ai.adapters.adapter_registry import adapter_for_task
from kiln_ai.adapters.eval.base_eval import BaseEval
from kiln_ai.adapters.prompt_builders import SimpleChainOfThoughtPromptBuilder
from kiln_ai.datamodel import Project, Task, TaskRun
from kiln_ai.datamodel.eval import EvalConfig, EvalConfigType

# better prompts
# https://github.com/microsoft/promptflow/tree/main/examples/flows/evaluation/eval-summarization


class GEvalTask(Task, parent_of={}):
    """
    Kiln task for executing a G-Eval. Can be run on any Kiln adapter.
    """

    def __init__(self, eval_config: EvalConfig, target_task: Task):
        # This keep the typechecker happy. TODO: shouldn't need this or parent_of above.
        tmp_project = Project(name="GEval")

        system_instruction = f"""
Your job to evaluate a model's performance on a task. Blocks will be marked with <eval_data> tags.
        
The task the model was given is as follows:
<eval_data>
{eval_config.prompt.prompt}
</eval_data>
"""
        # TODO allow over riding of system instruction via config

        # Build the COT eval instructions
        cot_instructions = "First, think step by step about the model's performance following these evaluation steps:\n\n"
        steps = eval_config.properties["g_eval_steps"]
        if not steps or not isinstance(steps, list):
            raise ValueError("g_eval_steps must be a list")
        for i, step in enumerate(steps):
            cot_instructions += f"{i + 1}) {step}\n"

        # We restrict the LLM scoring to integer scores (see later logprob calculation, which requires integer scores)
        # However, the overall score we output can be a float.
        output_schema = BaseEval.build_score_schema(
            target_task, allow_float_scores=False
        )

        super().__init__(
            name="GEval Task",
            parent=tmp_project,
            instruction=system_instruction,
            thinking_instruction=cot_instructions,
            output_json_schema=output_schema,
        )


class GEval(BaseEval):
    def __init__(self, eval_config: EvalConfig):
        if not eval_config.config_type == EvalConfigType.g_eval:
            raise ValueError("GEval must be initialized with a GEval Config")

        super().__init__(eval_config)

        self.geval_task = GEvalTask(eval_config, self.target_task)

    async def run_eval(self, task_run: TaskRun) -> Dict[str, int | float | str]:
        """
        Run this G-Eval on the given task run.
        """

        model_name, provider = self.model_and_provider()
        # We always use Simple COT for G-Eval
        prompt_builder = SimpleChainOfThoughtPromptBuilder(self.geval_task)

        adapter = adapter_for_task(
            self.geval_task,
            model_name,
            provider,
            prompt_builder,
        )

        # TODO: does eval see intermediate output? I don't think so, but think about it.
        input = f"""The model was given the following input for the task: 
<eval_data>
{task_run.input}
</eval_data>

The model produced the following output for the task:
<eval_data>
{task_run.output}
</eval_data>
"""

        result = await adapter.invoke(input)

        # TODO g_eval logprobs
        parsed_output = json.loads(result.output.output)
        return parsed_output
