"""Point-in-time churn scores from a notebook-trained model artifact.

Predictions are derived and are never a source of truth. The served model is
the logistic regression exported by ``notebooks/05_churn/05_churn.ipynb``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from telco_digital.intelligence.churn.features import (
    FEATURE_SET_VERSION,
    PREDICTION_SET_VERSION,
    vector_from_features,
)
from telco_digital.intelligence.churn.model import (
    artifact_model_version,
    load_artifact,
    predict_probability,
    risk_band,
    top_drivers,
)
from telco_digital.intelligence.features import CustomerFeatures, CustomerFeatureService
from telco_digital.intelligence.features.service import validate_as_of

RiskBand = Literal["LOW", "MEDIUM", "HIGH"]
DriverDirection = Literal["increases_risk", "decreases_risk"]


class ChurnDriver(BaseModel):
    model_config = ConfigDict(frozen=True)

    feature: str
    value: float
    contribution: float
    direction: DriverDirection


class CustomerChurn(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = "derived_live"
    customer_id: UUID
    customer_ref: str
    as_of: datetime
    computed_at: datetime
    prediction_set_version: str = PREDICTION_SET_VERSION
    model_version: str
    model_type: str
    feature_set_version: str = FEATURE_SET_VERSION
    probability: float
    risk_band: RiskBand
    drivers: tuple[ChurnDriver, ...]
    feature_snapshot: dict[str, float]
    unknowns: tuple[str, ...] = ()
    provenance: tuple[str, ...] = (
        "PostgreSQL point-in-time features",
        "Notebook-trained logistic regression artifact",
        "Predictions are derived and not persisted",
    )


class FeatureCalculator(Protocol):
    async def calculate(self, customer_ref: str, as_of: datetime) -> CustomerFeatures: ...


def score_churn(
    features: CustomerFeatures,
    artifact: dict[str, Any] | None = None,
) -> CustomerChurn:
    validate_as_of(features.as_of)
    payload = artifact if artifact is not None else load_artifact()
    vector, unknowns = vector_from_features(features)
    probability = predict_probability(vector, payload)
    drivers = tuple(ChurnDriver(**item) for item in top_drivers(vector, payload))
    return CustomerChurn(
        customer_id=features.customer_id,
        customer_ref=features.customer_ref,
        as_of=features.as_of,
        computed_at=datetime.now(tz=UTC),
        model_version=artifact_model_version(payload),
        model_type=str(payload["model_type"]),
        probability=probability,
        risk_band=risk_band(probability, payload),
        drivers=drivers,
        feature_snapshot=vector,
        unknowns=unknowns,
    )


class ChurnService:
    def __init__(
        self,
        features: CustomerFeatureService | FeatureCalculator,
        artifact: dict[str, Any] | None = None,
    ) -> None:
        self.features = features
        self.artifact = artifact

    async def predict(self, customer_ref: str, as_of: datetime) -> CustomerChurn:
        validate_as_of(as_of)
        features = await self.features.calculate(customer_ref, as_of)
        return score_churn(features, self.artifact)
