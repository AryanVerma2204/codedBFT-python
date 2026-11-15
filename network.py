from __future__ import annotations

import asyncio
import random
from typing import Any

from config import ExperimentConfig
from messages import Message


class SimulatedNetwork:
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.channels: list[asyncio.Queue[Message]] = [
            asyncio.Queue(maxsize=1000) for _ in range(config.num_nodes)
        ]
        self._loop = asyncio.get_running_loop()
        self.stop = asyncio.Event()
        self._blocked: set[asyncio.Task] = set()

    def get_channel(self, node_id: int) -> asyncio.Queue[Message]:
        return self.channels[node_id]

    def send(self, msg: Message) -> None:
        self._loop.call_later(self.config.network_latency, self._deliver, msg)

    def _shutdown(self) -> None:
        self._closed = True
        for t in list(self._blocked):
            t.cancel()

    def _deliver(self, msg: Message) -> None:
        if getattr(self, "_closed", False) or self.stop.is_set():
            return
        if random.random() > self.config.packet_loss_prob:
            ch = self.channels[msg.to]
            try:
                ch.put_nowait(msg)
            except asyncio.QueueFull:
                t = self._loop.create_task(ch.put(msg))
                self._blocked.add(t)
                t.add_done_callback(self._blocked.discard)

    def broadcast(self, from_node_id: int, payload: Any) -> None:
        for i in range(self.config.num_nodes):
            if i == from_node_id:
                continue
            self.send(Message(from_id=from_node_id, to=i, payload=payload))
