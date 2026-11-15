from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    from_id: int
    to: int
    payload: Any


@dataclass
class Block:
    id: bytes
    proposer: int
    view: int
    timestamp: float
    data: bytes


@dataclass
class ProposalPacket:
    view: int
    block_id: bytes
    hash: bytes
    packet: bytes


@dataclass
class VoteMsg:
    view: int
    block_id: bytes
    hash: bytes


@dataclass
class NewViewMsg:
    requested_view: int


@dataclass
class PrePrepareMsg:
    view: int
    block: Block


@dataclass
class PrepareMsg:
    view: int
    block_id: bytes
    hash: bytes


@dataclass
class CommitMsg:
    view: int
    block_id: bytes
    hash: bytes
