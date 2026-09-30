"""
ML Model wrapper module for Entity Resolution.
Supports LogisticRegression and LightGBM (if installed) with standardization and calibration.
"""
import os
import joblib
from typing import Optional, Dict, Any
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from . import config

logger = config.logger

def create_model(model_type: str = "logistic_regression", random_seed: int = config.RANDOM_SEED) -> Pipeline:
    """
    Instantiates an efficient, robust binary classification pipeline.
    """
    if model_type.lower() in ["lgbm", "lightgbm"]:
        try:
            import lightgbm as lgb
            clf = lgb.LGBMClassifier(
                n_estimators=100,
                learning_rate=0.05,
                max_depth=5,
                random_state=random_seed,
                n_jobs=-1
            )
            return Pipeline([("scaler", StandardScaler()), ("classifier", clf)])
        except ImportError:
            logger.warning("LightGBM not installed. Falling back to LogisticRegression.")
            
    # Default: Scaled Logistic Regression with class_weight='balanced'
    clf = LogisticRegression(
        max_iter=1000,
        C=1.0,
        class_weight="balanced",
        random_state=random_seed,
        solver="lbfgs"
    )
    return Pipeline([("scaler", StandardScaler()), ("classifier", clf)])

def save_model(model: Pipeline, path: str = config.MODEL_PATH) -> None:
    """Serializes the trained pipeline."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(model, path)
    logger.info(f"Model saved to {path}")

def load_model(path: str = config.MODEL_PATH) -> Pipeline:
    """Loads a serialized pipeline."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model file not found: {path}")
    model = joblib.load(path)
    logger.info(f"Loaded model from {path}")
    return model
