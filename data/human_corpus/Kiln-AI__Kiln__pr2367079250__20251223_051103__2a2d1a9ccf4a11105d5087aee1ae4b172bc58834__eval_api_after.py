import json
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from kiln_ai.adapters.eval.eval_runner import EvalRunner
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
from kiln_ai.datamodel.task import RunConfigProperties, TaskRunConfig
from kiln_ai.utils.name_generator import generate_memorable_name
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


def eval_config_from_id(
    project_id: str, task_id: str, eval_id: str, eval_config_id: str
) -> EvalConfig:
    eval = eval_from_id(project_id, task_id, eval_id)
    for config in eval.configs():
        if config.id == eval_config_id:
            return config

    raise HTTPException(
        status_code=404,
        detail=f"Eval config not found. ID: {eval_config_id}",
    )


def task_run_config_from_id(
    project_id: str, task_id: str, run_config_id: str
) -> TaskRunConfig:
    task = task_from_id(project_id, task_id)
    for run_config in task.run_configs():
        if run_config.id == run_config_id:
            return run_config

    raise HTTPException(
        status_code=404,
        detail=f"Task run config not found. ID: {run_config_id}",
    )


class CreateEvaluatorRequest(BaseModel):
    name: str
    description: str
    template: EvalTemplate | None
    output_scores: list[EvalOutputScore]
    eval_set_filter_id: DatasetFilterId
    eval_configs_filter_id: DatasetFilterId


class CreateEvalConfigRequest(BaseModel):
    name: str | None = None
    type: EvalConfigType
    properties: dict[str, Any]
    model_name: str
    provider: ModelProviderName
    prompt_id: PromptId


class CreateTaskRunConfigRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    model_name: str
    model_provider_name: ModelProviderName
    prompt_id: PromptId


class RunEvalConfigRequest(BaseModel):
    run_config_ids: list[str]


class ScoreSummary(BaseModel):
    mean_score: float


class EvalResultSummary(BaseModel):
    # run_config_id -> output_score_id -> ScoreSummary
    results: Dict[str, Dict[str, ScoreSummary]]


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

    @app.get("/api/projects/{project_id}/tasks/{task_id}/task_run_configs")
    async def get_task_run_configs(
        project_id: str, task_id: str
    ) -> list[TaskRunConfig]:
        task = task_from_id(project_id, task_id)
        return task.run_configs()

    @app.get("/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}")
    async def get_eval(project_id: str, task_id: str, eval_id: str) -> Eval:
        return eval_from_id(project_id, task_id, eval_id)

    @app.get("/api/projects/{project_id}/tasks/{task_id}/evals")
    async def get_evals(project_id: str, task_id: str) -> list[Eval]:
        task = task_from_id(project_id, task_id)
        return task.evals()

    @app.get("/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}/eval_configs")
    async def get_eval_configs(
        project_id: str, task_id: str, eval_id: str
    ) -> list[EvalConfig]:
        eval = eval_from_id(project_id, task_id, eval_id)
        return eval.configs()

    @app.post("/api/projects/{project_id}/tasks/{task_id}/task_run_config")
    async def create_task_run_config(
        project_id: str,
        task_id: str,
        request: CreateTaskRunConfigRequest,
    ) -> TaskRunConfig:
        task = task_from_id(project_id, task_id)
        name = request.name or generate_memorable_name()
        task_run_config = TaskRunConfig(
            parent=task,
            name=name,
            description=request.description,
            run_config_properties=RunConfigProperties(
                model_name=request.model_name,
                model_provider_name=request.model_provider_name,
                prompt_id=request.prompt_id,
            ),
        )
        task_run_config.save_to_file()
        return task_run_config

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
        name = request.name or generate_memorable_name()

        # Create a prompt instance to save to the eval config
        prompt_builder = prompt_builder_from_id(request.prompt_id, task)
        prompt = BasePrompt(
            name=request.prompt_id,
            generator_id=request.prompt_id,
            prompt=prompt_builder.build_base_prompt(),
            chain_of_thought_instructions=prompt_builder.chain_of_thought_prompt(),
        )

        eval_config = EvalConfig(
            name=name,
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

    # JS SSE client (EventSource) doesn't work with POST requests, so we use GET, even though post would be better
    @app.get(
        "/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}/eval_config/{eval_config_id}/run"
    )
    async def run_eval_config(
        project_id: str,
        task_id: str,
        eval_id: str,
        eval_config_id: str,
        run_config_ids: list[str] = Query([]),
        all_run_configs: bool = Query(False),
    ) -> StreamingResponse:
        eval_config = eval_config_from_id(project_id, task_id, eval_id, eval_config_id)

        # Load the list of run configs to use. Two options:
        run_configs: list[TaskRunConfig] = []
        if all_run_configs:
            run_configs = task_from_id(project_id, task_id).run_configs()
        else:
            if len(run_config_ids) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No run config ids provided. At least one run config id is required.",
                )
            run_configs = [
                task_run_config_from_id(project_id, task_id, run_config_id)
                for run_config_id in run_config_ids
            ]

        eval_runner = EvalRunner(
            eval_config=eval_config,
            run_configs=run_configs,
        )

        # Async messages via server side events (SSE)
        async def event_generator():
            async for progress in eval_runner.run():
                data = {
                    "progress": progress.complete,
                    "total": progress.total,
                    "errors": progress.errors,
                }
                yield f"data: {json.dumps(data)}\n\n"

            # Send the final complete message the app expects, and uses to stop listening
            yield "data: complete\n\n"

        return StreamingResponse(
            content=event_generator(),
            media_type="text/event-stream",
        )

    @app.get(
        "/api/projects/{project_id}/tasks/{task_id}/eval/{eval_id}/eval_config/{eval_config_id}/score_summary"
    )
    async def get_eval_config_score_summary(
        project_id: str,
        task_id: str,
        eval_id: str,
        eval_config_id: str,
    ) -> EvalResultSummary:
        eval = eval_from_id(project_id, task_id, eval_id)
        eval_config = eval_config_from_id(project_id, task_id, eval_id, eval_config_id)

        # task_run_config_id -> output_score_id -> score/total
        total_scores: Dict[str, Dict[str, float]] = {}
        score_counts: Dict[str, Dict[str, int]] = {}

        # TODO: is the dataset item still in the dataset? They can add/remove tags
        # TODO: is the score for each run_config complete

        # important: readonly makes this much faster
        for eval_run in eval_config.runs(readonly=True):
            for output_score in eval.output_scores:
                score_key = output_score.json_key()
                run_config_id = str(eval_run.task_run_config_id)
                if run_config_id not in total_scores:
                    total_scores[run_config_id] = {}
                    score_counts[run_config_id] = {}
                if score_key not in total_scores[run_config_id]:
                    total_scores[run_config_id][score_key] = 0
                    score_counts[run_config_id][score_key] = 0
                if score_key in eval_run.scores:
                    total_scores[run_config_id][score_key] += eval_run.scores[score_key]
                    score_counts[run_config_id][score_key] += 1
                    print(
                        f"adding score to {run_config_id} {score_key} = {eval_run.scores[score_key]}"
                    )

        # Convert to score summaries
        results: Dict[str, Dict[str, ScoreSummary]] = {}
        for run_config_id, output_scores in total_scores.items():
            results[run_config_id] = {}
            for output_score_id, score in output_scores.items():
                if score_counts[run_config_id][output_score_id] > 0:
                    results[run_config_id][output_score_id] = ScoreSummary(
                        mean_score=score / score_counts[run_config_id][output_score_id]
                    )

        return EvalResultSummary(
            results=results,
        )
