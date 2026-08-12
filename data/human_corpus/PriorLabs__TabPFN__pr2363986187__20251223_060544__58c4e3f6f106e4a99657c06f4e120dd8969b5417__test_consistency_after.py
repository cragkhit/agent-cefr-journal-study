"""Model consistency tests for TabPFN.

These tests verify that TabPFN models produce consistent predictions across code
changes. If predictions change significantly, tests will fail, prompting the developer
to verify that the changes are legitimate improvements.

This approach uses small, fixed datasets with reproducible random seeds to ensure
consistency across code changes. Each test case maintains its own reference file.

Platform Considerations:
-----------------------
Reference predictions are platform-specific. Tests pass only on matching platforms.
Set FORCE_CONSISTENCY_TESTS=1 environment variable to override this restriction.

If you need to update reference values:
1. Run: python tests/test_consistency.py
2. Include the updated reference files in your PR
3. Document the reason for the update in your PR description

How It Works:
------------
Each test is a subclass of ConsistencyTest that defines:
1. The dataset to use (via get_test_data)
2. The model configuration (via get_model)
3. How to extract predictions (via get_prediction_func)

When run, each test:
1. Creates a model
2. Fits it to a fixed dataset
3. Compares the predictions to previously saved references
4. Fails if predictions differ beyond tolerance thresholds

This design ensures tight coupling between test implementation and reference
generation, making it easier to maintain and extend the test suite.
"""

from __future__ import annotations

import contextlib
import json
import os
import pathlib
import platform

import numpy as np
import pytest
from sklearn.utils import check_random_state

# mypy: ignore-errors
from tabpfn import TabPFNClassifier, TabPFNRegressor  # type: ignore

# Test configuration parameters
DEFAULT_N_ESTIMATORS = 2  # Small number for quick tests
TEST_TOLERANCE_RTOL = 1e-3  # 0.1% relative tolerance
TEST_TOLERANCE_ATOL = 1e-3  # 0.001 absolute tolerance

# Sample configuration
# Fixed seeds and indices make tests more stable and predictable
FIXED_RANDOM_SEED = 42  # Always use the same random seed for reproducibility

# Reference platform settings
REFERENCE_OS = "Darwin"  # macOS
REFERENCE_PYTHON_VERSION = "3.10"  # Update when regenerating reference predictions

# Platform-specific test decorator
platform_specific = pytest.mark.skipif(
    os.environ.get("FORCE_CONSISTENCY_TESTS", "0") != "1"
    and not (
        platform.system() == REFERENCE_OS
        and platform.python_version().startswith(REFERENCE_PYTHON_VERSION)
    ),
    reason=f"Tests require {REFERENCE_OS} with Python {REFERENCE_PYTHON_VERSION}",
)


# Test data generators for reproducible datasets
def get_tiny_classification_data():
    """Get a tiny fixed classification dataset for testing."""
    random_state = check_random_state(FIXED_RANDOM_SEED)
    X = random_state.rand(10, 5)  # 10 samples, 5 features
    y = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1])  # Binary classification

    # Split into train/test
    X_train, X_test = X[:7], X[7:]
    y_train = y[:7]

    return X_train, y_train, X_test


def get_tiny_regression_data():
    """Get a tiny fixed regression dataset for testing."""
    random_state = check_random_state(FIXED_RANDOM_SEED)
    X = random_state.rand(10, 5)  # 10 samples, 5 features
    y = random_state.rand(10) * 10  # Continuous target

    # Split into train/test
    X_train, X_test = X[:7], X[7:]
    y_train = y[:7]

    return X_train, y_train, X_test


def get_iris_multiclass_data():
    """Get a small subset of iris data for multiclass testing."""
    from sklearn.datasets import load_iris

    # Load iris dataset with 3 well-separated classes
    X, y = load_iris(return_X_y=True)

    # Use fixed test samples (first sample of each class)
    test_indices = [0, 50, 100]  # First sample of each class

    # Use fixed training samples (samples 1-6 from each class)
    train_indices = []
    for base in [0, 50, 100]:  # Start of each class
        train_indices.extend([base + i for i in range(1, 7)])  # 6 samples per class

    X_train, X_test = X[train_indices], X[test_indices]
    y_train, _y_test = y[train_indices], y[test_indices]

    return X_train, y_train, X_test


def get_ensemble_data():
    """Get a fixed dataset for ensemble testing."""
    # Use the tiny classification dataset but with a larger ensemble
    return get_tiny_classification_data()


class ConsistencyTest:
    """Base class for model consistency tests.

    Each test case should subclass this and implement:
    1. get_dataset_name() - returns the unique name for the test case
    2. get_test_data() - returns (X_train, y_train, X_test) tuple
    3. get_model() - returns the TabPFN model to test with
    4. get_prediction_func() - returns function to get predictions

    This design ensures tight coupling between test generation and execution.
    """

    # Reference predictions directory
    REFERENCE_DIR = pathlib.Path(__file__).parent / "reference_predictions"

    @classmethod
    def setup_class(cls):
        """Ensure the reference predictions directory exists."""
        cls.REFERENCE_DIR.mkdir(exist_ok=True)

    def get_dataset_name(self):
        """Get the unique name for this test case."""
        raise NotImplementedError("Subclasses must implement get_dataset_name()")

    def get_test_data(self):
        """Get the test data tuple (X_train, y_train, X_test)."""
        raise NotImplementedError("Subclasses must implement get_test_data()")

    def get_model(self):
        """Get the model instance to test."""
        raise NotImplementedError("Subclasses must implement get_model()")

    def get_prediction_func(self):
        """Get the function to extract predictions from the model."""
        raise NotImplementedError("Subclasses must implement get_prediction_func()")

    def get_reference_path(self):
        """Get the path to the reference prediction file for this test."""
        return self.REFERENCE_DIR / f"{self.get_dataset_name()}_predictions.json"

    def save_reference(self, predictions):
        """Save predictions as reference for this test."""
        path = self.get_reference_path()
        with path.open("w") as f:
            json.dump(predictions.tolist(), f, indent=2)

    def load_reference(self):
        """Load reference predictions for this test."""
        path = self.get_reference_path()
        if not path.exists():
            return None
        with path.open("r") as f:
            return np.array(json.load(f))

    def run_test(self, *, override=False):
        """Run the consistency test.

        Args:
            override: If True, force update reference predictions

        Returns:
            predictions: The model predictions
        """
        # Get test data and model
        X_train, y_train, X_test = self.get_test_data()
        model = self.get_model()

        # Fit model
        model.fit(X_train, y_train)

        # Get predictions
        prediction_func = self.get_prediction_func()
        predictions = prediction_func(model, X_test)

        # Handle reference
        ref_path = self.get_reference_path()
        if override:
            self.save_reference(predictions)
            return predictions

        # Compare with reference
        reference = self.load_reference()
        if reference is None:
            # Save current predictions as reference
            self.save_reference(predictions)
            pytest.skip(f"Created new reference predictions at {ref_path}")
            return predictions

        # Compare with consistent tolerance settings
        np.testing.assert_allclose(
            predictions,
            reference,
            rtol=TEST_TOLERANCE_RTOL,
            atol=TEST_TOLERANCE_ATOL,
            err_msg=(
                f"Predictions for {self.get_dataset_name()} have changed.\n"
                f"If this change is intentional:\n"
                f"1. Verify the changes improve model performance\n"
                f"2. Delete the reference file at {ref_path} to update it\n"
                f"3. Document the improvement in your PR description\n"
            ),
        )
        return predictions


class TestTinyClassifier(ConsistencyTest):
    """Test prediction consistency for a tiny binary classifier."""

    def get_dataset_name(self):
        return "tiny_classifier"

    def get_test_data(self):
        return get_tiny_classification_data()

    def get_model(self):
        return TabPFNClassifier(
            n_estimators=DEFAULT_N_ESTIMATORS,
            random_state=FIXED_RANDOM_SEED,
            device="cpu",
        )

    def get_prediction_func(self):
        return lambda model, X: model.predict_proba(X)

    @platform_specific
    def test_consistency(self):
        """Test prediction consistency on a very small classification dataset."""
        self.run_test()


class TestTinyRegressor(ConsistencyTest):
    """Test prediction consistency for a tiny regressor."""

    def get_dataset_name(self):
        return "tiny_regressor"

    def get_test_data(self):
        return get_tiny_regression_data()

    def get_model(self):
        return TabPFNRegressor(
            n_estimators=DEFAULT_N_ESTIMATORS,
            random_state=FIXED_RANDOM_SEED,
            device="cpu",
        )

    def get_prediction_func(self):
        return lambda model, X: model.predict(X)

    @platform_specific
    def test_consistency(self):
        """Test prediction consistency on a very small regression dataset."""
        self.run_test()


class TestMulticlassClassifier(ConsistencyTest):
    """Test prediction consistency for a multiclass classifier."""

    def get_dataset_name(self):
        return "iris_multiclass"

    def get_test_data(self):
        return get_iris_multiclass_data()

    def get_model(self):
        return TabPFNClassifier(
            n_estimators=DEFAULT_N_ESTIMATORS,
            random_state=FIXED_RANDOM_SEED,
            device="cpu",
        )

    def get_prediction_func(self):
        return lambda model, X: model.predict_proba(X)

    @platform_specific
    def test_consistency(self):
        """Test prediction consistency on iris multiclass dataset."""
        self.run_test()


class TestEnsembleClassifier(ConsistencyTest):
    """Test prediction consistency for a classifier with larger ensemble."""

    def get_dataset_name(self):
        return "ensemble_classifier"

    def get_test_data(self):
        return get_ensemble_data()

    def get_model(self):
        return TabPFNClassifier(
            n_estimators=5,  # Larger ensemble for this test
            random_state=FIXED_RANDOM_SEED,
            device="cpu",
        )

    def get_prediction_func(self):
        return lambda model, X: model.predict_proba(X)

    @platform_specific
    def test_consistency(self):
        """Test prediction consistency with larger ensemble."""
        self.run_test()


def update_reference_predictions():
    """Generate and save reference predictions for all test cases.

    Uses the same test classes as the actual tests to ensure consistency.
    """
    # Ensure reference dir exists
    ref_dir = ConsistencyTest.REFERENCE_DIR
    ref_dir.mkdir(exist_ok=True)

    # Clear existing reference files
    for path in ref_dir.glob("*_predictions.json"):
        path.unlink()

    # Create and update references for each test case
    test_cases = [
        TestTinyClassifier(),
        TestTinyRegressor(),
        TestMulticlassClassifier(),
        TestEnsembleClassifier(),
    ]

    for test_case in test_cases:
        with contextlib.suppress(Exception):
            test_case.run_test(override=True)


if __name__ == "__main__":
    # Running this file directly will update reference predictions
    update_reference_predictions()
