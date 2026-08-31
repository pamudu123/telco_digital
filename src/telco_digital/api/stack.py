"""Compose existing intelligence services for HTTP adapters."""

from sqlalchemy.ext.asyncio import AsyncSession

from telco_digital.config import Settings
from telco_digital.copilot import CopilotService
from telco_digital.decisioning import DecisionEngine
from telco_digital.infrastructure.neo4j.features import Neo4jFeatureQueries
from telco_digital.infrastructure.neo4j.fraud import Neo4jGraphFraudQueries
from telco_digital.infrastructure.postgres.event_memory import PostgresEventMemoryQueries
from telco_digital.infrastructure.postgres.features import PostgresTemporalFeatureQueries
from telco_digital.infrastructure.postgres.forecasting import PostgresRetailerDemandQueries
from telco_digital.infrastructure.postgres.fraud import PostgresTransactionRiskQueries
from telco_digital.infrastructure.postgres.repositories import SqlPlanRepository
from telco_digital.infrastructure.postgres.unit_of_work import SqlAlchemyUnitOfWork
from telco_digital.intelligence.behaviour import BehaviourService
from telco_digital.intelligence.churn import ChurnService
from telco_digital.intelligence.digital_twin import DigitalTwinService, UnitOfWorkStateReader
from telco_digital.intelligence.event_memory import EventMemoryService
from telco_digital.intelligence.features import (
    CustomerFeatureService,
    GraphFeatureService,
    TemporalFeatureService,
)
from telco_digital.intelligence.forecasting import ForecastingService
from telco_digital.intelligence.fraud import FraudService
from telco_digital.intelligence.recommendations import (
    PlanRepositoryCatalogue,
    RecommendationService,
)


def customer_features(session: AsyncSession, settings: Settings) -> CustomerFeatureService:
    return CustomerFeatureService(
        TemporalFeatureService(PostgresTemporalFeatureQueries(session)),
        GraphFeatureService(Neo4jFeatureQueries(settings)),
    )


def event_memory(session: AsyncSession) -> EventMemoryService:
    return EventMemoryService(PostgresEventMemoryQueries(session))


def recommendations(session: AsyncSession) -> RecommendationService:
    return RecommendationService(
        event_memory(session),
        PlanRepositoryCatalogue(SqlPlanRepository(session)),
    )


def behaviour_service(session: AsyncSession, settings: Settings) -> BehaviourService:
    return BehaviourService(customer_features(session, settings), event_memory(session))


def churn_service(session: AsyncSession, settings: Settings) -> ChurnService:
    return ChurnService(customer_features(session, settings))


def fraud_service(session: AsyncSession, settings: Settings) -> FraudService:
    return FraudService(
        PostgresTransactionRiskQueries(session),
        Neo4jGraphFraudQueries(settings),
    )


def forecasting_service(session: AsyncSession) -> ForecastingService:
    return ForecastingService(PostgresRetailerDemandQueries(session))


def digital_twin(
    session: AsyncSession,
    settings: Settings,
    uow: SqlAlchemyUnitOfWork,
) -> DigitalTwinService:
    return DigitalTwinService(
        UnitOfWorkStateReader(uow),
        customer_features(session, settings),
        event_memory(session),
        PlanRepositoryCatalogue(SqlPlanRepository(session)),
    )


def decision_engine(session: AsyncSession, settings: Settings) -> DecisionEngine:
    features = customer_features(session, settings)
    memory = event_memory(session)
    return DecisionEngine(
        RecommendationService(memory, PlanRepositoryCatalogue(SqlPlanRepository(session))),
        BehaviourService(features, memory),
        ChurnService(features),
    )


def copilot_service(session: AsyncSession, settings: Settings) -> CopilotService:
    return CopilotService(decision_engine(session, settings), settings)
