import pytest
from pydantic import BaseModel, ValidationError

from kiln_ai.datamodel import (
    PromptGenerators,
    PromptId,
)


# Test model to validate the PromptId type
class ModelTester(BaseModel):
    prompt_id: PromptId


def test_valid_prompt_generator_names():
    """Test that valid prompt generator names are accepted"""
    for generator in PromptGenerators:
        model = ModelTester(prompt_id=generator.value)
        assert model.prompt_id == generator.value


def test_valid_saved_prompt_id():
    """Test that valid saved prompt IDs are accepted"""
    valid_id = "id::prompt_789"
    model = ModelTester(prompt_id=valid_id)
    assert model.prompt_id == valid_id


def test_valid_fine_tune_prompt_id():
    """Test that valid fine-tune prompt IDs are accepted"""
    valid_id = "fine_tune_prompt::ft_123456"
    model = ModelTester(prompt_id=valid_id)
    assert model.prompt_id == valid_id


@pytest.mark.parametrize(
    "invalid_id",
    [
        pytest.param("id::project_123::task_456", id="missing_prompt_id"),
        pytest.param("id::task_456::prompt_789", id="too_many_parts"),
        pytest.param("id::", id="empty_parts"),
    ],
)
def test_invalid_saved_prompt_id_format(invalid_id):
    """Test that invalid saved prompt ID formats are rejected"""
    with pytest.raises(ValidationError, match="Invalid saved prompt ID"):
        ModelTester(prompt_id=invalid_id)


@pytest.mark.parametrize(
    "invalid_id,expected_error",
    [
        ("fine_tune_prompt::", "Invalid fine-tune prompt ID: fine_tune_prompt::"),
        ("fine_tune_prompt", "Invalid prompt ID: fine_tune_prompt"),
    ],
)
def test_invalid_fine_tune_prompt_id_format(invalid_id, expected_error):
    """Test that invalid fine-tune prompt ID formats are rejected"""
    with pytest.raises(ValidationError, match=expected_error):
        ModelTester(prompt_id=invalid_id)


def test_completely_invalid_formats():
    """Test that completely invalid formats are rejected"""
    invalid_ids = [
        "",  # Empty string
        "invalid_format",  # Random string
        "id:wrong_format",  # Almost correct but wrong separator
        "fine_tune:wrong_format",  # Almost correct but wrong prefix
        ":::",  # Just separators
    ]

    for invalid_id in invalid_ids:
        with pytest.raises(ValidationError, match="Invalid prompt ID"):
            ModelTester(prompt_id=invalid_id)


def test_prompt_generator_case_sensitivity():
    """Test that prompt generator names are case sensitive"""
    # Take first generator and modify its case
    first_generator = next(iter(PromptGenerators)).value
    wrong_case = first_generator.upper()
    if wrong_case == first_generator:
        wrong_case = first_generator.lower()

    with pytest.raises(ValidationError):
        ModelTester(prompt_id=wrong_case)


@pytest.mark.parametrize(
    "valid_id",
    [
        "eval_prompt::project_123::task_456::eval_789::config_012",  # Valid eval prompt ID
    ],
)
def test_valid_eval_prompt_id(valid_id):
    """Test that valid eval prompt IDs are accepted"""
    model = ModelTester(prompt_id=valid_id)
    assert model.prompt_id == valid_id


@pytest.mark.parametrize(
    "invalid_id,expected_error",
    [
        ("eval_prompt::", "Invalid eval prompt ID"),
        ("eval_prompt::p1::t1", "Invalid eval prompt ID"),
        ("eval_prompt::p1::t1::e1", "Invalid eval prompt ID"),
        ("eval_prompt::p1::t1::e1::c1::extra", "Invalid eval prompt ID"),
    ],
)
def test_invalid_eval_prompt_id_format(invalid_id, expected_error):
    """Test that invalid eval prompt ID formats are rejected"""
    with pytest.raises(ValidationError, match=expected_error):
        ModelTester(prompt_id=invalid_id)
