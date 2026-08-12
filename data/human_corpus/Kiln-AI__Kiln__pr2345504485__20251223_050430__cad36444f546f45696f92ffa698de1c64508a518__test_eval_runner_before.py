from unittest.mock import AsyncMock

import pytest
from kiln_ai.adapters.eval.eval_runner import EvalRunner
from kiln_ai.datamodel import BasePrompt, DataSource, DataSourceType, Task
from kiln_ai.datamodel.eval import Eval, EvalConfig
from kiln_ai.datamodel.task import RunConfigProperties, TaskRunConfig


def test_asdf():
    assert 1 == 1


@pytest.fixture
def mock_task():
    return Task(
        name="test",
        description="test",
        instruction="do the thing",
    )


@pytest.fixture
def mock_eval(mock_task):
    return Eval(
        id="test",
        name="test",
        description="test",
        eval_set_filter_id="all",
        eval_configs_filter_id="all",
        parent=mock_task,
    )


@pytest.fixture
def data_source():
    return DataSource(
        type=DataSourceType.synthetic,
        properties={
            "model_name": "gpt-4",
            "model_provider": "openai",
            "adapter_name": "langchain_adapter",
        },
    )


@pytest.fixture
def mock_eval_runner(mock_eval, data_source, mock_task):
    return EvalRunner(
        eval_config=EvalConfig(
            name="test",
            model=data_source,
            parent=mock_eval,
            prompt=BasePrompt(
                name="test",
                prompt="test",
            ),
            properties={
                "eval_steps": ["step1", "step2", "step3"],
            },
        ),
        run_configs=[
            TaskRunConfig(
                name="test",
                description="test",
                run_config_properties=RunConfigProperties(
                    model_name="gpt-4",
                    model_provider_name="openai",
                    prompt_id="simple_prompt_builder",
                ),
                parent=mock_task,
            )
        ],
    )


# Test with and without concurrency
@pytest.mark.parametrize("concurrency", [1, 25])
@pytest.mark.asyncio
async def test_async_eval_runner_status_updates(mock_eval_runner, concurrency):
    # Real async testing!

    job_count = 50
    # Job objects are not the right type, but since we're mocking run_job, it doesn't matter
    jobs = [{} for _ in range(job_count)]

    # Mock collect_tasks to return our fake jobs
    mock_eval_runner.collect_tasks = lambda: jobs

    # Mock run_job to return True immediately
    mock_eval_runner.run_job = AsyncMock(return_value=True)

    # Expect the status updates in order, and 1 for each job
    expected_compelted_count = 0
    async for progress in mock_eval_runner.run(concurrency=concurrency):
        assert progress.complete == expected_compelted_count
        expected_compelted_count += 1
        assert progress.errors == 0
        assert progress.total == job_count

    # Verify last status update was complete
    assert expected_compelted_count == job_count + 1

    # Verify run_job was called for each job
    assert mock_eval_runner.run_job.call_count == job_count
