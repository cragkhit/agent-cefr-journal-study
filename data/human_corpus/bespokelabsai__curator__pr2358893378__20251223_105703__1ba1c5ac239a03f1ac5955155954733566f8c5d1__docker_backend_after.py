"""Docker Code Execution Backend."""

import io
import logging
import os
import tarfile
import tempfile

import docker
from docker.errors import DockerException

from bespokelabs.curator.code_executor.code_execution_backend.base_backend import BaseCodeExecutionBackend
from bespokelabs.curator.code_executor.types import CodeAPIRequest, CodeExecutionOutput, CodeExecutionRequestParams, CodeExecutionResponse

logger = logging.getLogger(__name__)


class DockerCodeExecutionBackend(BaseCodeExecutionBackend):
    """Docker-based code execution backend."""

    PYTHON_IMAGE = "python:3.11-slim"
    WORKSPACE_DIR = "/workspace"

    def __init__(self, config):
        """Initialize the backend."""
        super().__init__(config)
        self.config = config
        self.PYTHON_IMAGE = config.docker_image if config.docker_image else self.PYTHON_IMAGE
        self.client = docker.from_env()
        logger.debug("Initialized Docker backend")

    def _ensure_image(self):
        """Ensure required Docker image is pulled."""
        try:
            self.client.images.get(self.PYTHON_IMAGE)
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling {self.PYTHON_IMAGE} image...")
            self.client.images.pull(self.PYTHON_IMAGE)
        except DockerException as e:
            raise RuntimeError(f"Error ensuring Docker image: {str(e)}") from e

    async def execute_request(self, request: CodeAPIRequest) -> CodeExecutionResponse:
        """Execute a single request in a Docker container."""
        return await self.execute_standard_input_request(
            request.execution_request.code, request.execution_request.code_input, request.execution_request.execution_params
        )

    @classmethod
    def _create_temp_file(cls, content: str) -> str:
        """Create a temporary file with the given content."""
        with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as temp_file:
            temp_file.write(content)
            return temp_file.name

    def _create_tar_archive(self, data: bytes, filename: str) -> io.BytesIO:
        """Create a tar archive containing a single file."""
        tarstream = io.BytesIO()
        with tarfile.TarFile(fileobj=tarstream, mode="w") as tar:
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(data)
            tar.addfile(tarinfo, io.BytesIO(data))
        tarstream.seek(0)
        return tarstream

    def _get_container_file(self, container, file_path: str) -> str:
        """Get content of a file from a Docker container."""
        try:
            bits, _ = container.get_archive(file_path)
            bio = io.BytesIO()
            for chunk in bits:
                bio.write(chunk)
            bio.seek(0)

            with tarfile.open(fileobj=bio) as tar:
                member = tar.next()
                f = tar.extractfile(member)
                if f:
                    return f.read().decode("utf-8")
                return ""

        except docker.errors.NotFound:
            return ""

    def _setup_volume_with_files(self, volume, code_file: str, input_file: str):
        """Set up a volume with code and input files."""
        setup_container = self.client.containers.create(
            self.PYTHON_IMAGE, command=["sleep", "5"], volumes={volume.name: {"bind": self.WORKSPACE_DIR, "mode": "rw"}}
        )

        try:
            setup_container.start()
            for src, dest in [(code_file, "program.py"), (input_file, "input.txt")]:
                with open(src, "rb") as f:
                    data = f.read()
                    tarstream = self._create_tar_archive(data, dest)
                    setup_container.put_archive(self.WORKSPACE_DIR, tarstream)
        finally:
            setup_container.stop()
            setup_container.remove()

    def _get_created_files(self, container: docker.models.containers.Container, directory: str) -> str:
        """Get any files created during code execution."""
        # Get all files in the directory as a tar archive
        bits, _ = container.get_archive(directory, encode_stream=True)
        bio = io.BytesIO()
        for chunk in bits:
            bio.write(chunk)
        bio.seek(0)
        return str(bio.getvalue())

    def _create_execution_container(self, volume_name: str) -> docker.models.containers.Container:
        """Create the main execution container."""
        # TODO: Add a name to the container and volume so that they are unique for a each row
        return self.client.containers.create(
            self.PYTHON_IMAGE,
            command=[  # noqa: E501
                f"bash -c python {self.WORKSPACE_DIR}/program.py < {self.WORKSPACE_DIR}/input.txt > {self.WORKSPACE_DIR}/output.txt 2> {self.WORKSPACE_DIR}/error.txt; echo $? > {self.WORKSPACE_DIR}/exit_code.txt"  # noqa: E501
            ],
            volumes={volume_name: {"bind": self.WORKSPACE_DIR, "mode": "rw"}},
            working_dir=self.WORKSPACE_DIR,
            entrypoint=["/bin/sh", "-c"],
            user="root",
        )

    def _handle_execution_result(self, container, status_code: int) -> CodeExecutionOutput:
        """Handle the execution result and create appropriate output."""
        stdout = self._get_container_file(container, f"{self.WORKSPACE_DIR}/output.txt")
        stderr = self._get_container_file(container, f"{self.WORKSPACE_DIR}/error.txt")
        files = self._get_created_files(container, self.WORKSPACE_DIR)

        if status_code == 0:
            return CodeExecutionOutput(
                message="success",
                stdout=stdout,
                stderr=stderr,
                files=files,
            )

        # Create a more descriptive error message
        error_message = f"Program exited with status code {status_code}"
        if stderr:
            error_message = f"{error_message}\n\nError details:\n{stderr}"

        return CodeExecutionOutput(
            message="error",
            error=error_message,
            stdout=stdout,
            stderr=stderr,
            files=files,
        )

    async def execute_standard_input_request(self, code: str, code_input: str, execution_params: CodeExecutionRequestParams) -> CodeExecutionOutput:
        """Execute code in Docker container."""
        self._ensure_image()

        code_file = self._create_temp_file(code)
        input_file = self._create_temp_file(code_input)
        container = None
        volume = None

        try:
            volume = self.client.volumes.create()
            self._setup_volume_with_files(volume, code_file, input_file)

            container = self._create_execution_container(volume.name)
            container.start()
            result = container.wait(timeout=execution_params.timeout)
            output = self._handle_execution_result(container, result["StatusCode"])

        except docker.errors.ContainerError as e:
            output = CodeExecutionOutput(message="error", error=f"Docker container error: {str(e)}\n\nExit code: {e.exit_status}\n\nStderr: {e.stderr}")
        except docker.errors.ImageNotFound as e:
            output = CodeExecutionOutput(message="error", error=f"Docker image not found: {str(e)}")
        except docker.errors.APIError as e:
            output = CodeExecutionOutput(message="error", error=f"Docker API error: {str(e)}")
        except Exception as e:
            output = CodeExecutionOutput(message="error", error=f"Error during code execution: {str(e)}\n\nType: {type(e).__name__}")
        finally:
            # Clean up but capture any errors during cleanup
            try:
                if container:
                    # Before removing, try to get logs
                    logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
                    if logs and "error" in output.message:
                        output.error += f"\n\nContainer logs:\n{logs}"
                    container.remove(force=True)
                if volume:
                    try:
                        volume.remove(force=True)
                    except Exception as e:
                        logger.warning(f"Error removing volume: {str(e)}")
                for f in [code_file, input_file]:
                    if os.path.exists(f):
                        os.unlink(f)

            except Exception as cleanup_error:
                if "error" in output.message:
                    output.error += f"\n\nCleanup error: {str(cleanup_error)}"

        return output

    async def shutdown(self):
        """Cleanup resources."""
        self.client.close()
        logger.debug("Shutting down Docker backend")
