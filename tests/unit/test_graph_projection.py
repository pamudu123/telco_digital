from dataclasses import fields

from telco_digital.infrastructure.neo4j.projector import GraphProjector, GraphSnapshot


class RecordingRepository:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def ensure_constraints(self) -> None:
        self.calls.append("ensure_constraints")

    def clear_managed_projection(self) -> None:
        self.calls.append("clear_managed_projection")

    def counts(self) -> dict[str, int]:
        self.calls.append("counts")
        return {"Customer": 1}

    def __getattr__(self, name: str):
        if name.startswith("project_"):
            return lambda _rows: self.calls.append(name)
        raise AttributeError(name)


def empty_snapshot() -> GraphSnapshot:
    return GraphSnapshot(**{field.name: [] for field in fields(GraphSnapshot)})


def test_rebuild_clears_only_managed_projection_and_projects_all_domains() -> None:
    repository = RecordingRepository()

    counts = GraphProjector(repository).rebuild(empty_snapshot())

    assert counts == {"Customer": 1}
    assert repository.calls[:2] == ["ensure_constraints", "clear_managed_projection"]
    assert "project_wallets" in repository.calls
    assert "project_transactions" in repository.calls
    assert "project_retailers" in repository.calls
    assert "project_sales" in repository.calls
    assert "project_inventory_events" in repository.calls
    assert repository.calls[-1] == "counts"


def test_rebuild_can_preserve_existing_managed_projection() -> None:
    repository = RecordingRepository()

    GraphProjector(repository).rebuild(empty_snapshot(), reset_managed=False)

    assert "clear_managed_projection" not in repository.calls
