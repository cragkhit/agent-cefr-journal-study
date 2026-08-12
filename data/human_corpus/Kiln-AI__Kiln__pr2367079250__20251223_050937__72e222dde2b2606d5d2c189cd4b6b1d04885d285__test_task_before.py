import pytest
from pydantic import ValidationError

from kiln_ai.datamodel.prompt_id import PromptGenerators
from kiln_ai.datamodel.task import RunConfig, Task, TaskRunConfig


def test_runconfig_valid_creation():
    task = Task(id="task1", name="Test Task", instruction="Do something")

    config = RunConfig(task=task, model_name="gpt-4", model_provider_name="openai")

    assert config.task == task
    assert config.model_name == "gpt-4"
    assert config.model_provider_name == "openai"
    assert config.prompt_id == PromptGenerators.SIMPLE  # Check default value


def test_runconfig_missing_required_fields():
    with pytest.raises(ValidationError) as exc_info:
        RunConfig()

    errors = exc_info.value.errors()
    assert len(errors) == 3  # task, model_name, and model_provider_name are required
    assert any(error["loc"][0] == "task" for error in errors)
    assert any(error["loc"][0] == "model_name" for error in errors)
    assert any(error["loc"][0] == "model_provider_name" for error in errors)


def test_runconfig_custom_prompt_id():
    task = Task(id="task1", name="Test Task", instruction="Do something")

    config = RunConfig(
        task=task,
        model_name="gpt-4",
        model_provider_name="openai",
        prompt_id=PromptGenerators.SIMPLE_CHAIN_OF_THOUGHT,
    )

    assert config.prompt_id == PromptGenerators.SIMPLE_CHAIN_OF_THOUGHT


@pytest.fixture
def sample_task():
    return Task(name="Test Task", instruction="Test instruction")


@pytest.fixture
def sample_run_config(sample_task):
    return RunConfig(task=sample_task, model_name="gpt-4", model_provider_name="openai")


def test_task_run_config_valid_creation(sample_task, sample_run_config):
    config = TaskRunConfig(
        name="Test Config",
        description="Test description",
        run_config=sample_run_config,
        parent=sample_task,
    )

    assert config.name == "Test Config"
    assert config.description == "Test description"
    assert config.run_config == sample_run_config
    assert config.parent_task() == sample_task


def test_task_run_config_minimal_creation(sample_task, sample_run_config):
    # Test creation with only required fields
    config = TaskRunConfig(
        name="Test Config", run_config=sample_run_config, parent=sample_task
    )

    assert config.name == "Test Config"
    assert config.description is None
    assert config.run_config == sample_run_config


def test_task_run_config_missing_required_fields(sample_task):
    # Test missing name
    with pytest.raises(ValidationError) as exc_info:
        TaskRunConfig(
            run_config=RunConfig(
                task=sample_task, model_name="gpt-4", model_provider_name="openai"
            ),
            parent=sample_task,
        )
    assert "Field required" in str(exc_info.value)

    # Test missing run_config
    with pytest.raises(ValidationError) as exc_info:
        TaskRunConfig(name="Test Config", parent=sample_task)
    assert "Field required" in str(exc_info.value)


def test_task_run_config_task_mismatch(sample_task, sample_run_config):
    # Create a different task
    different_task = Task(name="Different Task", instruction="Different instruction")

    # Test run_config task different from parent task
    with pytest.raises(ValueError, match="Run config task must match parent task"):
        TaskRunConfig(
            name="Test Config", run_config=sample_run_config, parent=different_task
        )


def test_task_run_config_missing_task_in_run_config(sample_task):
    with pytest.raises(
        ValidationError, match="Input should be a valid dictionary or instance of Task"
    ):
        # Create a run config without a task
        RunConfig(
            model_name="gpt-4",
            model_provider_name="openai",
            task=None,  # type: ignore
        )
