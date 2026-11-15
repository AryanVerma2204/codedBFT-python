from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time

from config import ExperimentConfig, SimulationResult
from messages import Block
from network import SimulatedNetwork
from node import Node

log = logging.getLogger("codedbft")


class Simulation:
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.net: SimulatedNetwork | None = None
        self.nodes: list[Node] = []
        self._tasks: list[asyncio.Task] = []
        self.stop: asyncio.Event | None = None

    def run(self) -> SimulationResult:
        return asyncio.run(self._run())

    async def _run(self) -> SimulationResult:
        c = self.config
        log.info("--- Running: %s | RunID: %d | Protocol: %s | Nodes: %d | Loss: %.2f%% ---",
                 c.name, c.run_id, c.protocol, c.num_nodes, c.packet_loss_prob * 100)

        self.stop = asyncio.Event()
        self.net = SimulatedNetwork(c)
        self.nodes = [None] * c.num_nodes
        for i in range(c.num_nodes):
            self.nodes[i] = Node(i, c, self.net)
            self._tasks.append(asyncio.create_task(self.nodes[i].start()))

        asyncio.create_task(self._client_proposer())

        await asyncio.sleep(c.sim_duration)
        self.stop.set()

        result = await self._collect_results()
        self.net._shutdown()
        return result

    async def _client_proposer(self) -> None:
        loop = asyncio.get_running_loop()
        interval = 0.020
        next_tick = loop.time() + interval
        while True:
            stop_wait = asyncio.ensure_future(self.stop.wait())
            done, _ = await asyncio.wait({stop_wait}, timeout=max(0.0, next_tick - loop.time()))
            if done:
                return
            stop_wait.cancel()
            now = loop.time()
            next_tick += interval
            if next_tick <= now:
                next_tick = now + interval

            leader_id = self.nodes[0].get_current_view() % self.config.num_nodes
            leader_node = self.nodes[leader_id]

            if leader_node is not None and not leader_node.is_stopped():
                block_data = os.urandom(self.config.block_size)
                block = Block(
                    id=hashlib.sha256(block_data).digest(),
                    proposer=leader_id,
                    view=0,
                    timestamp=time.time(),
                    data=block_data,
                )
                leader_node.propose(block)

    async def _collect_results(self) -> SimulationResult:
        for node in self.nodes:
            node.stop()
        await asyncio.gather(*self._tasks)

        total_commits = 0
        total_bytes_sent = 0
        total_view_changes = 0
        all_latencies: list[float] = []

        for node in self.nodes:
            metrics = node.get_metrics()
            if node.id == 1:
                total_commits = metrics.commits
                all_latencies.extend(metrics.latency_values)
            total_bytes_sent += metrics.bytes_sent
            total_view_changes += metrics.view_changes
        total_view_changes //= self.config.num_nodes

        return SimulationResult(
            config=self.config,
            total_commits=total_commits,
            total_bytes_sent=total_bytes_sent,
            total_view_changes=total_view_changes,
            latency_values=all_latencies,
        )
