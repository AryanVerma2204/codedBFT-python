from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from config import ExperimentConfig, ProtocolType
from messages import Block, Message
from metrics import Metrics

if TYPE_CHECKING:
    from network import SimulatedNetwork

log = logging.getLogger("codedbft")


def time_since(t: float) -> float:
    import time
    return time.monotonic() - t


class ConsensusProtocol(ABC):
    NAME = "Protocol"

    def init(self, node: Node) -> None:
        self.node = node
        self.metrics = Metrics()
        self.current_view = 0
        self._task: asyncio.Task | None = None

    @abstractmethod
    def propose(self, block: Block) -> None: ...

    @abstractmethod
    def handle_message(self, msg: Message) -> None: ...

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        timeout = self.node.config.consensus_timeout
        inbox = self.node.net.get_channel(self.node.id)
        self._task = asyncio.current_task()
        self._deadline = loop.time() + timeout
        watchdog = asyncio.create_task(self._timeout_watchdog())
        try:
            while True:
                msg = await inbox.get()
                self._deadline = loop.time() + timeout
                self.handle_message(msg)
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            pass
        finally:
            watchdog.cancel()

    async def _timeout_watchdog(self) -> None:
        loop = asyncio.get_running_loop()
        timeout = self.node.config.consensus_timeout
        while True:
            remaining = self._deadline - loop.time()
            if remaining > 0:
                await asyncio.sleep(remaining)
                continue
            self.current_view += 1
            self.metrics.inc_view_changes()
            log.info("[Node %d] %s: Timeout, moving to view %d",
                     self.node.id, self.NAME, self.current_view)
            self._deadline = loop.time() + timeout

    def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()

    def get_metrics(self) -> Metrics:
        return self.metrics

    def get_current_view(self) -> int:
        return self.current_view


class Node:
    def __init__(self, node_id: int, config: ExperimentConfig, net: SimulatedNetwork):
        from protocol_codedbft import CodedBFTProtocol
        from protocol_pbft import PBFTProtocol

        self.id = node_id
        self.config = config
        self.net = net
        self.stopped = False

        if config.protocol == ProtocolType.CODED_BFT:
            self.protocol: ConsensusProtocol = CodedBFTProtocol(speculative_execution_enabled=True)
        elif config.protocol == ProtocolType.CODED_BFT_NO_SPEC:
            self.protocol = CodedBFTProtocol(speculative_execution_enabled=False)
        elif config.protocol == ProtocolType.PBFT:
            self.protocol = PBFTProtocol()
        else:
            self.protocol = None
        self.protocol.init(self)

    async def start(self) -> None:
        await self.protocol.start()

    def stop(self) -> None:
        self.protocol.stop()

    def is_stopped(self) -> bool:
        return self.stopped

    def propose(self, block: Block) -> None:
        self.protocol.propose(block)

    def get_metrics(self) -> Metrics:
        return self.protocol.get_metrics()

    def get_current_view(self) -> int:
        return self.protocol.get_current_view()
