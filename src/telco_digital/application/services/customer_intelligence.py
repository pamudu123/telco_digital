"""Compose the Customer 360 intelligence read model without repeated calculations."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel

from telco_digital.application.queries.showcase import Customer360
from telco_digital.application.services.showcase import ShowcaseQueries
from telco_digital.application.unit_of_work.protocol import UnitOfWork
from telco_digital.decisioning import CustomerDecision, decide
from telco_digital.intelligence.behaviour import CustomerBehaviour, build_behaviour
from telco_digital.intelligence.churn import CustomerChurn, score_churn
from telco_digital.intelligence.digital_twin import (
    CustomerDigitalTwin,
    UnitOfWorkStateReader,
    assemble_customer_twin,
)
from telco_digital.intelligence.event_memory import CustomerContext
from telco_digital.intelligence.features import CustomerFeatures
from telco_digital.intelligence.fraud import CustomerFraud
from telco_digital.intelligence.recommendations import (
    CataloguePlan,
    CustomerRecommendation,
    build_recommendation,
)


class FeatureCalculator(Protocol):
    async def calculate(self, customer_ref: str, as_of: datetime) -> CustomerFeatures: ...


class EpisodeRecaller(Protocol):
    async def recall(
        self,
        customer_ref: str,
        as_of: datetime,
        *,
        destination: str | None = None,
    ) -> CustomerContext: ...


class CatalogueReader(Protocol):
    async def list_roaming(self, *, country_code: str | None) -> tuple[CataloguePlan, ...]: ...


class FraudEvaluator(Protocol):
    async def evaluate(self, customer_ref: str, as_of: datetime) -> CustomerFraud: ...


class CustomerIntelligence(BaseModel):
    facts: Customer360
    features: CustomerFeatures
    event_memory: CustomerContext
    behaviour: CustomerBehaviour
    churn: CustomerChurn
    recommendation: CustomerRecommendation
    fraud: CustomerFraud
    twin: CustomerDigitalTwin
    decision: CustomerDecision


async def get_customer_intelligence(
    *,
    customer_ref: str,
    as_of: datetime,
    destination: str | None,
    queries: ShowcaseQueries,
    uow: UnitOfWork,
    features: FeatureCalculator,
    memory: EpisodeRecaller,
    catalogue: CatalogueReader,
    fraud: FraudEvaluator,
) -> CustomerIntelligence:
    """Build every Customer 360 panel once from shared intermediate results."""

    observed, feature_document, context, fraud_document = await asyncio.gather(
        UnitOfWorkStateReader(uow).get(customer_ref, as_of),
        features.calculate(customer_ref, as_of),
        memory.recall(customer_ref, as_of, destination=destination),
        fraud.evaluate(customer_ref, as_of),
    )
    facts, plans = await asyncio.gather(
        queries.customer_facts(observed, queried_at=datetime.now(tz=UTC)),
        catalogue.list_roaming(
            country_code=(
                context.current_situation.destination
                if context.current_situation.destination_known
                else None
            )
        ),
    )
    behaviour = build_behaviour(feature_document, context.historical_episodes)
    churn = score_churn(feature_document)
    recommendation = build_recommendation(context, plans)
    twin = assemble_customer_twin(
        observed, feature_document, context, behaviour, churn, recommendation
    )
    decision = decide(recommendation, behaviour, churn)
    return CustomerIntelligence(
        facts=facts,
        features=feature_document,
        event_memory=context,
        behaviour=behaviour,
        churn=churn,
        recommendation=recommendation,
        fraud=fraud_document,
        twin=twin,
        decision=decision,
    )
