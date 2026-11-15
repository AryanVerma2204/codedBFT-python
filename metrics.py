from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Metrics:
    commits: int = 0
    bytes_sent: int = 0
    view_changes: int = 0
    latency_values: list[float] = field(default_factory=list)

    def add_commit(self, latency_seconds: float) -> None:
        self.commits += 1

        self.latency_values.append(float(int(latency_seconds * 1000)))

    def add_bytes_sent(self, nbytes: int) -> None:
        self.bytes_sent += nbytes

    def inc_view_changes(self) -> None:
        self.view_changes += 1
