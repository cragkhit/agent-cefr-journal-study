import pytest
from kiln_ai.adapters.eval.g_eval import GEval
from kiln_ai.datamodel import (
    BasePrompt,
    DataSource,
    DataSourceType,
    Project,
    Task,
    TaskOutput,
    TaskOutputRatingType,
    TaskRequirement,
    TaskRun,
)
from kiln_ai.datamodel.eval import Eval, EvalConfig, EvalConfigType


@pytest.fixture
def test_task(tmp_path):
    project = Project(name="Test Project", path=tmp_path / "project.kiln")
    project.save_to_file()

    task = Task(
        name="Joke Generator",
        instruction="Generate a joke, given a topic",
        parent=project,
        requirements=[
            TaskRequirement(
                name="Topic alignment",
                instruction="Rate how aligned the joke is to the provided topic",
                type=TaskOutputRatingType.five_star,
            ),
            TaskRequirement(
                name="Appropriateness",
                instruction="Check if the content is appropriate for all audiences",
                type=TaskOutputRatingType.pass_fail,
            ),
        ],
    )
    task.save_to_file()
    return task


@pytest.fixture
def test_eval_config(test_task):
    eval = Eval(name="Joke Quality Eval", parent=test_task)
    eval.save_to_file()

    config = EvalConfig(
        name="Llama 8b Joke Generator Eval",
        parent=eval,
        config_type=EvalConfigType.g_eval,
        model=DataSource(
            type=DataSourceType.synthetic,
            properties={
                "model_name": "gpt_4o_mini",
                "model_provider": "openai",
                "adapter_name": "openai_compatible",
            },
        ),
        prompt=BasePrompt(
            # TODO ensure it's called with the frozen prompt
            name="Joke Generator Frozen Prompt",
            prompt=test_task.instruction,
        ),
        properties={
            "g_eval_steps": [
                "Is the joke funny?",
                "Is the content appropriate for all audiences?",
                "Is the joke culturally sensitive?",
                "Is the joke politically correct?",
                "Is the joke aligned with the provided topic?",
            ]
        },
    )
    config.save_to_file()
    return config


@pytest.fixture
def test_task_run(test_task):
    task_run = TaskRun(
        parent=test_task,
        input="Tell me a chicken joke",
        input_source=DataSource(
            type=DataSourceType.human, properties={"created_by": "test_user"}
        ),
        output=TaskOutput(
            output="Why did the chicken cross the road? To get to the other side!",
            source=DataSource(
                type=DataSourceType.synthetic,
                properties={
                    "model_name": "llama_3_1_8b",
                    "model_provider": "groq",
                    "adapter_name": "langchain",
                },
            ),
        ),
    )
    task_run.save_to_file()
    return task_run


@pytest.mark.paid
async def test_run_g_eval(test_task, test_eval_config, test_task_run):
    # Create G-Eval instance
    g_eval = GEval(test_eval_config)

    # Run the evaluation
    eval_result = await g_eval.run_eval(test_task_run)

    # Verify the evaluation results
    assert isinstance(eval_result, dict)
    assert "topic_alignment" in eval_result
    assert isinstance(eval_result["topic_alignment"], int)
    assert 1 <= eval_result["topic_alignment"] <= 5

    assert "appropriateness" in eval_result
    assert eval_result["appropriateness"] in ["pass", "fail"]

    assert "overall_rating" in eval_result
    assert isinstance(eval_result["overall_rating"], int)
    assert 1 <= eval_result["overall_rating"] <= 5


@pytest.mark.paid
async def test_run_g_eval_e2e(test_task, test_eval_config, test_task_run):
    # Create G-Eval instance
    g_eval = GEval(test_eval_config)

    # Run the evaluation
    eval_result = await g_eval.run("chickens")

    # Verify the evaluation results
    assert isinstance(eval_result, dict)
    assert "topic_alignment" in eval_result
    assert isinstance(eval_result["topic_alignment"], int)
    assert 1 <= eval_result["topic_alignment"] <= 5

    assert "appropriateness" in eval_result
    assert eval_result["appropriateness"] in ["pass", "fail"]

    assert "overall_rating" in eval_result
    assert isinstance(eval_result["overall_rating"], int)
    assert 1 <= eval_result["overall_rating"] <= 5
