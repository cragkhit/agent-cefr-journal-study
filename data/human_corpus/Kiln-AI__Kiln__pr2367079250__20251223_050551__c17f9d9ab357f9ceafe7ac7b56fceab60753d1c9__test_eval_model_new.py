import pytest

from kiln_ai.datamodel.basemodel import KilnParentModel
from kiln_ai.datamodel.eval import (
    Eval,
    EvalConfig,
    EvalConfigType,
    EvalState,
)
from kiln_ai.datamodel.task import Task
from kiln_ai.datamodel.task_output import DataSource, DataSourceType


@pytest.fixture
def mock_task():
    return Task(name="Test Task", instruction="Test instruction")


@pytest.fixture
def valid_eval_config_data():
    return {
        "name": "Test Config",
        "model_provider": "openai",
        "model_name": "gpt-4",
        "config_type": EvalConfigType.g_eval,
        "properties": {"g_eval_steps": ["step1", "step2"]},
    }


def test_eval_state_values():
    assert EvalState.enabled == "enabled"
    assert EvalState.disabled == "disabled"
    assert len(EvalState) == 2


def test_eval_config_type_values():
    assert EvalConfigType.g_eval == "g_eval"
    assert len(EvalConfigType) == 1


@pytest.fixture
def valid_eval_config_data():
    return {
        "name": "Test Config",
        "config_type": EvalConfigType.g_eval,
        "properties": {"g_eval_steps": ["step1", "step2"]},
        "model": DataSource(
            type=DataSourceType.synthetic,
            properties={
                "model_name": "gpt-4",
                "model_provider": "openai",
                "adapter_name": "openai_compatible",
            },
        ),
    }


@pytest.fixture
def valid_eval_config(valid_eval_config_data):
    return EvalConfig(**valid_eval_config_data)


def test_eval_config_valid(valid_eval_config):
    assert valid_eval_config.name == "Test Config"
    assert valid_eval_config.config_type == EvalConfigType.g_eval
    assert valid_eval_config.properties["g_eval_steps"] == ["step1", "step2"]
    assert valid_eval_config.model.type == DataSourceType.synthetic
    assert valid_eval_config.model.properties["model_name"] == "gpt-4"
    assert valid_eval_config.model.properties["model_provider"] == "openai"
    assert valid_eval_config.model.properties["adapter_name"] == "openai_compatible"


def test_eval_config_missing_g_eval_steps(valid_eval_config):
    with pytest.raises(
        ValueError, match="g_eval_steps is required and must be a list for g_eval"
    ):
        valid_eval_config.properties = {}


def test_eval_config_invalid_json(valid_eval_config):
    class InvalidClass:
        pass

    with pytest.raises(ValueError, match="Properties must be JSON serializable"):
        valid_eval_config.properties = {
            "g_eval_steps": [],
            "invalid_key": InvalidClass(),
        }


def test_eval_config_invalid_g_eval_steps_type(valid_eval_config):
    with pytest.raises(
        ValueError, match="g_eval_steps is required and must be a list for g_eval"
    ):
        valid_eval_config.properties = {"g_eval_steps": "not a list"}


def test_eval_config_invalid_config_type(valid_eval_config):
    # Create an invalid config type using string
    with pytest.raises(ValueError):
        valid_eval_config.config_type = "invalid_type"


def test_human_datasource(valid_eval_config):
    with pytest.raises(ValueError):
        valid_eval_config.model.type = DataSourceType.human
        # Not ideal - error isn'd caught until we try to save or set a root field
        valid_eval_config.name = "Test Config"


def test_eval_basic_properties():
    eval = Eval(
        name="Test Eval",
        description="Test Description",
        state=EvalState.enabled,
        current_config_id="config123",
    )

    assert eval.name == "Test Eval"
    assert eval.description == "Test Description"
    assert eval.state == EvalState.enabled
    assert eval.current_config_id == "config123"


def test_eval_default_values():
    eval = Eval(name="Test Eval")

    assert eval.description is None
    assert eval.state == EvalState.enabled
    assert eval.current_config_id is None


def test_eval_parent_task_relationship(mock_task, valid_eval_config_data):
    eval = Eval(name="Test Eval", parent=mock_task)
    config = EvalConfig(parent=eval, **valid_eval_config_data)

    assert eval.parent_task() == mock_task
    assert eval.parent == mock_task
    assert config.parent == eval
    assert config.parent_eval() == eval


def test_eval_parent_task_none():
    eval = Eval(name="Test Eval")
    assert eval.parent_task() is None


def test_eval_parent_task_wrong_type():
    # Create a non-Task parent
    class DummyParent(KilnParentModel, parent_of={}):
        pass

    with pytest.raises(ValueError):
        Eval(name="Test Eval", parent=DummyParent())


def test_eval_with_configs(mock_task, valid_eval_config_data, tmp_path):
    task_path = tmp_path / "task.kiln"
    mock_task.path = task_path
    mock_task.save_to_file()

    eval = Eval(name="Test Eval", parent=mock_task)
    eval.save_to_file()

    # Add config using the parent relationship
    config = EvalConfig(parent=eval, **valid_eval_config_data)
    config.save_to_file()

    # Test configs can be retrieved from disk
    evals = mock_task.evals()
    assert len(evals) == 1
    assert evals[0].name == "Test Eval"
    configs = evals[0].configs()
    assert len(configs) == 1
    assert configs[0].name == "Test Config"
    assert configs[0].model.properties["model_provider"] == "openai"

    # and back up
    assert configs[0].parent_eval().parent_task().path == task_path
