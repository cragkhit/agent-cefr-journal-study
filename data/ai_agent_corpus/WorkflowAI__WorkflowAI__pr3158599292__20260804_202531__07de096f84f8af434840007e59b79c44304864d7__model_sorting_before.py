"""Model sorting utilities for MCP service."""

import logging

from api.routers.mcp._mcp_models import ConciseLatestModelResponse, ConciseModelResponse, SortModelBy

logger = logging.getLogger(__name__)


def sort_models(
    models: list[ConciseModelResponse | ConciseLatestModelResponse],
    sort_by: SortModelBy,
) -> list[ConciseModelResponse | ConciseLatestModelResponse]:
    """Sort models based on the specified criteria with stable secondary sorting by model id.

    Args:
        models: List of model responses to sort
        sort_by: Sort criteria
            - "latest_released_first": Sort by release_date (newest first)
            - "smartest_first": Sort by quality_index (highest first)
            - "cheapest_first": Sort by combined input+output cost (lowest first)

    Returns:
        Sorted list of models (modifies in place and returns the list)
    """
    # Separate latest models from concrete models for sorting
    latest_models = [m for m in models if isinstance(m, ConciseLatestModelResponse)]
    concrete_models = [m for m in models if isinstance(m, ConciseModelResponse)]

    if sort_by == "latest_released_first":
        # Sort by release date (newest first), with model id as secondary key for stable ordering
        concrete_models.sort(key=lambda x: (x.release_date, x.id), reverse=True)
    elif sort_by == "smartest_first":
        # Sort by quality index (highest first), with model id as secondary key
        concrete_models.sort(key=lambda x: (x.quality_index, x.id), reverse=True)
    elif sort_by == "cheapest_first":
        # Sort by combined cost (lowest first), with model id as secondary key
        # Note: For cheapest first, we don't use reverse=True because we want lowest cost first
        concrete_models.sort(
            key=lambda x: (x.cost_per_input_token_usd + x.cost_per_output_token_usd, x.id),
            reverse=False,
        )

    # Sort latest models by their id for stable ordering
    latest_models.sort(key=lambda x: x.id)

    # Insert latest models just above the models they point to
    result: list[ConciseModelResponse | ConciseLatestModelResponse] = []
    concrete_models_set = {model.id for model in concrete_models}

    for concrete_model in concrete_models:
        # Find any latest models that point to this concrete model
        pointing_latest_models = [latest for latest in latest_models if latest.currently_points_to == concrete_model.id]

        # Add the latest models first (they appear just above the model they point to)
        result.extend(pointing_latest_models)
        # Then add the concrete model
        result.append(concrete_model)

    # Add any latest models that don't point to concrete models in our list (orphaned latest models)
    orphaned_latest_models = [
        latest for latest in latest_models if latest.currently_points_to not in concrete_models_set
    ]
    if len(orphaned_latest_models) > 0:
        logger.warning(
            "Found orphaned latest models",
            extra={"orphaned_latest_models": orphaned_latest_models},
        )
        result.extend(orphaned_latest_models)

    # Replace the original list contents
    models.clear()
    models.extend(result)

    return models
