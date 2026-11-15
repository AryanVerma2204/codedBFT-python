from __future__ import annotations

import dataclasses
import logging
import sys

from config import MB, ExperimentConfig, ProtocolType
from simulation import Simulation

NUM_RUNS = 5


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                        format="%(asctime)s %(message)s", datefmt="%Y/%m/%d %H:%M:%S")

    print("experiment_name,run_id,protocol,num_nodes,block_size,packet_loss,throughput_bps,avg_latency_ms,view_changes")

    print("# Running Scalability Study...")
    run_scalability_study()
    print("# Running Packet Loss Resilience Study...")
    run_packet_loss_study()
    print("# Running Ablation Study...")
    run_ablation_study()
    print("# All experiments complete.")


def run_experiment(cfg: ExperimentConfig) -> None:
    for i in range(NUM_RUNS):
        cfg = dataclasses.replace(cfg, run_id=i)
        sim = Simulation(cfg)
        res = sim.run()
        res.print_as_csv()


def run_scalability_study() -> None:
    for n in [4, 8, 16, 32]:
        run_experiment(base_config("scalability", ProtocolType.CODED_BFT, n, 1 * MB))
        run_experiment(base_config("scalability", ProtocolType.PBFT, n, 1 * MB))


def run_packet_loss_study() -> None:
    for loss in [0.0, 0.01, 0.02, 0.05]:
        cfg_coded = base_config("packet_loss", ProtocolType.CODED_BFT, 16, 1 * MB)
        cfg_coded.packet_loss_prob = loss
        run_experiment(cfg_coded)

        cfg_pbft = base_config("packet_loss", ProtocolType.PBFT, 16, 1 * MB)
        cfg_pbft.packet_loss_prob = loss
        run_experiment(cfg_pbft)


def run_ablation_study() -> None:
    cfg_no_spec = base_config("ablation", ProtocolType.CODED_BFT_NO_SPEC, 16, 1 * MB)
    cfg_no_spec.packet_loss_prob = 0.02
    run_experiment(cfg_no_spec)

    cfg_full = base_config("ablation", ProtocolType.CODED_BFT, 16, 1 * MB)
    cfg_full.packet_loss_prob = 0.02
    run_experiment(cfg_full)


def base_config(name: str, proto: ProtocolType, num_nodes: int, block_size: int) -> ExperimentConfig:
    return ExperimentConfig(
        name=name,
        protocol=proto,
        num_nodes=num_nodes,
        num_faulty=(num_nodes - 1) // 3,
        block_size=block_size,
        packet_size=1400,
        network_latency=0.020,
        packet_loss_prob=0.0,
        sim_duration=5.0,
        consensus_timeout=1.0,
    )


if __name__ == "__main__":
    main()
