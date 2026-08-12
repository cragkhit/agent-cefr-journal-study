from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from kiln_ai.adapters.ml_model_list import ModelProviderName
from kiln_ai.datamodel import (
    BasePrompt,
    DataSource,
    DataSourceType,
    PromptId,
    Task,
)
from kiln_ai.datamodel.dataset_filters import DatasetFilterId
from kiln_ai.datamodel.eval import (
    Eval,
    EvalConfig,
    EvalConfigType,
    EvalOutputScore,
    EvalTemplate,
)

from app.desktop.studio_server.evals_api import (
    CreateEvalConfigRequest,
    CreateEvaluatorRequest,
    connect_evals_api,
)


@pytest.fixture
def app():
    app = FastAPI()
    connect_evals_api(app)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_task(tmp_path):
    task = Task(
        id="task1",
        name="Test Task",
        description="Test Description",
        instruction="Test Instructions",
        path=tmp_path / "task.kiln",
    )
    task.save_to_file()
    return task


@pytest.fixture
def mock_eval(mock_task):
    eval = Eval(
        id="eval1",
        name="Test Eval",
        description="Test Description",
        template=EvalTemplate.bias,
        output_scores=[
            EvalOutputScore(name="score1", description="desc1", type="five_star"),
        ],
        eval_set_filter_id="tag::eval_set",
        eval_configs_filter_id="tag::golden",
        parent=mock_task,
    )
    eval.save_to_file()
    return eval


@pytest.fixture
def mock_eval_config(mock_eval):
    eval_config = EvalConfig(
        id="eval_config1",
        config_type=EvalConfigType.g_eval,
        properties={"eval_steps": ["step1", "step2"]},
        parent=mock_eval,
        model=DataSource(
            id="model1",
            type=DataSourceType.synthetic,
            properties={
                "model_name": "gpt-4",
                "model_provider": "openai",
                "adapter_name": "TODO",
            },
        ),
        prompt=BasePrompt(
            name="test",
            prompt="base prompt",
            chain_of_thought_instructions="cot prompt",
        ),
    )
    eval_config.save_to_file()
    return eval_config


@pytest.fixture
def mock_task_from_id(mock_task):
    with patch("app.desktop.studio_server.evals_api.task_from_id") as mock:
        mock.return_value = mock_task
        yield mock


def test_get_evals_success(client, mock_task, mock_task_from_id, mock_eval):
    mock_task_from_id.return_value = mock_task

    response = client.get("/api/projects/project1/tasks/task1/evals")

    assert response.status_code == 200
    result = response.json()
    assert len(result) == 1
    assert result[0]["id"] == "eval1"
    assert result[0]["name"] == "Test Eval"
    mock_task_from_id.assert_called_once_with("project1", "task1")


def test_get_eval_success(client, mock_task, mock_task_from_id, mock_eval):
    mock_task_from_id.return_value = mock_task

    response = client.get("/api/projects/project1/tasks/task1/eval/eval1")

    assert response.status_code == 200
    result = response.json()
    assert result["id"] == "eval1"
    assert result["name"] == "Test Eval"
    mock_task_from_id.assert_called_once_with("project1", "task1")


def test_get_eval_not_found(client, mock_task, mock_task_from_id):
    mock_task_from_id.return_value = mock_task

    response = client.get("/api/projects/project1/tasks/task1/eval/non_existent")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found. ID: task1"


@pytest.fixture
def valid_evaluator_request():
    return CreateEvaluatorRequest(
        name="Test Evaluator",
        description="Test Description",
        template=None,
        output_scores=[
            EvalOutputScore(name="score1", description="desc1", type="five_star"),
        ],
        eval_set_filter_id="tag::eval_set",
        eval_configs_filter_id="tag::golden",
    )


@pytest.fixture
def valid_eval_config_request():
    return CreateEvalConfigRequest(
        type=EvalConfigType.g_eval,
        properties={"eval_steps": ["step1", "step2"]},
        model_name="gpt-4",
        provider=ModelProviderName.openai,
        prompt_id="simple_chain_of_thought_prompt_builder",
    )


@pytest.mark.asyncio
async def test_create_evaluator(
    client, mock_task_from_id, valid_evaluator_request, mock_task
):
    mock_task_from_id.return_value = mock_task

    with patch.object(Eval, "save_to_file") as mock_save:
        response = client.post(
            "/api/projects/project1/tasks/task1/create_evaluator",
            json=valid_evaluator_request.model_dump(),
        )

    assert response.status_code == 200
    result = response.json()
    assert result["name"] == valid_evaluator_request.name
    assert result["description"] == valid_evaluator_request.description
    mock_save.assert_called_once()


@pytest.mark.asyncio
async def test_create_eval_config(
    client, mock_task_from_id, valid_eval_config_request, mock_eval, mock_task
):
    mock_task_from_id.return_value = mock_task

    with (
        patch("app.desktop.studio_server.evals_api.eval_from_id") as mock_eval_from_id,
        patch(
            "app.desktop.studio_server.evals_api.prompt_builder_from_id"
        ) as mock_prompt_builder,
        # patch.object(EvalConfig, "save_to_file") as mock_save,
    ):
        mock_eval_from_id.return_value = mock_eval
        mock_prompt_builder.return_value.build_base_prompt.return_value = "base prompt"
        mock_prompt_builder.return_value.chain_of_thought_prompt.return_value = (
            "cot prompt"
        )

        response = client.post(
            "/api/projects/project1/tasks/task1/eval/eval1/create_eval_config",
            json=valid_eval_config_request.model_dump(),
        )

    assert response.status_code == 200
    result = response.json()
    assert result["config_type"] == valid_eval_config_request.type
    assert result["properties"] == valid_eval_config_request.properties
    assert result["model"]["type"] == DataSourceType.synthetic
    assert (
        result["model"]["properties"]["model_name"]
        == valid_eval_config_request.model_name
    )
    assert (
        result["model"]["properties"]["model_provider"]
        == valid_eval_config_request.provider
    )
    assert isinstance(result["prompt"], dict)
    # mock_save.assert_called_once()

    # Fetch disk
    assert len(mock_eval.configs()) == 1
    config = mock_eval.configs()[0]
    assert config.config_type == valid_eval_config_request.type
    assert config.properties == valid_eval_config_request.properties
    assert config.model.type == DataSourceType.synthetic
    assert config.model.properties["model_name"] == valid_eval_config_request.model_name
    assert (
        config.model.properties["model_provider"] == valid_eval_config_request.provider
    )
    assert config.prompt.prompt == "base prompt"
    assert config.prompt.chain_of_thought_instructions == "cot prompt"
    assert config.properties["eval_steps"][0] == "step1"
    assert config.properties["eval_steps"][1] == "step2"


def test_get_eval_configs(
    client, mock_task_from_id, mock_eval, mock_task, mock_eval_config
):
    mock_task_from_id.return_value = mock_task

    with patch("app.desktop.studio_server.evals_api.eval_from_id") as mock_eval_from_id:
        mock_eval_from_id.return_value = mock_eval
        response = client.get(
            "/api/projects/project1/tasks/task1/eval/eval1/eval_configs"
        )

    assert response.status_code == 200
    configs = response.json()
    assert isinstance(configs, list)
    assert len(configs) == 1

    config = configs[0]
    assert config["config_type"] == mock_eval_config.config_type
    assert config["properties"] == mock_eval_config.properties
    assert config["model"]["type"] == mock_eval_config.model.type
    assert isinstance(config["prompt"], dict)

    mock_eval_from_id.assert_called_once_with("project1", "task1", "eval1")
