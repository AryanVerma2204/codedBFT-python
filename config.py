from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

KB = 1024
MB = 1024 * KB


class ProtocolType(str, Enum):
    CODED_BFT = "CodedBFT"
    PBFT = "PBFT"
    CODED_BFT_NO_SPEC = "CodedBFT-NoSpec"

    def __str__(self) -> str:
        return self.value


@dataclass
class ExperimentConfig:
    name: str
    protocol: ProtocolType
    num_nodes: int
    num_faulty: int
    block_size: int
    packet_size: int
    network_latency: float
    packet_loss_prob: float
    sim_duration: float
    consensus_timeout: float
    run_id: int = 0


@dataclass
class SimulationResult:
    config: ExperimentConfig
    total_commits: int = 0
    total_bytes_sent: int = 0
    total_view_changes: int = 0
    latency_values: list[float] = field(default_factory=list)

    def print_as_csv(self) -> None:
        avg_latency = 0.0
        if self.latency_values:
            avg_latency = sum(self.latency_values) / len(self.latency_values)

        try:
            throughput_bps = (
                self.total_commits * self.config.block_size * 8
            ) / self.config.sim_duration
        except ZeroDivisionError:
            throughput_bps = 0.0
        if math.isnan(throughput_bps) or math.isinf(throughput_bps):
            throughput_bps = 0.0

        c = self.config
        print(
            f"{c.name},{c.run_id},{c.protocol},{c.num_nodes},{c.block_size},"
            f"{c.packet_loss_prob:.2f},{throughput_bps:.2f},{avg_latency:.2f},"
            f"{self.total_view_changes}",
            flush=True,
        )
