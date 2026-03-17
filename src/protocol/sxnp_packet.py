"""
S-XNP v2.0 - Synaptic eXtended Network Protocol
โปรโตคอลสำหรับการสื่อสารระหว่างอวัยวะชีวภาพและระบบดิจิทัล
กลุ่ม 18
"""

import struct
import hashlib
import time
import zlib
from dataclasses import dataclass, field
from typing import Optional


# ═══════════════════════════════════════════════
# ค่าคงที่ของโปรโตคอล
# ═══════════════════════════════════════════════
PROTOCOL_VERSION = 0x02
MAX_PRESSURE_N   = 100.0    # แรงกดสูงสุด (นิวตัน)
BASE_FREQ_HZ     = 10.0     # ความถี่พื้นฐาน (Hz)
MAX_FREQ_HZ      = 100.0    # ความถี่สูงสุด (Hz)
DELTA_THRESHOLD  = 0.02     # เกณฑ์ Delta Encoding
MAX_LATENCY_MS   = 200.0    # ความหน่วงสูงสุดที่ยอมรับได้ (ms)
NEURAL_STRESS_LIMIT = 0.85  # ขีดจำกัดความเครียดประสาท (0-1)


@dataclass
class SXNPHeader:
    """
    ส่วนหัวของ S-XNP Packet
    ขนาด: 12 bytes  |  รูปแบบ: Big-endian binary
    """
    version:      int = PROTOCOL_VERSION  # uint8  - เวอร์ชันโปรโตคอล
    packet_type:  int = 0x01              # uint8  - ประเภท Packet (0x01=Data, 0x02=ACK, 0xFF=Kill)
    sequence_id:  int = 0                 # uint16 - ลำดับ Packet (0-65535, วนซ้ำ)
    timestamp_ms: int = 0                 # uint32 - Unix timestamp หน่วยมิลลิวินาที
    checksum:     int = 0                 # uint32 - CRC32 ของ Payload

    STRUCT_FORMAT = "!BBHII"
    SIZE = struct.calcsize(STRUCT_FORMAT)  # = 12 bytes

    def to_bytes(self) -> bytes:
        return struct.pack(
            self.STRUCT_FORMAT,
            self.version,
            self.packet_type,
            self.sequence_id,
            self.timestamp_ms,
            self.checksum,
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "SXNPHeader":
        if len(data) < cls.SIZE:
            raise ValueError(f"ข้อมูลสั้นเกินไป: ต้องการ {cls.SIZE} bytes, ได้รับ {len(data)}")
        fields = struct.unpack(cls.STRUCT_FORMAT, data[:cls.SIZE])
        return cls(*fields)


@dataclass
class SXNPPayload:
    """
    ส่วนข้อมูลของ S-XNP Packet
    บรรจุข้อมูลจากทุก Domain ที่แปลงแล้ว
    """
    intensity:       float = 0.0                                      # float32 - Physical Domain (0.0–1.0)
    packet_rate_hz:  float = BASE_FREQ_HZ                             # float32 - Biological Domain (Hz)
    sector_id:       int   = 0                                        # uint32  - Neurological Domain (3D address)
    bio_token:       bytes = field(default_factory=lambda: b'\x00'*32)# bytes32 - Security Domain (SHA-256)
    neural_stress:   float = 0.0                                      # float32 - ระดับความเครียด (0.0–1.0)

    STRUCT_FORMAT = "!ffI32sf"
    SIZE = struct.calcsize(STRUCT_FORMAT)

    def to_bytes(self) -> bytes:
        return struct.pack(
            self.STRUCT_FORMAT,
            self.intensity,
            self.packet_rate_hz,
            self.sector_id,
            self.bio_token,
            self.neural_stress,
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "SXNPPayload":
        if len(data) < cls.SIZE:
            raise ValueError(f"Payload สั้นเกินไป: ต้องการ {cls.SIZE} bytes")
        fields = struct.unpack(cls.STRUCT_FORMAT, data[:cls.SIZE])
        return cls(
            intensity=fields[0],
            packet_rate_hz=fields[1],
            sector_id=fields[2],
            bio_token=fields[3],
            neural_stress=fields[4],
        )


class SXNPPacket:
    """
    S-XNP Packet ฉบับสมบูรณ์ (Header + Payload)

    การใช้งาน:
        packet = SXNPPacket(header, payload)
        raw = packet.build()          # แปลงเป็น bytes
        ok  = packet.validate(raw)    # ตรวจสอบ checksum
    """

    _sequence_counter: int = 0

    def __init__(self, header: Optional[SXNPHeader] = None, payload: Optional[SXNPPayload] = None):
        self.header  = header  or SXNPHeader()
        self.payload = payload or SXNPPayload()

    def build(self) -> bytes:
        """สร้าง Packet พร้อม Checksum และ Timestamp อัตโนมัติ"""
        self.header.sequence_id  = SXNPPacket._next_seq()
        self.header.timestamp_ms = int(time.time() * 1000) & 0xFFFFFFFF
        payload_bytes            = self.payload.to_bytes()
        self.header.checksum     = self._crc32(payload_bytes)
        return self.header.to_bytes() + payload_bytes

    @staticmethod
    def _next_seq() -> int:
        SXNPPacket._sequence_counter = (SXNPPacket._sequence_counter + 1) % 65536
        return SXNPPacket._sequence_counter

    @staticmethod
    def _crc32(data: bytes) -> int:
        return zlib.crc32(data) & 0xFFFFFFFF

    def validate(self, raw_bytes: bytes) -> bool:
        """ตรวจสอบความถูกต้องของ Packet ด้วย CRC32"""
        min_size = SXNPHeader.SIZE + SXNPPayload.SIZE
        if len(raw_bytes) < min_size:
            return False
        payload_bytes     = raw_bytes[SXNPHeader.SIZE:]
        expected_checksum = self._crc32(payload_bytes)
        return self.header.checksum == expected_checksum

    @classmethod
    def from_bytes(cls, data: bytes) -> "SXNPPacket":
        """แกะ Packet จาก raw bytes"""
        header  = SXNPHeader.from_bytes(data)
        payload = SXNPPayload.from_bytes(data[SXNPHeader.SIZE:])
        return cls(header, payload)

    def __repr__(self) -> str:
        return (
            f"SXNPPacket(seq={self.header.sequence_id}, "
            f"intensity={self.payload.intensity:.3f}, "
            f"rate={self.payload.packet_rate_hz:.1f}Hz, "
            f"sector={self.payload.sector_id:#010x})"
        )
