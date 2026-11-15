from __future__ import annotations

import hashlib
import time

from messages import Block, CommitMsg, Message, PrepareMsg, PrePrepareMsg
from node import ConsensusProtocol, log, time_since


class PBFTProtocol(ConsensusProtocol):
    NAME = "PBFT"

    def init(self, node) -> None:
        super().init(node)
        self.prepares: dict[bytes, set[int]] = {}
        self.commits: dict[bytes, set[int]] = {}
        self.committed: dict[bytes, bool] = {}

    def propose(self, block: Block) -> None:
        view = self.get_current_view()
        if self.node.id != view % self.node.config.num_nodes:
            return

        payload = PrePrepareMsg(view=view, block=block)
        self.node.net.broadcast(self.node.id, payload)
        self.metrics.add_bytes_sent(len(block.data))

    def handle_message(self, msg: Message) -> None:
        payload = msg.payload
        cfg = self.node.config

        if isinstance(payload, PrePrepareMsg):
            if payload.view < self.current_view:
                return
            block_hash = hashlib.sha256(payload.block.data).digest()
            prepare = PrepareMsg(view=payload.view, block_id=payload.block.id, hash=block_hash)
            self.node.net.broadcast(self.node.id, prepare)
            self.metrics.add_bytes_sent(68)

        elif isinstance(payload, PrepareMsg):
            if payload.view < self.current_view or self.committed.get(payload.hash):
                return
            self.prepares.setdefault(payload.hash, set()).add(msg.from_id)

            quorum = 2 * cfg.num_faulty
            if len(self.prepares[payload.hash]) >= quorum:
                commit = CommitMsg(view=payload.view, block_id=payload.block_id, hash=payload.hash)
                self.node.net.broadcast(self.node.id, commit)
                self.metrics.add_bytes_sent(68)

        elif isinstance(payload, CommitMsg):
            if payload.view < self.current_view or self.committed.get(payload.hash):
                return
            self.commits.setdefault(payload.hash, set()).add(msg.from_id)

            quorum = 2 * cfg.num_faulty + 1
            if len(self.commits[payload.hash]) >= quorum:
                self.committed[payload.hash] = True
                log.info("[Node %d] PBFT: Committed block %s",
                         self.node.id, payload.hash[:4].hex())
                self.metrics.add_commit(time_since(time.monotonic()))
