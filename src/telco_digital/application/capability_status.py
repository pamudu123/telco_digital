"""Structured POC capability status. Markdown docs must match this manifest."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CapabilityStatusValue = Literal["POC complete", "In progress", "Not started", "Deferred"]


class CapabilityRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    number: str
    name: str
    status: CapabilityStatusValue
    document: str | None = None
    demonstrated_scenario: str
    consuming_applications: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    implemented: tuple[str, ...] = ()
    not_implemented: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


class CapabilityManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    capabilities: tuple[CapabilityRecord, ...]
    notes: str = (
        "POC complete means the documented scenario works in the shared demo "
        "environment; it does not mean production ready. An early read-only "
        "showcase may present capability-00 facts without completing FastAPI "
        "or the simulator."
    )


CAPABILITIES: tuple[CapabilityRecord, ...] = (
    CapabilityRecord(
        number="00",
        name="Expanded POC dataset",
        status="POC complete",
        document="docs/features/00-poc-dataset.md",
        demonstrated_scenario=(
            "Deterministic cross-domain dataset: U001–U005 preserved, U006–U010 "
            "added, 1,000 background customers, facts with matching activity and outbox events."
        ),
        consuming_applications=(
            "Selfcare",
            "Loyalty",
            "adReach",
            "Viber",
            "Mobile Money",
            "SFA",
            "Lottery",
        ),
        evidence=(
            "docs/features/00-poc-dataset.md",
            "notebooks/00_dataset/00_dataset.ipynb",
            "notebooks/00_dataset/outputs/metrics.json",
            "notebooks/00_dataset/outputs/tables/",
            "notebooks/00_dataset/outputs/plots/",
        ),
        implemented=(
            "Deterministic golden and background population generation",
            "Cross-domain facts with activity/outbox parity",
            "Idempotent load, dataset-owned reset, validation, notebook, and plots",
        ),
        not_implemented=(
            "Neo4j projection of the expanded outbox",
            "Features, event memory, models, twins, decisions, Copilot",
            "Complete FastAPI surface and POC simulator",
        ),
        limitations=(
            "Synthetic, scenario-shaped distributions",
            "Not a production-scale or certified dataset",
        ),
    ),
    CapabilityRecord(
        number="01",
        name="Outbox and Neo4j projection",
        status="POC complete",
        document="docs/features/01-neo4j-projection.md",
        demonstrated_scenario="PostgreSQL outbox projected into a rebuildable Neo4j graph.",
        consuming_applications=("Mobile Money", "SFA", "Lottery"),
        evidence=(
            "docs/features/01-neo4j-projection.md",
            "notebooks/01_graph_projection/01_graph_projection.ipynb",
            "notebooks/01_graph_projection/outputs/metrics.json",
            "notebooks/01_graph_projection/outputs/tables/",
            "notebooks/01_graph_projection/outputs/plots/",
        ),
        implemented=(
            "Managed cross-domain graph rebuild",
            "Single-worker outbox retry and success checkpointing",
            "Source/projection reconciliation and graph-shape evidence",
        ),
        not_implemented=(
            "Distributed worker operations and dead-letter replay",
            "Incremental event-specific projection",
        ),
        limitations=(
            "Graph output remains a rebuildable projection, never source of truth",
            "One controlled worker and snapshot rebuild are POC-only choices",
        ),
    ),
    CapabilityRecord(
        number="02",
        name="Temporal and graph features",
        status="POC complete",
        document="docs/features/02-feature-layer.md",
        demonstrated_scenario="Time-aware and graph features derived from recorded facts.",
        consuming_applications=("Selfcare", "Loyalty", "Mobile Money", "SFA"),
        evidence=(
            "docs/features/02-feature-layer.md",
            "notebooks/02_features/02_features.ipynb",
            "notebooks/02_features/outputs/metrics.json",
            "notebooks/02_features/outputs/tables/",
            "notebooks/02_features/outputs/plots/",
        ),
        implemented=(
            "Point-in-time temporal and graph feature services",
            "Explicit deterministic snapshot materialization",
            "Read-only feature and graph showcase endpoints",
        ),
        not_implemented=("Training and scoring", "Production feature store"),
        limitations=("POC feature definitions over synthetic data",),
    ),
    CapabilityRecord(
        number="03",
        name="Event memory",
        status="POC complete",
        document="docs/features/03-event-memory.md",
        demonstrated_scenario=(
            "U001 travelling to Singapore again retrieves the March 2026 episode: "
            "6 days, 11.4 GB, ROAM_15, no additional package required."
        ),
        consuming_applications=("Selfcare", "Loyalty", "adReach", "Viber", "SFA"),
        evidence=(
            "docs/features/03-event-memory.md",
            "notebooks/03_event_memory/03_event_memory.ipynb",
            "notebooks/03_event_memory/outputs/metrics.json",
            "notebooks/03_event_memory/outputs/tables/",
            "notebooks/03_event_memory/outputs/plots/",
        ),
        implemented=(
            "Travel episode extraction from point-in-time facts",
            "Similar-event matching with personal-history priority",
            "CustomerContext with explicit unknowns",
            "Read-only event-memory API and Journey page",
        ),
        not_implemented=(
            "Non-travel episode types",
            "Persisted episode store",
            "Recommendation ranking from retrieved episodes",
        ),
        limitations=(
            "Travel-only memory over synthetic journeys",
            "Similarity is deterministic and rule-based, not learned",
        ),
    ),
    CapabilityRecord(
        number="04",
        name="Behaviour intelligence",
        status="POC complete",
        document="docs/features/04-behaviour-intelligence.md",
        demonstrated_scenario=(
            "U002 repeated small recharges yield PRICE_SENSITIVE with confidence and evidence. "
            "U001 is a frequent traveller and heavy data user from travel history."
        ),
        consuming_applications=("Selfcare", "Loyalty", "adReach", "Viber", "Mobile Money", "SFA"),
        evidence=(
            "docs/features/04-behaviour-intelligence.md",
            "notebooks/04_behaviour/04_behaviour.ipynb",
            "notebooks/04_behaviour/outputs/metrics.json",
            "notebooks/04_behaviour/outputs/tables/",
            "notebooks/04_behaviour/outputs/plots/",
        ),
        implemented=(
            "Point-in-time rule traits from features and travel episodes",
            "Confidence and evidence on every trait",
            "Read-only behaviour API and Customer 360 trait panel",
        ),
        not_implemented=(
            "Persisted trait store",
            "Online clustering in the API",
        ),
        limitations=(
            "Deterministic rules over synthetic history",
            "Clustering remains a notebook experiment, not a served model",
        ),
    ),
    CapabilityRecord(
        number="05",
        name="Churn prediction",
        status="POC complete",
        document="docs/features/05-churn-prediction.md",
        demonstrated_scenario=(
            "U004 declining usage and open network/complaint tickets score HIGH "
            "churn risk from a notebook-trained logistic regression, with drivers."
        ),
        consuming_applications=("Selfcare", "Loyalty", "adReach", "Viber"),
        evidence=(
            "docs/features/05-churn-prediction.md",
            "notebooks/05_churn/05_churn.ipynb",
            "notebooks/05_churn/outputs/metrics.json",
            "notebooks/05_churn/outputs/tables/",
            "notebooks/05_churn/outputs/plots/",
            "notebooks/05_churn/artifacts/churn-model-v1.json",
        ),
        implemented=(
            "Notebook training comparing logistic regression and gradient-boosted trees",
            "Served logistic-regression artifact with probability, risk band and drivers",
            "Read-only churn API and Customer 360 prediction panel",
        ),
        not_implemented=(
            "Persisted prediction store",
            "Online retraining",
        ),
        limitations=(
            "Synthetic labelled population, not a live churn outcome table",
            "Gradient boosting is compared in the notebook and is not served",
        ),
    ),
    CapabilityRecord(
        number="06",
        name="Recommendations and uncertainty",
        status="POC complete",
        document="docs/features/06-recommendations-uncertainty.md",
        demonstrated_scenario=(
            "U001 travelling to Singapore with unknown duration is SCENARIO_BASED; "
            "ROAM_15 ranks highest from the March 6-day / 11.4 GB episode; "
            "ROAM_5 and ROAM_30 remain catalogue alternatives."
        ),
        consuming_applications=("Selfcare", "Loyalty", "adReach", "Viber", "SFA"),
        evidence=(
            "docs/features/06-recommendations-uncertainty.md",
            "notebooks/06_recommendations/06_recommendations.ipynb",
            "notebooks/06_recommendations/outputs/metrics.json",
            "notebooks/06_recommendations/outputs/tables/",
            "notebooks/06_recommendations/outputs/plots/",
        ),
        implemented=(
            "Candidate generation from the active roaming catalogue only",
            "Deterministic scoring from retrieved travel episodes",
            "Known / inferred / predicted / unknown uncertainty facts",
            "Read-only recommendation API, Journey panel and Customer 360 panel",
        ),
        not_implemented=(
            "Outcome recording of the chosen offer",
            "Learned ranking that invents a plan",
        ),
        limitations=(
            "Travel-offer ranking over a synthetic Singapore catalogue",
            "Churn is not applied as a discount or invented plan",
        ),
    ),
    CapabilityRecord(
        number="07",
        name="Graph fraud",
        status="Not started",
        demonstrated_scenario="Shared-device and transfer patterns scored from the graph.",
        consuming_applications=("Mobile Money", "Loyalty", "SFA", "Lottery"),
        not_implemented=("Fraud features", "Fraud scorer"),
    ),
    CapabilityRecord(
        number="08",
        name="SFA forecasting",
        status="Not started",
        demonstrated_scenario="Retailer demand forecast and stockout warning.",
        consuming_applications=("SFA",),
        not_implemented=("Forecast model", "Retailer twin"),
    ),
    CapabilityRecord(
        number="09",
        name="Digital twins",
        status="Not started",
        demonstrated_scenario="Interpreted current state distinct from recorded facts.",
        consuming_applications=("Selfcare", "Loyalty", "adReach", "Viber", "Mobile Money", "SFA"),
        not_implemented=("DigitalTwin V1",),
    ),
    CapabilityRecord(
        number="10",
        name="Decision engine and explanations",
        status="POC complete",
        document="docs/features/10-decision-engine.md",
        demonstrated_scenario=(
            "U001 Singapore with unknown duration presents catalogue ROAM_15. "
            "U004 HIGH churn with open network/complaint tickets gets "
            "SUPPORT_FOLLOW_UP, not a discount. U002 PRICE_SENSITIVE with no "
            "travel context does not invent an offer."
        ),
        consuming_applications=("Selfcare", "Loyalty", "adReach", "Viber", "Mobile Money", "SFA"),
        evidence=(
            "docs/features/10-decision-engine.md",
            "notebooks/10_decisioning/10_decisioning.ipynb",
            "notebooks/10_decisioning/outputs/metrics.json",
            "notebooks/10_decisioning/outputs/tables/",
            "notebooks/10_decisioning/outputs/plots/",
        ),
        implemented=(
            "DecisionEngine composing event memory, behaviour, churn and recommendations",
            "Deterministic NBA with reason codes and What/Why explanations",
            "Churn used as a constraint, never as a discount generator",
            "Read-only decision API plus Journey, Customer 360 and Models panels",
        ),
        not_implemented=(
            "Outcome recording of the chosen action",
            "Fraud, forecast and digital-twin inputs",
        ),
        limitations=(
            "Missing 07–09 inputs are explicit unknowns, not invented zeros",
            "Rules are catalogue-safe and synthetic-persona shaped",
        ),
    ),
    CapabilityRecord(
        number="11",
        name="OpenRouter GLM Copilot",
        status="POC complete",
        document="docs/features/11-copilot.md",
        demonstrated_scenario=(
            "Why is U001 receiving this recommendation? is answered from the "
            "decision document: March episode, ROAM_15, duration unknown, "
            "alternatives ROAM_5 and ROAM_30."
        ),
        consuming_applications=("Selfcare", "Loyalty", "adReach", "Viber", "Mobile Money", "SFA"),
        evidence=(
            "docs/features/11-copilot.md",
            "notebooks/11_copilot/11_copilot.ipynb",
            "notebooks/11_copilot/outputs/metrics.json",
            "notebooks/11_copilot/outputs/tables/",
        ),
        implemented=(
            "Structured context pack from decision, recommendations and event memory",
            "Deterministic fallback that never invents a plan",
            "Optional OpenRouter GLM when OPENROUTER_API_KEY is set",
            "Read-only Copilot API and live Copilot page",
        ),
        not_implemented=(
            "Command writes from Copilot",
            "Persistent conversation history",
        ),
        limitations=(
            "Copilot is a presentation layer and does not create facts",
            "Missing key, failed call or ungrounded model text uses the fallback",
        ),
    ),
    CapabilityRecord(
        number="12",
        name="FastAPI",
        status="Not started",
        demonstrated_scenario=(
            "Stable application-service API including health, projection lag, and model versions."
        ),
        consuming_applications=("All applications",),
        implemented=(),
        not_implemented=(
            "Complete FastAPI surface",
            "Projection lag and model-version endpoints",
            "Command adapters",
        ),
        limitations=("A minimal read-only showcase slice must not be labelled FastAPI complete",),
    ),
    CapabilityRecord(
        number="13",
        name="POC simulator",
        status="Not started",
        document=None,
        demonstrated_scenario="Framework-free simulator using the NG application visual language.",
        consuming_applications=("All applications",),
        not_implemented=("Write path from UI", "Simulator.js", "End-to-end command tracing"),
        limitations=(
            "An early read-only showcase is not the simulator; the document name remains "
            "13-poc-simulator.md when this capability is implemented",
        ),
    ),
)

MANIFEST = CapabilityManifest(capabilities=CAPABILITIES)

STATUS_TABLE_ROWS: tuple[tuple[str, str, str], ...] = tuple(
    (item.number, item.name, item.status) for item in CAPABILITIES
)

ARTIFACT_LINKS: tuple[dict[str, str], ...] = (
    {
        "title": "Documentation",
        "path": "docs/features/00-poc-dataset.md",
        "description": "Capability-00 dataset evidence",
        "source": "capability_00_artifact",
    },
    {
        "title": "Executed notebook",
        "path": "notebooks/00_dataset/00_dataset.ipynb",
        "description": "Read-only analysis of retained metrics",
        "source": "capability_00_artifact",
    },
    {
        "title": "Metrics",
        "path": "notebooks/00_dataset/outputs/metrics.json",
        "description": "Validated load report",
        "source": "capability_00_artifact",
    },
    {
        "title": "Tables",
        "path": "notebooks/00_dataset/outputs/tables/",
        "description": "Compact JSON tables from the notebook",
        "source": "capability_00_artifact",
    },
    {
        "title": "Plots",
        "path": "notebooks/00_dataset/outputs/plots/",
        "description": "Retained capability-00 charts",
        "source": "capability_00_artifact",
    },
)


class WalkthroughStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    number: int
    title: str
    live: bool
    summary: str


class Walkthrough(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    customer_ref: str | None = None
    retailer_ref: str | None = None
    applications: tuple[str, ...]
    current_evidence: str
    later_intelligence: str
    steps: tuple[WalkthroughStep, ...] = Field(default_factory=tuple)


def _fact_steps(*, unknown: str, consumer: str) -> tuple[WalkthroughStep, ...]:
    return (
        WalkthroughStep(
            number=1, title="What happened", live=True, summary="Authoritative recorded facts."
        ),
        WalkthroughStep(
            number=2,
            title="What the platform knows",
            live=True,
            summary="Reconstructed context from facts at as_of.",
        ),
        WalkthroughStep(
            number=3,
            title="What it infers or predicts",
            live=False,
            summary="Derived output is POC planned until later capabilities are verified.",
        ),
        WalkthroughStep(
            number=4,
            title="What it recommends",
            live=False,
            summary="Decisions and reason codes are POC planned.",
        ),
        WalkthroughStep(number=5, title="What remains unknown", live=True, summary=unknown),
        WalkthroughStep(
            number=6,
            title="Which existing application consumes the result",
            live=True,
            summary=consumer,
        ),
    )


WALKTHROUGHS: tuple[Walkthrough, ...] = (
    Walkthrough(
        id="singapore-travel",
        title="Customer travels to Singapore",
        customer_ref="U001",
        applications=("Selfcare",),
        current_evidence=(
            "Travel facts, retrieved March episode, ranked catalogue offers "
            "and PRESENT_OFFER ROAM_15"
        ),
        later_intelligence="Copilot explanation of the offer and outcome recording",
        steps=(
            WalkthroughStep(
                number=1, title="What happened", live=True, summary="Authoritative recorded facts."
            ),
            WalkthroughStep(
                number=2,
                title="What the platform knows",
                live=True,
                summary="Reconstructed context from facts at as_of.",
            ),
            WalkthroughStep(
                number=3,
                title="What it infers or predicts",
                live=True,
                summary="March Singapore episode retrieved: 6 days, 11.4 GB, ROAM_15.",
            ),
            WalkthroughStep(
                number=4,
                title="What it recommends",
                live=True,
                summary="SCENARIO_BASED: ROAM_15 first; ROAM_5 and ROAM_30 as alternatives.",
            ),
            WalkthroughStep(
                number=5,
                title="What remains unknown",
                live=True,
                summary="August trip duration is unknown unless that later trip has already ended.",
            ),
            WalkthroughStep(
                number=6,
                title="Which existing application consumes the result",
                live=True,
                summary="Mobile Selfcare",
            ),
        ),
    ),
    Walkthrough(
        id="small-recharges",
        title="Repeated small recharges",
        customer_ref="U002",
        applications=("Selfcare", "Loyalty"),
        current_evidence="Recharge history plus PRICE_SENSITIVE trait and NO_INVENTED_OFFER",
        later_intelligence="A catalogue-backed personalised offer when travel context exists",
        steps=(
            WalkthroughStep(
                number=1, title="What happened", live=True, summary="Authoritative recorded facts."
            ),
            WalkthroughStep(
                number=2,
                title="What the platform knows",
                live=True,
                summary="Reconstructed context from facts at as_of.",
            ),
            WalkthroughStep(
                number=3,
                title="What it infers or predicts",
                live=True,
                summary="PRICE_SENSITIVE from repeated small recharges, with evidence.",
            ),
            WalkthroughStep(
                number=4,
                title="What it recommends",
                live=True,
                summary="NO_INVENTED_OFFER: price sensitivity without catalogue travel context.",
            ),
            WalkthroughStep(
                number=5,
                title="What remains unknown",
                live=True,
                summary="No personalised offer is generated without catalogue travel context.",
            ),
            WalkthroughStep(
                number=6,
                title="Which existing application consumes the result",
                live=True,
                summary="Mobile Selfcare and Loyalty Management",
            ),
        ),
    ),
    Walkthrough(
        id="declining-usage",
        title="Falling usage with complaints",
        customer_ref="U004",
        applications=("Selfcare", "Loyalty", "adReach", "Viber"),
        current_evidence="Usage and service events plus a trained churn score and support NBA",
        later_intelligence="Copilot explanation and outcome recording of the support action",
        steps=(
            WalkthroughStep(
                number=1, title="What happened", live=True, summary="Authoritative recorded facts."
            ),
            WalkthroughStep(
                number=2,
                title="What the platform knows",
                live=True,
                summary="Reconstructed context from facts at as_of.",
            ),
            WalkthroughStep(
                number=3,
                title="What it infers or predicts",
                live=True,
                summary="Notebook-trained logistic regression scores U004 HIGH with drivers.",
            ),
            WalkthroughStep(
                number=4,
                title="What it recommends",
                live=True,
                summary="SUPPORT_FOLLOW_UP: support action, not a discount.",
            ),
            WalkthroughStep(
                number=5,
                title="What remains unknown",
                live=True,
                summary=(
                    "Fraud, forecast and twin inputs remain unknown. "
                    "The action is not recorded as an outcome."
                ),
            ),
            WalkthroughStep(
                number=6,
                title="Which existing application consumes the result",
                live=True,
                summary="Mobile Selfcare, Loyalty, adReach and Viber",
            ),
        ),
    ),
    Walkthrough(
        id="shared-device",
        title="Shared device and suspicious transfers",
        customer_ref="U009",
        applications=("Mobile Money",),
        current_evidence="Device, wallet, merchant and transaction facts",
        later_intelligence="Neo4j graph fraud evidence",
        steps=_fact_steps(
            unknown="Graph fraud scoring is not implemented.",
            consumer="Mobile Money",
        ),
    ),
    Walkthrough(
        id="retailer-stock",
        title="Falling retailer stock with rising sales",
        retailer_ref="RET-001",
        applications=("SFA",),
        current_evidence="Sales and inventory events",
        later_intelligence="Forecast, retailer twin and restock action",
        steps=_fact_steps(
            unknown="No forecast or stockout score is produced in this showcase.",
            consumer="Mobile SFA",
        ),
    ),
    Walkthrough(
        id="campaign-response",
        title="Changing campaign responses",
        customer_ref="U006",
        applications=("adReach", "Viber"),
        current_evidence="Campaign interaction history",
        later_intelligence="Campaign intelligence and channel decision",
        steps=_fact_steps(
            unknown="No propensity or channel decision is produced in this showcase.",
            consumer="adReach and Viber Campaign Manager",
        ),
    ),
)


def get_manifest() -> CapabilityManifest:
    return MANIFEST


def get_walkthroughs() -> tuple[Walkthrough, ...]:
    return WALKTHROUGHS
