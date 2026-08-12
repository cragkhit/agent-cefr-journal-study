import json

import pytest
from pydantic import BaseModel, ValidationError

from kiln_ai.adapters.model_adapters.base_adapter import AdapterInfo, BaseAdapter
from kiln_ai.adapters.model_adapters.test_structured_output import (
    build_structured_output_test_task,
)
from kiln_ai.adapters.prompt_builders import (
    EvalPromptBuilder,
    FewShotChainOfThoughtPromptBuilder,
    FewShotPromptBuilder,
    FineTunePromptBuilder,
    MultiShotChainOfThoughtPromptBuilder,
    MultiShotPromptBuilder,
    PromptGenerators,
    PromptId,
    RepairsPromptBuilder,
    SavedPromptBuilder,
    SimpleChainOfThoughtPromptBuilder,
    SimplePromptBuilder,
    chain_of_thought_prompt,
    prompt_builder_from_id,
)
from kiln_ai.adapters.test_prompt_adaptors import build_test_task
from kiln_ai.datamodel import (
    DataSource,
    DataSourceType,
    Finetune,
    FinetuneDataStrategy,
    Project,
    Prompt,
    Task,
    TaskOutput,
    TaskOutputRating,
    TaskRun,
)
from kiln_ai.datamodel.eval import Eval, EvalConfig, EvalConfigType


def test_simple_prompt_builder(tmp_path):
    task = build_test_task(tmp_path)
    builder = SimplePromptBuilder(task=task)
    input = "two plus two"
    prompt = builder.build_prompt(include_json_instructions=False)
    assert (
        "You are an assistant which performs math tasks provided in plain text."
        in prompt
    )

    assert "1) " + task.requirements[0].instruction in prompt
    assert "2) " + task.requirements[1].instruction in prompt
    assert "3) " + task.requirements[2].instruction in prompt

    user_msg = builder.build_user_message(input)
    assert input in user_msg
    assert input not in prompt


class MockAdapter(BaseAdapter):
    def _run(self, input: str) -> str:
        return "mock response"

    def adapter_info(self) -> AdapterInfo:
        return AdapterInfo(
            adapter_name="mock_adapter",
            model_name="mock_model",
            model_provider="mock_provider",
        )


def test_simple_prompt_builder_structured_output(tmp_path):
    task = build_structured_output_test_task(tmp_path)
    builder = SimplePromptBuilder(task=task)
    input = "Cows"
    prompt = builder.build_prompt(include_json_instructions=False)
    assert "You are an assistant which tells a joke, given a subject." in prompt

    user_msg = builder.build_user_message(input)
    assert input in user_msg
    assert input not in prompt


def test_simple_prompt_builder_structured_input_non_ascii(tmp_path):
    task = build_structured_output_test_task(tmp_path)
    builder = SimplePromptBuilder(task=task)
    input = {"key": "你好👋"}
    user_msg = builder.build_user_message(input)
    assert "你好👋" in user_msg


@pytest.fixture
def task_with_examples(tmp_path):
    # Create a project and task hierarchy
    project = Project(name="Test Project", path=(tmp_path / "test_project.kiln"))
    project.save_to_file()
    task = Task(
        name="Test Task",
        instruction="You are an assistant which tells a joke, given a subject.",
        parent=project,
        input_json_schema=json.dumps(
            {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                },
                "required": ["subject"],
            }
        ),
        output_json_schema=json.dumps(
            {
                "type": "object",
                "properties": {"joke": {"type": "string"}},
                "required": ["joke"],
            }
        ),
    )
    task.save_to_file()

    check_example_outputs(task, 0)

    # Create an task input, but with no output
    e1 = TaskRun(
        input='{"subject": "Cows"}',
        input_source=DataSource(
            type=DataSourceType.human,
            properties={"created_by": "john_doe"},
        ),
        parent=task,
        output=TaskOutput(
            output='{"joke": "Moo I am a cow joke."}',
            source=DataSource(
                type=DataSourceType.human,
                properties={"created_by": "john_doe"},
            ),
        ),
    )
    e1.save_to_file()

    ## still zero since not fixed and not rated highly
    check_example_outputs(task, 0)

    e1.output.rating = TaskOutputRating(value=4)
    e1.save_to_file()
    # Now that it's highly rated, it should be included
    check_example_outputs(task, 1)

    # Test with repaired output (highest priority)
    e1 = TaskRun(
        input='{"subject": "Cows"}',
        input_source=DataSource(
            type=DataSourceType.human,
            properties={"created_by": "john_doe"},
        ),
        parent=task,
        output=TaskOutput(
            output='{"joke": "Moo I am a cow joke."}',
            source=DataSource(
                type=DataSourceType.human,
                properties={"created_by": "john_doe"},
            ),
        ),
        repair_instructions="Fix the joke",
        repaired_output=TaskOutput(
            output='{"joke": "Why did the cow cross the road? To get to the udder side!"}',
            source=DataSource(
                type=DataSourceType.human,
                properties={"created_by": "jane_doe"},
            ),
        ),
    )
    e1.save_to_file()
    check_example_outputs(task, 1)

    # Test with high-quality output (second priority)
    e2 = TaskRun(
        input='{"subject": "Dogs"}',
        input_source=DataSource(
            type=DataSourceType.human,
            properties={"created_by": "john_doe"},
        ),
        parent=task,
        output=TaskOutput(
            output='{"joke": "Why did the dog get a job? He wanted to be a collar-ary!"}',
            source=DataSource(
                type=DataSourceType.human,
                properties={"created_by": "john_doe"},
            ),
            rating=TaskOutputRating(value=4, reason="Good pun"),
        ),
    )
    e2.save_to_file()
    check_example_outputs(task, 2)

    # Test sorting by rating value
    e3 = TaskRun(
        input='{"subject": "Cats"}',
        input_source=DataSource(
            type=DataSourceType.human,
            properties={"created_by": "john_doe"},
        ),
        parent=task,
        output=TaskOutput(
            output='{"joke": "Why don\'t cats play poker in the jungle? Too many cheetahs!"}',
            source=DataSource(
                type=DataSourceType.human,
                properties={"created_by": "john_doe"},
            ),
            rating=TaskOutputRating(value=5, reason="Excellent joke"),
        ),
    )
    e3.save_to_file()
    check_example_outputs(task, 3)
    return task


def test_multi_shot_prompt_builder(task_with_examples):
    # Verify the order of examples
    prompt_builder = MultiShotPromptBuilder(task=task_with_examples)
    prompt = prompt_builder.build_prompt(include_json_instructions=False)
    assert "Why did the cow cross the road?" in prompt
    assert prompt.index("Why did the cow cross the road?") < prompt.index(
        "Why don't cats play poker in the jungle?"
    )
    assert prompt.index("Why don't cats play poker in the jungle?") < prompt.index(
        "Why did the dog get a job?"
    )


# Add a new test for the FewShotPromptBuilder
def test_few_shot_prompt_builder(tmp_path):
    # Create a project and task hierarchy (similar to test_multi_shot_prompt_builder)
    project = Project(name="Test Project", path=(tmp_path / "test_project.kiln"))
    project.save_to_file()
    task = Task(
        name="Test Task",
        instruction="You are an assistant which tells a joke, given a subject.",
        parent=project,
        input_json_schema=json.dumps(
            {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                },
                "required": ["subject"],
            }
        ),
        output_json_schema=json.dumps(
            {
                "type": "object",
                "properties": {"joke": {"type": "string"}},
                "required": ["joke"],
            }
        ),
    )
    task.save_to_file()

    # Create 6 examples (2 repaired, 4 high-quality)
    for i in range(6):
        run = TaskRun(
            input=f'{{"subject": "Subject {i + 1}"}}',
            input_source=DataSource(
                type=DataSourceType.human,
                properties={"created_by": "john_doe"},
            ),
            parent=task,
            output=TaskOutput(
                output=f'{{"joke": "Joke Initial Output {i + 1}"}}',
                source=DataSource(
                    type=DataSourceType.human,
                    properties={"created_by": "john_doe"},
                ),
                rating=TaskOutputRating(value=4 + (i % 2), reason="Good joke"),
            ),
        )
        print("RATING", "Joke Initial Output ", i + 1, " - RATED:", 4 + (i % 2), "\n")
        if i < 2:
            run = run.model_copy(
                update={
                    "repair_instructions": "Fix the joke",
                    "repaired_output": TaskOutput(
                        output=f'{{"joke": "Repaired Joke {i + 1}"}}',
                        source=DataSource(
                            type=DataSourceType.human,
                            properties={"created_by": "jane_doe"},
                        ),
                    ),
                }
            )
        run.save_to_file()

    # Check that only 4 examples are included
    prompt_builder = FewShotPromptBuilder(task=task)
    prompt = prompt_builder.build_prompt(include_json_instructions=False)
    assert prompt.count("## Example") == 4

    print("PROMPT", prompt)
    # Verify the order of examples (2 repaired, then 2 highest-rated)
    assert "Repaired Joke 1" in prompt
    assert "Repaired Joke 2" in prompt
    assert "Joke Initial Output 6" in prompt  # Rating 5
    assert "Joke Initial Output 4" in prompt  # Rating 5
    assert "Joke Initial Output 5" not in prompt  # Rating 4, not included
    assert "Joke Initial Output 3" not in prompt  # Rating 4, not included
    assert "Joke Initial Output 1" not in prompt  # Repaired, so using that
    assert "Joke Initial Output 2" not in prompt  # Repaired, so using that


def check_example_outputs(task: Task, count: int):
    prompt_builder = MultiShotPromptBuilder(task=task)
    prompt = prompt_builder.build_prompt(include_json_instructions=False)
    assert "# Instruction" in prompt
    assert task.instruction in prompt
    if count == 0:
        assert "# Example Outputs" not in prompt
    else:
        assert "# Example Outputs" in prompt
        assert f"## Example {count}" in prompt


def test_prompt_builder_name():
    assert SimplePromptBuilder.prompt_builder_name() == "simple_prompt_builder"
    assert MultiShotPromptBuilder.prompt_builder_name() == "multi_shot_prompt_builder"
    assert RepairsPromptBuilder.prompt_builder_name() == "repairs_prompt_builder"


def test_prompt_builder_from_id(task_with_examples):
    task = task_with_examples
    assert isinstance(
        prompt_builder_from_id("simple_prompt_builder", task), SimplePromptBuilder
    )
    assert isinstance(
        prompt_builder_from_id("few_shot_prompt_builder", task),
        FewShotPromptBuilder,
    )
    assert isinstance(
        prompt_builder_from_id("multi_shot_prompt_builder", task),
        MultiShotPromptBuilder,
    )
    assert isinstance(
        prompt_builder_from_id("repairs_prompt_builder", task),
        RepairsPromptBuilder,
    )
    assert isinstance(
        prompt_builder_from_id("simple_chain_of_thought_prompt_builder", task),
        SimpleChainOfThoughtPromptBuilder,
    )
    assert isinstance(
        prompt_builder_from_id("few_shot_chain_of_thought_prompt_builder", task),
        FewShotChainOfThoughtPromptBuilder,
    )
    assert isinstance(
        prompt_builder_from_id("multi_shot_chain_of_thought_prompt_builder", task),
        MultiShotChainOfThoughtPromptBuilder,
    )

    with pytest.raises(ValueError, match="Unknown prompt generator: invalid_name"):
        prompt_builder_from_id("invalid_name", task)

    with pytest.raises(ValueError, match="Prompt ID not found: 123"):
        prompt_builder_from_id("id::123", task)

    with pytest.raises(
        ValueError,
        match="Invalid fine-tune ID format. Expected 'project_id::task_id::fine_tune_id'",
    ):
        prompt_builder_from_id("fine_tune_prompt::123", task)

    with pytest.raises(
        ValueError,
        match="Fine-tune ID not found",
    ):
        prompt_builder_from_id("fine_tune_prompt::123::456::789", task)

    prompt = Prompt(
        name="test_prompt_name",
        prompt="test_prompt",
        chain_of_thought_instructions="coti",
        parent=task,
    )
    prompt.save_to_file()
    pb = prompt_builder_from_id("id::" + prompt.id, task)
    assert isinstance(pb, SavedPromptBuilder)
    assert pb.prompt_id() == prompt.id
    assert pb.build_prompt(include_json_instructions=False) == "test_prompt"
    assert pb.chain_of_thought_prompt() == "coti"

    finetune = Finetune(
        name="test_finetune_name",
        system_message="test_system_message",
        thinking_instructions="test_thinking_instructions",
        parent=task,
        base_model_id="test_base_model_id",
        dataset_split_id="asdf",
        provider="test_provider",
        data_strategy=FinetuneDataStrategy.final_and_intermediate,
    )
    finetune.save_to_file()
    nested_fine_tune_id = (
        task_with_examples.parent.id + "::" + task_with_examples.id + "::" + finetune.id
    )
    pb = prompt_builder_from_id(
        "fine_tune_prompt::" + nested_fine_tune_id,
        task_with_examples,
    )
    assert isinstance(pb, FineTunePromptBuilder)
    assert pb.prompt_id() == nested_fine_tune_id
    assert pb.build_base_prompt() == "test_system_message"
    assert pb.chain_of_thought_prompt() == "test_thinking_instructions"


def test_example_count():
    assert FewShotPromptBuilder.example_count() == 4
    assert MultiShotPromptBuilder.example_count() == 25


def test_repair_multi_shot_prompt_builder(task_with_examples):
    # Verify the order of examples
    prompt_builder = RepairsPromptBuilder(task=task_with_examples)
    prompt = prompt_builder.build_prompt(include_json_instructions=False)
    assert (
        'Repaired Output Which is Sufficient: {"joke": "Why did the cow cross the road? To get to the udder side!"}'
        in prompt
    )
    assert "Instructions On How to Improve the Initial Output: Fix the joke" in prompt
    assert (
        'Initial Output Which Was Insufficient: {"joke": "Moo I am a cow joke."}'
        in prompt
    )


def test_chain_of_thought_prompt(tmp_path):
    # Test with default thinking instruction
    task = Task(
        name="Test Task",
        instruction="Test instruction",
        parent=None,
        thinking_instruction=None,
    )
    assert (
        chain_of_thought_prompt(task)
        == "Think step by step, explaining your reasoning."
    )

    # Test with custom thinking instruction
    custom_instruction = "First analyze the problem, then break it down into steps."
    task = Task(
        name="Test Task",
        instruction="Test instruction",
        parent=None,
        thinking_instruction=custom_instruction,
    )
    assert chain_of_thought_prompt(task) == custom_instruction


@pytest.mark.parametrize(
    "builder_class",
    [
        SimpleChainOfThoughtPromptBuilder,
        FewShotChainOfThoughtPromptBuilder,
        MultiShotChainOfThoughtPromptBuilder,
    ],
)
def test_chain_of_thought_prompt_builders(builder_class, task_with_examples):
    # Test with default thinking instruction
    builder = builder_class(task=task_with_examples)
    assert (
        builder.chain_of_thought_prompt()
        == "Think step by step, explaining your reasoning."
    )

    # Test with custom thinking instruction
    custom_instruction = "First analyze the problem, then break it down into steps."
    task_with_custom = task_with_examples.model_copy(
        update={"thinking_instruction": custom_instruction}
    )
    builder = builder_class(task=task_with_custom)
    assert builder.chain_of_thought_prompt() == custom_instruction


def test_build_prompt_for_ui(tmp_path):
    # Test regular prompt builder
    task = build_test_task(tmp_path)
    simple_builder = SimplePromptBuilder(task=task)
    ui_prompt = simple_builder.build_prompt_for_ui()

    # Should match regular prompt since no chain of thought
    assert ui_prompt == simple_builder.build_prompt(include_json_instructions=False)
    assert "# Thinking Instructions" not in ui_prompt

    # Test chain of thought prompt builder
    cot_builder = SimpleChainOfThoughtPromptBuilder(task=task)
    ui_prompt_cot = cot_builder.build_prompt_for_ui()

    # Should include both base prompt and thinking instructions
    assert cot_builder.build_prompt(include_json_instructions=False) in ui_prompt_cot
    assert "# Thinking Instructions" in ui_prompt_cot
    assert "Think step by step" in ui_prompt_cot

    # Test with custom thinking instruction
    custom_instruction = "First analyze the problem, then solve it."
    task_with_custom = task.model_copy(
        update={"thinking_instruction": custom_instruction}
    )
    custom_cot_builder = SimpleChainOfThoughtPromptBuilder(task=task_with_custom)
    ui_prompt_custom = custom_cot_builder.build_prompt_for_ui()

    assert (
        custom_cot_builder.build_prompt(include_json_instructions=False)
        in ui_prompt_custom
    )
    assert "# Thinking Instructions" in ui_prompt_custom
    assert custom_instruction in ui_prompt_custom


def test_saved_prompt_builder(tmp_path):
    task = build_test_task(tmp_path)

    prompt = Prompt(
        name="test_prompt_name",
        prompt="test_prompt",
        parent=task,
    )
    prompt.save_to_file()

    builder = SavedPromptBuilder(task=task, prompt_id=prompt.id)
    assert builder.build_prompt(include_json_instructions=False) == "test_prompt"
    assert builder.chain_of_thought_prompt() is None
    assert builder.build_prompt_for_ui() == "test_prompt"
    assert builder.prompt_id() == prompt.id


def test_saved_prompt_builder_with_chain_of_thought(tmp_path):
    task = build_test_task(tmp_path)

    prompt = Prompt(
        name="test_prompt_name",
        prompt="test_prompt",
        chain_of_thought_instructions="Think step by step",
        parent=task,
    )
    prompt.save_to_file()

    builder = SavedPromptBuilder(task=task, prompt_id=prompt.id)
    assert builder.build_prompt(include_json_instructions=False) == "test_prompt"
    assert builder.chain_of_thought_prompt() == "Think step by step"
    assert "Think step by step" in builder.build_prompt_for_ui()
    assert builder.prompt_id() == prompt.id


def test_saved_prompt_builder_not_found(tmp_path):
    task = build_test_task(tmp_path)

    with pytest.raises(ValueError, match="Prompt ID not found: 123"):
        SavedPromptBuilder(task=task, prompt_id="123")


def test_build_prompt_with_json_instructions(tmp_path):
    task = build_test_task(tmp_path)
    task = task.model_copy(
        update={
            "output_json_schema": json.dumps(
                {
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                    "required": ["result"],
                }
            )
        }
    )

    builder = SimplePromptBuilder(task=task)

    # Test without JSON instructions
    prompt_without_json = builder.build_prompt(include_json_instructions=False)
    assert "Format Instructions" not in prompt_without_json
    assert (
        "Return a JSON object conforming to the following schema:"
        not in prompt_without_json
    )
    assert task.output_json_schema not in prompt_without_json

    # Test with JSON instructions
    prompt_with_json = builder.build_prompt(include_json_instructions=True)
    assert "# Format Instructions" in prompt_with_json
    assert (
        "Return a JSON object conforming to the following schema:" in prompt_with_json
    )
    assert "```" in prompt_with_json
    assert (
        "{'type': 'object', 'properties': {'result': {'type': 'string'}}, 'required': ['result']}"
        in prompt_with_json
    )

    # Verify base prompt is still included
    assert task.instruction in prompt_with_json
    for requirement in task.requirements:
        assert requirement.instruction in prompt_with_json


# Test model to validate the PromptId type
class TestModel(BaseModel):
    prompt_id: PromptId


def test_valid_prompt_generator_names():
    """Test that valid prompt generator names are accepted"""
    for generator in PromptGenerators:
        model = TestModel(prompt_id=generator.value)
        assert model.prompt_id == generator.value


def test_valid_saved_prompt_id():
    """Test that valid saved prompt IDs are accepted"""
    valid_id = "id::project_123::task_456::prompt_789"
    model = TestModel(prompt_id=valid_id)
    assert model.prompt_id == valid_id


def test_valid_fine_tune_prompt_id():
    """Test that valid fine-tune prompt IDs are accepted"""
    valid_id = "fine_tune_prompt::ft_123456"
    model = TestModel(prompt_id=valid_id)
    assert model.prompt_id == valid_id


@pytest.mark.parametrize(
    "invalid_id",
    [
        pytest.param("id::project_123::task_456", id="missing_prompt_id"),
        pytest.param(
            "id::project_123::task_456::prompt_789::extra", id="too_many_parts"
        ),
        pytest.param("id::", id="empty_parts"),
        pytest.param("id::project_123", id="too_few_parts"),
    ],
)
def test_invalid_saved_prompt_id_format(invalid_id):
    """Test that invalid saved prompt ID formats are rejected"""
    with pytest.raises(ValidationError, match="Invalid saved prompt ID"):
        TestModel(prompt_id=invalid_id)


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
        TestModel(prompt_id=invalid_id)


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
            TestModel(prompt_id=invalid_id)


def test_prompt_generator_case_sensitivity():
    """Test that prompt generator names are case sensitive"""
    # Take first generator and modify its case
    first_generator = next(iter(PromptGenerators)).value
    wrong_case = first_generator.upper()
    if wrong_case == first_generator:
        wrong_case = first_generator.lower()

    with pytest.raises(ValidationError):
        TestModel(prompt_id=wrong_case)


@pytest.fixture
def valid_eval_config_datasource():
    return DataSource(
        type=DataSourceType.synthetic,
        properties={
            "model_name": "gpt-4",
            "model_provider": "openai",
            "adapter_name": "openai_compatible",
        },
    )


def test_eval_prompt_builder(tmp_path, valid_eval_config_datasource):
    task = build_test_task(tmp_path)

    # Create an eval and eval config
    eval = Eval(
        name="test_eval",
        parent=task,
    )
    eval.save_to_file()

    eval_config = EvalConfig(
        name="test_eval_config",
        parent=eval,
        config_type=EvalConfigType.g_eval,
        model=valid_eval_config_datasource,
        prompt=Prompt(
            name="test_prompt",
            prompt="test_eval_prompt",
            chain_of_thought_instructions="Think carefully",
        ),
        properties={"g_eval_steps": ["step1", "step2"]},
    )
    eval_config.save_to_file()

    # Construct the eval prompt ID
    eval_prompt_id = (
        f"eval_prompt::{task.parent.id}::{task.id}::{eval.id}::{eval_config.id}"
    )

    # Test successful creation, constructor and ID creation
    builders = [
        EvalPromptBuilder(task=task, eval_config_prompt_id=eval_prompt_id),
        prompt_builder_from_id(eval_prompt_id, task),
    ]

    for builder in builders:
        assert (
            builder.build_prompt(include_json_instructions=False) == "test_eval_prompt"
        )
        assert builder.chain_of_thought_prompt() == "Think carefully"
        assert builder.prompt_id() == eval_prompt_id

    # test accessor


def test_eval_prompt_builder_validation_errors(tmp_path):
    task = build_test_task(tmp_path)

    # Test invalid format
    with pytest.raises(ValueError, match="Invalid eval prompt ID"):
        EvalPromptBuilder(task=task, eval_config_prompt_id="eval_prompt::wrong::format")

    # Test task ID mismatch
    wrong_task_id = f"eval_prompt::{task.parent.id}::wrong_task_id::eval_id::config_id"
    with pytest.raises(ValueError, match="Task ID mismatch"):
        EvalPromptBuilder(task=task, eval_config_prompt_id=wrong_task_id)

    # Test eval not found
    nonexistent_eval = (
        f"eval_prompt::{task.parent.id}::{task.id}::nonexistent_eval::config_id"
    )
    with pytest.raises(ValueError, match="Eval ID not found"):
        EvalPromptBuilder(task=task, eval_config_prompt_id=nonexistent_eval)

    # Create eval but test config not found
    eval = Eval(
        name="test_eval",
        parent=task,
    )
    eval.save_to_file()

    nonexistent_config = (
        f"eval_prompt::{task.parent.id}::{task.id}::{eval.id}::nonexistent_config"
    )
    with pytest.raises(ValueError, match="Eval config ID not found"):
        EvalPromptBuilder(task=task, eval_config_prompt_id=nonexistent_config)


@pytest.mark.parametrize(
    "valid_id",
    [
        "eval_prompt::project_123::task_456::eval_789::config_012",  # Valid eval prompt ID
    ],
)
def test_valid_eval_prompt_id(valid_id):
    """Test that valid eval prompt IDs are accepted"""
    model = TestModel(prompt_id=valid_id)
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
        TestModel(prompt_id=invalid_id)
