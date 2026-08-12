from typing import Any

from fastapi import FastAPI, HTTPException
from kiln_ai.adapters.ml_model_list import ModelProviderName
from kiln_ai.adapters.prompt_builders import prompt_builder_from_id
from kiln_ai.datamodel import (
    BasePrompt,
    DataSource,
    DataSourceType,
    PromptId,
)
from kiln_ai.datamodel.dataset_filters import DatasetFilterId
from kiln_ai.datamodel.eval import (
    Eval,
    EvalConfig,
    EvalConfigType,
    EvalOutputScore,
    EvalTemplate,
)
from kiln_server.task_api import task_from_id
from pydantic import BaseModel


def eval_from_id(project_id: str, task_id: str, eval_id: str) -> Eval:
    task = task_from_id(project_id, task_id)
    for eval in task.evals():
        if eval.id == eval_id:
            return eval

    raise HTTPException(
        status_code=404,
        detail=f"Task not found. ID: {task_id}",
    )


class CreateEvaluatorRequest(BaseModel):
    name: str
    description: str
    template: EvalTemplate | None
    output_scores: list[EvalOutputScore]
    eval_set_filter_id: DatasetFilterId
    eval_configs_filter_id: DatasetFilterId


class CreateEvalConfigRequest(BaseModel):
    type: EvalConfigType
    properties: dict[str, Any]
    model_name: str
    provider: ModelProviderName
    prompt_id: PromptId


def connect_evals_api(app: FastAPI):
    @app.post("/api/projects/{project_id}/tasks/{task_id}/create_evaluator")
    async def create_evaluator(
        project_id: str,
        task_id: str,
        request: CreateEvaluatorRequest,
    ) -> Eval:
        task = task_from_id(project_id, task_id)
        eval = Eval(
            name=request.name,
            description=request.description,
            template=request.template,
            output_scores=request.output_scores,
            eval_set_filter_id=request.eval_set_filter_id,
            eval_configs_filter_id=request.eval_configs_filter_id,
            parent=task,
        )
        eval.save_to_file()
        return eval

    @app.get("/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}")
    async def get_eval(project_id: str, task_id: str, eval_id: str) -> Eval:
        return eval_from_id(project_id, task_id, eval_id)

    @app.get("/api/projects/{project_id}/tasks/{task_id}/evals")
    async def get_evals(project_id: str, task_id: str) -> list[Eval]:
        task = task_from_id(project_id, task_id)
        return task.evals()

    @app.post(
        "/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}/create_eval_config"
    )
    async def create_eval_config(
        project_id: str,
        task_id: str,
        eval_id: str,
        request: CreateEvalConfigRequest,
    ) -> EvalConfig:
        task = task_from_id(project_id, task_id)
        eval = eval_from_id(project_id, task_id, eval_id)

        # Create a prompt instance to save to the eval config
        prompt_builder = prompt_builder_from_id(request.prompt_id, task)
        prompt = BasePrompt(
            name=request.prompt_id,
            generator_id=request.prompt_id,
            prompt=prompt_builder.build_base_prompt(),
            chain_of_thought_instructions=prompt_builder.chain_of_thought_prompt(),
        )

        eval_config = EvalConfig(
            config_type=request.type,
            properties=request.properties,
            model=DataSource(
                type=DataSourceType.synthetic,
                properties={
                    "model_name": request.model_name,
                    "model_provider": request.provider,
                    # TODO remove this
                    "adapter_name": "eval",
                },
            ),
            prompt=prompt,
            parent=eval,
        )
        eval_config.save_to_file()
        return eval_config
