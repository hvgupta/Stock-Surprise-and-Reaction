from backend.logger import get_configured_logger
logger = get_configured_logger(__name__)

import optuna
import pandas as pd

from sklearn.metrics import (
    mean_squared_error,
    r2_score
)
from typing import Dict, List
from sklearn.model_selection import (
    train_test_split,
    KFold,
    cross_val_score
)
from sklearn.ensemble import GradientBoostingRegressor



def train_GradientBoostModel(final_dataset: List[Dict]):

    df = pd.DataFrame(final_dataset).dropna()

    X = df.drop(columns=["reaction"])
    y = df["reaction"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )


    def objective(trial):

        params = {
            "n_estimators": trial.suggest_int(
                "n_estimators",
                50,
                500,
                step=10
            ),
            "learning_rate": trial.suggest_float(
                "learning_rate",
                0.01,
                0.3,
                log=True
            ),
            "max_depth": trial.suggest_int(
                "max_depth",
                2,
                8
            ),
            "min_samples_split": trial.suggest_int(
                "min_samples_split",
                2,
                20
            ),
            "min_samples_leaf": trial.suggest_int(
                "min_samples_leaf",
                1,
                10
            ),
            "subsample": trial.suggest_float(
                "subsample",
                0.6,
                1.0
            ),
            "max_features": trial.suggest_categorical(
                "max_features",
                [None, "sqrt", "log2"]
            ),
            "loss": trial.suggest_categorical(
                "loss",
                [
                    "squared_error",
                    "huber",
                    "absolute_error"
                ]
            )
        }

        model = GradientBoostingRegressor(
            **params,
            random_state=42
        )

        cv = KFold(
            n_splits=5,
            shuffle=True,
            random_state=42
        )

        # sklearn returns negative MSE because higher scores are normally better.
        cv_scores = cross_val_score(
            model,
            X_train,
            y_train,
            cv=cv,
            scoring="neg_mean_squared_error",
            n_jobs=-1
        )

        # Convert negative MSE to positive MSE.
        return -cv_scores.mean()


    # -----------------------------
    # Run optimization
    # -----------------------------

    study = optuna.create_study(
        direction="minimize",
        study_name="gradient_boosting_regressor"
    )

    study.optimize(
        objective,
        n_trials=100,
        show_progress_bar=True
    )


    # -----------------------------
    # Display best parameters
    # -----------------------------

    logger.info("Best CV MSE:", study.best_value)
    logger.info("\nBest parameters:")

    for parameter, value in study.best_params.items():
        logger.info(f"{parameter}: {value}")


    # -----------------------------
    # Train final optimized model
    # -----------------------------

    best_model = GradientBoostingRegressor(
        **study.best_params,
        random_state=42
    )

    best_model.fit(X_train, y_train)


    # -----------------------------
    # Evaluate model
    # -----------------------------

    y_train_pred = best_model.predict(X_train)
    y_test_pred = best_model.predict(X_test)

    train_mse = mean_squared_error(y_train, y_train_pred)
    test_mse = mean_squared_error(y_test, y_test_pred)

    train_r2 = r2_score(y_train, y_train_pred)
    test_r2 = r2_score(y_test, y_test_pred)

    logger.info("\nFinal Model Results")
    logger.info("-------------------")
    logger.info("Train R²:", train_r2)
    logger.info("Test R²:", test_r2)
    logger.info("Train MSE:", train_mse)
    logger.info("Test MSE:", test_mse)

    return best_model