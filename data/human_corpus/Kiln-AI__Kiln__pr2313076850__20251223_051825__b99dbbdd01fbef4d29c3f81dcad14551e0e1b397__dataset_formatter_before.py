import json
import tempfile
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Protocol
from uuid import uuid4

from kiln_ai.datamodel import DatasetSplit, TaskRun


class DatasetFormat(str, Enum):
    """Formats for dataset generation. Both for file format (like JSONL), and internal structure (like chat/toolcall)"""

    """OpenAI chat format with plaintext response"""
    OPENAI_CHAT_JSONL = "openai_chat_jsonl"

    """OpenAI chat format with json response_format"""
    OPENAI_CHAT_JSON_SCHEMA_JSONL = "openai_chat_json_schema_jsonl"

    """OpenAI chat format with tool call response"""
    OPENAI_CHAT_TOOLCALL_JSONL = "openai_chat_toolcall_jsonl"

    """HuggingFace chat template in JSONL"""
    HUGGINGFACE_CHAT_TEMPLATE_JSONL = "huggingface_chat_template_jsonl"

    """HuggingFace chat template with tool calls in JSONL"""
    HUGGINGFACE_CHAT_TEMPLATE_TOOLCALL_JSONL = (
        "huggingface_chat_template_toolcall_jsonl"
    )

    """Vertex Gemini 1.5 format (flash and pro)"""
    VERTEX_GEMINI_1_5 = "vertex_gemini_1_5"


class FormatGenerator(Protocol):
    """Protocol for format generators"""

    def __call__(self, task_run: TaskRun, system_message: str) -> Dict[str, Any]: ...


def best_task_output(task_run: TaskRun) -> str:
    """Get the best task output from the task run, preferring repaired output if available"""
    if task_run.repaired_output is not None:
        return task_run.repaired_output.output
    return task_run.output.output


def generate_chat_message_response(
    task_run: TaskRun, system_message: str
) -> Dict[str, Any]:
    """Generate OpenAI chat format with plaintext response"""
    return {
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": task_run.input},
            {"role": "assistant", "content": best_task_output(task_run)},
        ]
    }


def generate_json_schema_message(
    task_run: TaskRun, system_message: str
) -> Dict[str, Any]:
    """Generate OpenAI chat format with tool call response"""
    # Load and dump to ensure it's valid JSON and goes to 1 line
    try:
        json_data = json.loads(best_task_output(task_run))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in for tool call: {e}") from e
    json_string = json.dumps(json_data)

    return {
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": task_run.input},
            {"role": "assistant", "content": json_string},
        ]
    }


def generate_chat_message_toolcall(
    task_run: TaskRun, system_message: str
) -> Dict[str, Any]:
    """Generate OpenAI chat format with tool call response"""
    try:
        arguments = json.loads(best_task_output(task_run))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in for tool call: {e}") from e

    return {
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": task_run.input},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "task_response",
                            # Yes we parse then dump again. This ensures it's valid JSON, and ensures it goes to 1 line
                            "arguments": json.dumps(arguments, ensure_ascii=False),
                        },
                    }
                ],
            },
        ]
    }


def generate_huggingface_chat_template(
    task_run: TaskRun, system_message: str
) -> Dict[str, Any]:
    """Generate HuggingFace chat template"""
    return {
        "conversations": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": task_run.input},
            {"role": "assistant", "content": best_task_output(task_run)},
        ]
    }


def generate_huggingface_chat_template_toolcall(
    task_run: TaskRun, system_message: str
) -> Dict[str, Any]:
    """Generate HuggingFace chat template with tool calls"""
    try:
        arguments = json.loads(best_task_output(task_run))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in for tool call: {e}") from e

    # See https://huggingface.co/docs/transformers/en/chat_templating
    return {
        "conversations": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": task_run.input},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "type": "function",
                        "function": {
                            "name": "task_response",
                            "id": str(uuid4()).replace("-", "")[:9],
                            "arguments": arguments,
                        },
                    }
                ],
            },
        ]
    }


def generate_vertex_gemini_1_5(
    task_run: TaskRun, system_message: str
) -> Dict[str, Any]:
    """Generate Vertex Gemini 1.5 format (flash and pro)"""
    # See https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-supervised-tuning-prepare
    return {
        "systemInstruction": {
            "role": "system",
            "parts": [
                {
                    "text": system_message,
                }
            ],
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": task_run.input,
                    }
                ],
            },
            {
                "role": "model",
                "parts": [
                    {
                        "text": best_task_output(task_run),
                    }
                ],
            },
        ],
    }


FORMAT_GENERATORS: Dict[DatasetFormat, FormatGenerator] = {
    DatasetFormat.OPENAI_CHAT_JSONL: generate_chat_message_response,
    DatasetFormat.OPENAI_CHAT_JSON_SCHEMA_JSONL: generate_json_schema_message,
    DatasetFormat.OPENAI_CHAT_TOOLCALL_JSONL: generate_chat_message_toolcall,
    DatasetFormat.HUGGINGFACE_CHAT_TEMPLATE_JSONL: generate_huggingface_chat_template,
    DatasetFormat.HUGGINGFACE_CHAT_TEMPLATE_TOOLCALL_JSONL: generate_huggingface_chat_template_toolcall,
    DatasetFormat.VERTEX_GEMINI_1_5: generate_vertex_gemini_1_5,
}


class DatasetFormatter:
    """Handles formatting of datasets into various output formats"""

    def __init__(self, dataset: DatasetSplit, system_message: str):
        self.dataset = dataset
        self.system_message = system_message

        task = dataset.parent_task()
        if task is None:
            raise ValueError("Dataset has no parent task")
        self.task = task

    def dump_to_file(
        self, split_name: str, format_type: DatasetFormat, path: Path | None = None
    ) -> Path:
        """
        Format the dataset into the specified format.

        Args:
            split_name: Name of the split to dump
            format_type: Format to generate the dataset in
            path: Optional path to write to. If None, writes to temp directory

        Returns:
            Path to the generated file

        Note:
            The output is written in UTF-8 encoding with ensure_ascii=False to properly
            support international text content while maintaining readability.
        """
        if format_type not in FORMAT_GENERATORS:
            raise ValueError(f"Unsupported format: {format_type}")
        if split_name not in self.dataset.split_contents:
            raise ValueError(f"Split {split_name} not found in dataset")

        generator = FORMAT_GENERATORS[format_type]

        # Write to a temp file if no path is provided
        output_path = (
            path
            or Path(tempfile.gettempdir())
            / f"{self.dataset.name}_{split_name}_{format_type}.jsonl"
        )

        runs = self.task.runs()
        runs_by_id = {run.id: run for run in runs}

        # Generate formatted output with UTF-8 encoding
        with open(output_path, "w", encoding="utf-8") as f:
            for run_id in self.dataset.split_contents[split_name]:
                task_run = runs_by_id[run_id]
                if task_run is None:
                    raise ValueError(
                        f"Task run {run_id} not found. This is required by this dataset."
                    )

                example = generator(task_run, self.system_message)
                # Allow non-ascii characters in the dataset.
                # Better readability for non-English users. If you don't support UTF-8... you should.
                f.write(json.dumps(example, ensure_ascii=False) + "\n")

        return output_path
