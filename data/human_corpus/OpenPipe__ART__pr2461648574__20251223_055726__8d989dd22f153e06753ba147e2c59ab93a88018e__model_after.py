from openai import AsyncOpenAI
from typing import cast, Iterable, TYPE_CHECKING, Optional

from . import dev
from .openai import patch_openai
from .trajectories import Trajectory, TrajectoryGroup
from .types import TrainableModelName, TrainConfig
from pydantic import BaseModel

if TYPE_CHECKING:
    from .local.api import LocalAPI


class Model(BaseModel):
    name: str
    project: str

    config: BaseModel | None = None

    # These are generally only used on trainable models, but are included on the
    # base because they're sometimes useful for prompted models that you'd like
    # to call via an OpenAI-compatible API as well.
    base_url: str | None = None
    api_key: str | None = None

    trainable: bool = False
    _api: Optional["LocalAPI"] = None


class TrainableModel(Model):
    base_model: TrainableModelName
    trainable: bool = True

    # The fields within `_internal_config` are unstable and subject to change.
    # Use at your own risk.
    _internal_config: dev.InternalModelConfig | None = None
    _openai_client: AsyncOpenAI | None = None

    async def register_for_training(
        self,
        api: "LocalAPI",
        _openai_client_config: dev.OpenAIServerConfig | None = None,
    ) -> None:
        if self.config is not None:
            try:
                self.config.model_dump_json()
            except Exception as e:
                raise ValueError(
                    "The model config cannot be serialized to JSON. Please ensure that all fields are JSON serializable and try again."
                ) from e

        self._api = api
        await self._api.register_for_training(self)
        openai_client = await api._get_openai_client(self, _openai_client_config)
        patch_openai(openai_client)
        self._openai_client = openai_client
        self.base_url = str(openai_client.base_url)
        self.api_key = openai_client.api_key

    def api(self) -> "LocalAPI":
        if self._api is None:
            raise ValueError(
                "Model is not registered with the API. You must call `model.register_for_training()` first."
            )
        return self._api

    def openai_client(
        self,
    ) -> AsyncOpenAI:
        self.api()
        if self._openai_client is None:
            raise ValueError(
                "OpenAI client not yet initialized. You must call `model.register_for_training()` first."
            )
        return self._openai_client

    async def get_step(self) -> int:
        """
        Get the model's current training step.
        """
        return await self.api()._get_step(self)

    async def delete_checkpoints(
        self, best_checkpoint_metric: str = "val/reward"
    ) -> None:
        """
        Delete all but the latest and best checkpoints.

        Args:
            best_checkpoint_metric: The metric to use to determine the best checkpoint.
                Defaults to "val/reward".
        """
        await self.api()._delete_checkpoints(self, best_checkpoint_metric)

    async def log(
        self,
        trajectories: Iterable[Trajectory] | Iterable[TrajectoryGroup],
        split: str = "val",
    ) -> None:
        """
        Log the model's performance for an evaluation batch of trajectories or trajectory groups.

        Args:
            trajectories: A batch of trajectories or trajectory groups.
            split: The evaluation's split. Defaults to "val".
        """
        if any(isinstance(t, Trajectory) for t in trajectories):
            trajectory_groups = [
                TrajectoryGroup(cast(Iterable[Trajectory], trajectories))
            ]
        else:
            trajectory_groups = cast(list[TrajectoryGroup], list(trajectories))
        await self.api()._log(
            self,
            trajectory_groups,
            split,
        )

    async def train(
        self,
        trajectory_groups: Iterable[TrajectoryGroup],
        config: TrainConfig = TrainConfig(),
        _config: dev.TrainConfig | None = None,
    ) -> None:
        """
        Reinforce fine-tune the model with a batch of trajectory groups.

        Args:
            trajectory_groups: A batch of trajectory groups.
            config: Fine-tuning specific configuration
            _config: Additional configuration that is subject to change and
                not yet part of the public API. Use at your own risk.
        """
        await self.api()._train_model(
            self, list(trajectory_groups), config, _config or {}
        )
