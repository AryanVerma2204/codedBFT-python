from __future__ import annotations

import random
import struct

_HEADER = struct.Struct(">IIHQ")


def _coefficients(index: int, k: int) -> int:
    if index < k:
        return 1 << index
    coeff = random.Random(index).getrandbits(k)
    return coeff or 1


class Encoder:
    def __init__(self, data: bytes, packet_size: int):
        packet_size &= 0xFFFF
        if not data or packet_size == 0:
            raise ValueError("gorsa: invalid input")
        self.packet_size = packet_size
        self.data_len = len(data)
        self.k = -(-len(data) // packet_size)
        padded = data + bytes(self.k * packet_size - len(data))
        self._symbols = [
            int.from_bytes(padded[i * packet_size:(i + 1) * packet_size], "big")
            for i in range(self.k)
        ]
        self._next_index = 0

    def get_encoded_packet(self) -> bytes:
        idx = self._next_index
        self._next_index += 1
        coeff = _coefficients(idx, self.k)
        if idx < self.k:
            value = self._symbols[idx]
        else:
            value = 0
            i = 0
            while coeff:
                if coeff & 1:
                    value ^= self._symbols[i]
                coeff >>= 1
                i += 1
        header = _HEADER.pack(self.k, self.data_len, self.packet_size, idx)
        return header + value.to_bytes(self.packet_size, "big")


class Decoder:
    def __init__(self) -> None:
        self.k: int | None = None
        self.data_len = 0
        self.packet_size = 0
        self._rows: dict[int, tuple[int, int]] = {}
        self._result: bytes | None = None

    def add_packet(self, packet: bytes) -> bool:
        if self._result is not None:
            return True
        if len(packet) < _HEADER.size:
            return False
        k, data_len, packet_size, idx = _HEADER.unpack_from(packet)
        if self.k is None:
            self.k, self.data_len, self.packet_size = k, data_len, packet_size
        elif (k, data_len, packet_size) != (self.k, self.data_len, self.packet_size):
            return False

        coeff = _coefficients(idx, k)
        value = int.from_bytes(packet[_HEADER.size:], "big")
        rows = self._rows
        while coeff:
            pivot = coeff.bit_length() - 1
            row = rows.get(pivot)
            if row is None:
                rows[pivot] = (coeff, value)
                break
            coeff ^= row[0]
            value ^= row[1]

        if len(rows) == k:
            self._solve()
            return True
        return False

    def _solve(self) -> None:
        solved: list[int] = [0] * self.k
        for p in range(self.k):
            coeff, value = self._rows[p]
            rest = coeff ^ (1 << p)
            while rest:
                b = rest.bit_length() - 1
                value ^= solved[b]
                rest ^= 1 << b
            solved[p] = value
        ps = self.packet_size
        data = b"".join(v.to_bytes(ps, "big") for v in solved)
        self._result = data[: self.data_len]
        self._rows.clear()

    def get_decoded_data(self) -> tuple[bytes | None, Exception | None]:
        data, ok = self._result, self._result is not None
        if not ok:
            return None, fmt.Errorf("decoding failed")
        return data, None
