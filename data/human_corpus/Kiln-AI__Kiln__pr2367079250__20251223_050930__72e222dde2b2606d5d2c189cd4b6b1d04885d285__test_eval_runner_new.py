from unittest.mock import AsyncMock, patch

import pytest
from kiln_ai.adapters.eval.base_eval import BaseEval
from kiln_ai.adapters.eval.eval_runner import EvalJob, EvalRunner
from kiln_ai.datamodel import (
    BasePrompt,
    DataSource,
    DataSourceType,
    Task,
    TaskOutput,
    TaskRun,
)
from kiln_ai.datamodel.eval import Eval, EvalConfig, EvalRun
from kiln_ai.datamodel.task import RunConfigProperties, TaskRunConfig


@pytest.fixture
def mock_task(tmp_path):
    task = Task(
        name="test",
        description="test",
        instruction="do the thing",
        path=tmp_path / "task.kiln",
    )
    task.save_to_file()
    return task


@pytest.fixture
def mock_eval(mock_task):
    eval = Eval(
        id="test",
        name="test",
        description="test",
        eval_set_filter_id="all",
        eval_configs_filter_id="all",
        parent=mock_task,
    )
    eval.save_to_file()
    return eval


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
def mock_eval_config(mock_eval, data_source):
    eval_config = EvalConfig(
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
    )
    eval_config.save_to_file()
    return eval_config


@pytest.fixture
def mock_run_config(
    mock_task,
):
    rc = TaskRunConfig(
        name="test",
        description="test",
        run_config_properties=RunConfigProperties(
            model_name="gpt-4",
            model_provider_name="openai",
            prompt_id="simple_prompt_builder",
        ),
        parent=mock_task,
    )
    rc.save_to_file()
    return rc


@pytest.fixture
def mock_eval_runner(
    mock_eval, data_source, mock_task, mock_eval_config, mock_run_config
):
    return EvalRunner(
        eval_config=mock_eval_config,
        run_configs=[mock_run_config],
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


def test_collect_tasks_filtering(
    mock_eval_runner, mock_task, mock_eval_config, data_source
):
    """Test that tasks are properly filtered based on eval filters"""
    tags = ["tag1", "tag2", "tag3"]
    task_runs = []
    for tag in tags:
        # Create some task runs with different tags
        task_run = TaskRun(
            parent=mock_task,
            input="test1",
            input_source=data_source,
            output=TaskOutput(
                output="test1",
            ),
            tags=[tag],
        )
        task_run.save_to_file()
        task_runs.append(task_run)

    # Set up filters to only match tag1
    mock_eval_runner.eval.eval_set_filter_id = "tag::tag1"
    mock_eval_runner.eval.eval_configs_filter_id = "tag::tag2"

    jobs = mock_eval_runner.collect_tasks()

    # Should only get task_run1 jobs
    assert len(jobs) == 2
    ids = [job.item.id for job in jobs]
    assert task_runs[0].id in ids
    assert task_runs[1].id in ids
    assert task_runs[2].id not in ids


def test_collect_tasks_excludes_already_run(mock_eval_runner, mock_task, data_source):
    """Test that already run tasks are excluded"""
    # Create a task run
    task_run = TaskRun(
        parent=mock_task,
        input="test",
        input_source=data_source,
        tags=["tag1"],
        output=TaskOutput(
            output="test",
        ),
    )
    task_run.save_to_file()

    # Prior to any eval runs, we should get the task run
    jobs = mock_eval_runner.collect_tasks()
    assert len(jobs) == 1
    assert jobs[0].item.id == task_run.id

    # Create an eval run for this task
    EvalRun(
        parent=mock_eval_runner.eval_config,
        dataset_id=task_run.id,
        task_run_config_id=mock_eval_runner.run_configs[0].id,
        input="test",
        output="test",
        scores={"score": 1.0},
    ).save_to_file()

    # Set filter to match the task
    mock_eval_runner.eval.eval_set_filter_id = "tag::tag1"
    mock_eval_runner.eval.eval_configs_filter_id = "tag::nonexistent"

    jobs = mock_eval_runner.collect_tasks()

    # Should get no jobs since the task was already run
    assert len(jobs) == 0


def test_collect_tasks_multiple_run_configs(
    mock_eval_runner, mock_task, data_source, mock_run_config
):
    """Test handling multiple run configs"""
    # Create a task run
    task_run = TaskRun(
        parent=mock_task,
        input="test",
        input_source=data_source,
        tags=["tag1"],
        output=TaskOutput(
            output="test",
        ),
    )
    task_run.save_to_file()

    # Add another run config
    second_config = TaskRunConfig(
        name="test2",
        description="test2",
        run_config_properties=RunConfigProperties(
            model_name="gpt-3.5",
            model_provider_name="openai",
            prompt_id="simple_prompt_builder",
        ),
        parent=mock_task,
    )
    second_config.save_to_file()
    mock_eval_runner.run_configs.append(second_config)

    # Set filter to match the task
    mock_eval_runner.eval.eval_set_filter_id = "tag::tag1"

    jobs = mock_eval_runner.collect_tasks()

    # Should get 2 jobs, one for each config
    assert len(jobs) == 2
    assert {job.task_run_config.id for job in jobs} == {
        second_config.id,
        mock_run_config.id,
    }


def test_collect_tasks_empty_cases(mock_eval_runner, mock_task, data_source):
    """Test empty cases - no matching tasks or no tasks at all"""
    # Set filter that won't match anything
    mock_eval_runner.eval.eval_set_filter_id = "tag::nonexistent"
    mock_eval_runner.eval.eval_configs_filter_id = "tag::nonexistent"

    jobs = mock_eval_runner.collect_tasks()
    assert len(jobs) == 0

    # Create task run with non-matching tag
    task_run = TaskRun(
        parent=mock_task,
        input="test",
        input_source=data_source,
        tags=["other_tag"],
        output=TaskOutput(
            output="test",
        ),
    )
    task_run.save_to_file()

    jobs = mock_eval_runner.collect_tasks()
    assert len(jobs) == 0


@pytest.mark.asyncio
async def test_run_job_success(
    mock_eval_runner, mock_task, data_source, mock_run_config
):
    # Create a task run to evaluate
    task_run = TaskRun(
        parent=mock_task,
        input="test input",
        input_source=data_source,
        output=TaskOutput(output="test output"),
    )
    task_run.save_to_file()

    # Create eval job
    job = EvalJob(item=task_run, task_run_config=mock_run_config)

    # Mock the evaluator
    mock_result_run = TaskRun(
        input="test input",
        input_source=data_source,
        output=TaskOutput(output="evaluated output"),
    )
    mock_scores = {"accuracy": 0.95}

    class MockEvaluator(BaseEval):
        async def run(self, input_text):
            return mock_result_run, mock_scores

    with patch(
        "kiln_ai.adapters.eval.eval_runner.eval_adapter_from_type",
        return_value=lambda *args: MockEvaluator(*args),
    ):
        success = await mock_eval_runner.run_job(job)

    assert success is True

    # Verify eval run was saved
    eval_runs = mock_eval_runner.eval_config.runs()
    assert len(eval_runs) == 1
    saved_run = eval_runs[0]
    assert saved_run.dataset_id == task_run.id
    assert saved_run.task_run_config_id == mock_run_config.id
    assert saved_run.scores == mock_scores
    assert saved_run.input == "test input"
    assert saved_run.output == "evaluated output"


@pytest.mark.asyncio
async def test_run_job_invalid_evaluator(
    mock_eval_runner, mock_task, data_source, mock_run_config
):
    task_run = TaskRun(
        parent=mock_task,
        input="test input",
        input_source=data_source,
        output=TaskOutput(output="test output"),
    )
    task_run.save_to_file()
    job = EvalJob(item=task_run, task_run_config=mock_run_config)

    # Return an invalid evaluator type
    with patch(
        "kiln_ai.adapters.eval.eval_runner.eval_adapter_from_type",
        return_value=lambda *args: object(),
    ):
        success = await mock_eval_runner.run_job(job)

    assert success is False
    assert len(mock_eval_runner.eval_config.runs()) == 0


@pytest.mark.asyncio
async def test_run_job_evaluator_error(
    mock_eval_runner, mock_task, data_source, mock_run_config
):
    task_run = TaskRun(
        parent=mock_task,
        input="test input",
        input_source=data_source,
        output=TaskOutput(output="test output"),
    )
    task_run.save_to_file()
    job = EvalJob(item=task_run, task_run_config=mock_run_config)

    class ErrorEvaluator(BaseEval):
        async def run(self, input_text):
            raise ValueError("Evaluation failed")

    with patch(
        "kiln_ai.adapters.eval.eval_runner.eval_adapter_from_type",
        return_value=lambda *args: ErrorEvaluator(*args),
    ):
        success = await mock_eval_runner.run_job(job)

    assert success is False
    assert len(mock_eval_runner.eval_config.runs()) == 0
