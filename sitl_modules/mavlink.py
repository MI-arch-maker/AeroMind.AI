"""Codec MAVLink-like minimaliste pour simulation pédagogique.

Ce module ne remplace pas pymavlink et ne doit pas être utilisé pour piloter
un appareil réel. Il fournit un framing déterministe pour les tests SITL.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import ClassVar

START_SIGN = 0xFE
HEADER = struct.Struct("<BBBBB")  # len, seq, sysid, compid, msgid


def crc_x25(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return crc & 0xFFFF


@dataclass(frozen=True)
class SimMessage:
    msg_id: int
    payload: bytes
    sequence: int = 0
    system_id: int = 1
    component_id: int = 1

    def encode(self) -> bytes:
        if not 0 <= self.msg_id <= 255 or len(self.payload) > 255:
            raise ValueError("msg_id et payload doivent tenir dans un frame v1")
        header = HEADER.pack(len(self.payload), self.sequence & 0xFF, self.system_id & 0xFF, self.component_id & 0xFF, self.msg_id)
        checksum = crc_x25(header + self.payload)
        return bytes([START_SIGN]) + header + self.payload + struct.pack("<H", checksum)

    @classmethod
    def decode(cls, frame: bytes) -> "SimMessage":
        if len(frame) < 8 or frame[0] != START_SIGN:
            raise ValueError("frame SITL invalide")
        length, sequence, system_id, component_id, msg_id = HEADER.unpack(frame[1:6])
        expected = 1 + HEADER.size + length + 2
        if len(frame) != expected:
            raise ValueError(f"taille de frame invalide: attendu {expected}, reçu {len(frame)}")
        payload = frame[6 : 6 + length]
        received_crc = struct.unpack("<H", frame[-2:])[0]
        if crc_x25(frame[1:-2]) != received_crc:
            raise ValueError("checksum MAVLink-like invalide")
        return cls(msg_id, payload, sequence, system_id, component_id)


@dataclass(frozen=True)
class Heartbeat:
    armed: bool
    mode: str

    MESSAGE_ID: ClassVar[int] = 0

    def to_message(self, sequence: int = 0) -> SimMessage:
        mode_bytes = self.mode.encode("ascii")[:15]
        payload = struct.pack("<?B15s", self.armed, len(mode_bytes), mode_bytes.ljust(15, b"\0"))
        return SimMessage(self.MESSAGE_ID, payload, sequence)

    @classmethod
    def from_message(cls, message: SimMessage) -> "Heartbeat":
        if message.msg_id != cls.MESSAGE_ID or len(message.payload) != 17:
            raise ValueError("message heartbeat incompatible")
        armed, size, mode = struct.unpack("<?B15s", message.payload)
        return cls(armed=armed, mode=mode[:size].decode("ascii"))
