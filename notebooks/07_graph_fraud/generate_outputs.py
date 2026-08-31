"""Write retained capability-07 tables, plots and metrics."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from fixtures import GOLDEN

from telco_digital.intelligence.fraud import score_fraud

ROOT = Path(__file__).resolve().parent
TABLES = ROOT / "outputs" / "tables"
PLOTS = ROOT / "outputs" / "plots"
for folder in (TABLES, PLOTS, ROOT / "artifacts"):
    folder.mkdir(parents=True, exist_ok=True)


def main() -> None:
    documents = {ref: score_fraud(*pair) for ref, pair in GOLDEN.items()}
    scores = [
        {
            "customer_ref": ref,
            "transaction_risk": document.transaction_risk,
            "graph_risk": document.graph_risk,
            "combined_risk": document.combined_risk,
            "risk_band": document.risk_band,
            "fired_rules": [rule.code for rule in document.rules if rule.fired],
            "in_known_fraud_seed": document.in_known_fraud_seed,
        }
        for ref, document in documents.items()
    ]
    u009 = documents["U009"]
    rules = [
        {
            "code": rule.code,
            "fired": rule.fired,
            "severity": rule.severity,
            "boost": rule.boost,
        }
        for rule in u009.rules
    ]
    comparison = [
        {
            "customer_ref": row["customer_ref"],
            "transaction_risk": row["transaction_risk"],
            "graph_risk": row["graph_risk"],
            "delta": round(row["graph_risk"] - row["transaction_risk"], 4),
        }
        for row in scores
    ]
    (TABLES / "golden_scores.json").write_text(
        json.dumps(scores, indent=2) + "\n", encoding="utf-8"
    )
    (TABLES / "u009_rules.json").write_text(json.dumps(rules, indent=2) + "\n", encoding="utf-8")
    (TABLES / "transaction_vs_graph.json").write_text(
        json.dumps(comparison, indent=2) + "\n", encoding="utf-8"
    )

    refs = [row["customer_ref"] for row in scores]
    fig, ax = plt.subplots(figsize=(7, 4))
    x = range(len(refs))
    ax.bar(
        [i - 0.18 for i in x],
        [row["transaction_risk"] for row in scores],
        width=0.36,
        label="Transaction-only",
    )
    ax.bar(
        [i + 0.18 for i in x],
        [row["graph_risk"] for row in scores],
        width=0.36,
        label="Graph",
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels(refs)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Risk")
    ax.set_title("Transaction-only vs graph risk")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS / "transaction_vs_graph.png", dpi=120)
    plt.close(fig)

    fired_counts = {}
    for document in documents.values():
        for rule in document.rules:
            if rule.fired:
                fired_counts[rule.code] = fired_counts.get(rule.code, 0) + 1
    fig, ax = plt.subplots(figsize=(7, 4))
    labels = list(fired_counts)
    ax.barh(labels, [fired_counts[name] for name in labels])
    ax.set_xlabel("Golden customers")
    ax.set_title("Fired fraud rules")
    fig.tight_layout()
    fig.savefig(PLOTS / "rule_firings.png", dpi=120)
    plt.close(fig)

    metrics = {
        "scorer_version": u009.scorer_version,
        "prediction_set_version": u009.prediction_set_version,
        "u009_risk_band": u009.risk_band,
        "u009_transaction_risk": u009.transaction_risk,
        "u009_graph_risk": u009.graph_risk,
        "u003_risk_band": documents["U003"].risk_band,
        "graph_exceeds_transaction_for_u009": u009.graph_risk > u009.transaction_risk,
        "golden_customers": len(documents),
    }
    (ROOT / "outputs" / "metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
