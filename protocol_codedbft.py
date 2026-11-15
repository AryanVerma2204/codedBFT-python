from __future__ import annotations

import hashlib
import time

from coding import Decoder, Encoder
from messages import Block, Message, ProposalPacket, VoteMsg
from node import ConsensusProtocol, log, time_since


class CodedBFTProtocol(ConsensusProtocol):
    NAME = "CodedBFT"

    def __init__(self, speculative_execution_enabled: bool = True):
        self.speculative_execution_enabled = speculative_execution_enabled

    def init(self, node) -> None:
        super().init(node)
        self.decoders: dict[bytes, Decoder] = {}
        self.votes: dict[bytes, set[int]] = {}
        self.committed: dict[bytes, bool] = {}

    def propose(self, block: Block) -> None:
        cfg = self.node.config
        view = self.get_current_view()
        if self.node.id != view % cfg.num_nodes:
            return

        block_hash = hashlib.sha256(block.data).digest()
        try:
            encoder = Encoder(block.data, cfg.packet_size)
        except ValueError:
            return

        num_packets = len(block.data) // cfg.packet_size + 20
        for _ in range(num_packets):
            packet = encoder.get_encoded_packet()
            payload = ProposalPacket(view=view, block_id=block.id, hash=block_hash, packet=packet)
            self.node.net.broadcast(self.node.id, payload)
            self.metrics.add_bytes_sent(len(packet))

    def handle_message(self, msg: Message) -> None:
        payload = msg.payload

        if isinstance(payload, ProposalPacket):
            if payload.view < self.current_view or self.committed.get(payload.hash):
                return
            decoder = self.decoders.get(payload.block_id)
            if decoder is None:
                decoder = self.decoders[payload.block_id] = Decoder()
            if decoder.add_packet(payload.packet):
                decoded, err = decoder.get_decoded_data()
                del self.decoders[payload.block_id]
                if err is not None or hashlib.sha256(decoded).digest() != payload.hash:
                    return

                if self.speculative_execution_enabled:
                    vote = VoteMsg(view=payload.view, block_id=payload.block_id, hash=payload.hash)
                    self.node.net.broadcast(self.node.id, vote)
                    self.metrics.add_bytes_sent(68)

        elif isinstance(payload, VoteMsg):
            if payload.view < self.current_view or self.committed.get(payload.hash):
                return
            self.votes.setdefault(payload.hash, set()).add(msg.from_id)

            quorum = 2 * self.node.config.num_faulty + 1
            if len(self.votes[payload.hash]) >= quorum:
                self.committed[payload.hash] = True
                log.info("[Node %d] CodedBFT: Committed block %s",
                         self.node.id, payload.hash[:4].hex())
                self.metrics.add_commit(time_since(time.monotonic()))
