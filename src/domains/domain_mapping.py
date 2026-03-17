"""
Domain Interface Mapping
แปลงสัญญาณชีวภาพและกายภาพเป็นค่าเครือข่าย S-XNP
กลุ่ม 18
"""

import math
import hashlib
import time
from collections import deque
from typing import Tuple, Optional

from protocol.sxnp_packet import (
    MAX_PRESSURE_N, BASE_FREQ_HZ, MAX_FREQ_HZ,
    DELTA_THRESHOLD, SXNPPayload
)


# ═══════════════════════════════════════════════
# 1. Physical Domain — แรงกดนิ้ว → float32 intensity
# ═══════════════════════════════════════════════
def physical_domain(pressure_newton: float) -> float:
    """
    แปลงแรงบีบนิ้วมือ (Physical) → ค่า intensity (0.0–1.0)

    สูตร: I = pressure / MAX_PRESSURE_N
    - รับค่า: แรงกดหน่วยนิวตัน (N)
    - คืนค่า: float ในช่วง 0.0–1.0 (Normalized)
    """
    if pressure_newton < 0:
        raise ValueError("แรงกดต้องไม่ติดลบ")
    return min(pressure_newton / MAX_PRESSURE_N, 1.0)


# ═══════════════════════════════════════════════
# 2. Biological Domain — intensity → Packet Rate (Hz)
# ═══════════════════════════════════════════════
def biological_domain(intensity: float) -> float:
    """
    จำลองการยิงกระแสไฟฟ้าของเส้นประสาท (Frequency Coding)

    สูตร: Hz = BASE_FREQ + (MAX_FREQ × I)
    - รับค่า: intensity (0.0–1.0)
    - คืนค่า: ความถี่การส่ง Packet (10–110 Hz)
    """
    if not 0.0 <= intensity <= 1.0:
        raise ValueError(f"intensity ต้องอยู่ใน [0, 1], ได้รับ: {intensity}")
    return BASE_FREQ_HZ + (MAX_FREQ_HZ * intensity)


# ═══════════════════════════════════════════════
# 3. Neurological Domain — ตำแหน่งร่างกาย → uint32 sector_id
# ═══════════════════════════════════════════════

# พิกัดอ้างอิงตำแหน่งร่างกาย (Anatomical Coordinate System)
BODY_POSITIONS = {
    "นิ้วโป้ง":  (10, 5,  0, 0x01),
    "นิ้วชี้":   (12, 5,  0, 0x02),
    "นิ้วกลาง":  (14, 5,  0, 0x03),
    "นิ้วนาง":   (13, 5,  0, 0x04),
    "นิ้วก้อย":  (11, 5,  0, 0x05),
    "ฝ่ามือ":    (12, 8,  0, 0x10),
}


def neurological_domain(x: int, y: int, z: int, brain_region_code: int) -> int:
    """
    แปลงพิกัด 3D ตำแหน่งร่างกาย → uint32 sector_id

    รูปแบบ sector_id (32 bit):
    [31:24] brain_region_code  (8 bit)
    [23:16] X coordinate       (8 bit)
    [15: 8] Y coordinate       (8 bit)
    [ 7: 0] Z coordinate       (8 bit)
    """
    sector_id = (
        (brain_region_code & 0xFF) << 24 |
        (x & 0xFF) << 16 |
        (y & 0xFF) << 8  |
        (z & 0xFF)
    )
    return sector_id


def get_sector_id(position_name: str) -> int:
    """ดึง sector_id จากชื่อตำแหน่งร่างกาย"""
    if position_name not in BODY_POSITIONS:
        raise ValueError(f"ไม่รู้จักตำแหน่ง: {position_name}. ตัวเลือก: {list(BODY_POSITIONS.keys())}")
    x, y, z, region = BODY_POSITIONS[position_name]
    return neurological_domain(x, y, z, region)


# ═══════════════════════════════════════════════
# 4. Security Domain — BPM → bio_token (Dynamic Key)
# ═══════════════════════════════════════════════
def security_domain(bpm: int) -> bytes:
    """
    สร้าง Bio-Authentication Token จากอัตราการเต้นหัวใจ

    สูตร: Token = Hash(BPM + timestamp)
    - รับค่า: ชีพจร (Beats Per Minute)
    - คืนค่า: SHA-256 hash ขนาด 32 bytes
    """
    if not 30 <= bpm <= 220:
        raise ValueError(f"BPM ผิดปกติ: {bpm} (ปกติ 30–220)")
    timestamp = str(int(time.time()))
    raw = f"{bpm}:{timestamp}".encode("utf-8")
    return hashlib.sha256(raw).digest()


def security_domain_ecg(r_peak_intervals: list, device_id: str) -> bytes:
    """
    Enhanced: สร้าง bio_token จากรูปคลื่น ECG (R-Peak Intervals)

    สูตร: Key = SHA-256(R-Peak Intervals + DeviceID)
    แม่นยำกว่า BPM เฉลี่ย — ใช้อัตลักษณ์เฉพาะบุคคล (Liveness Detection)
    """
    interval_str = ",".join(f"{v:.3f}" for v in r_peak_intervals)
    raw = f"{interval_str}:{device_id}".encode("utf-8")
    return hashlib.sha256(raw).digest()


# ═══════════════════════════════════════════════
# 5. Signal Conditioning — กรองสัญญาณรบกวน (Noise Filter)
# ═══════════════════════════════════════════════
class MovingAverageFilter:
    """
    Moving Average Filter สำหรับลด Noise ในสัญญาณชีวภาพ

    สูตร: I_smooth = (1/n) × Σ I_i
    """

    def __init__(self, window_size: int = 5):
        if window_size < 1:
            raise ValueError("window_size ต้องมากกว่า 0")
        self.window_size = window_size
        self._buffer: deque = deque(maxlen=window_size)

    def update(self, value: float) -> float:
        """เพิ่มค่าใหม่และคืนค่าเฉลี่ยที่กรองแล้ว"""
        self._buffer.append(value)
        return sum(self._buffer) / len(self._buffer)

    def reset(self):
        self._buffer.clear()


# ═══════════════════════════════════════════════
# 6. Transmission Optimization — Delta Encoding
# ═══════════════════════════════════════════════
class DeltaEncoder:
    """
    Delta Encoding: ส่ง Packet เฉพาะเมื่อค่าเปลี่ยนเกิน Threshold
    ลดภาระ Network Bandwidth และประหยัดพลังงาน

    หลักการ: ส่งก็ต่อเมื่อ |I_current − I_last| > Threshold
    """

    def __init__(self, threshold: float = DELTA_THRESHOLD):
        self.threshold     = threshold
        self._last_sent    = None
        self.packets_saved = 0
        self.packets_sent  = 0

    def should_transmit(self, current_value: float) -> bool:
        """ตัดสินใจว่าควรส่ง Packet หรือไม่"""
        if self._last_sent is None:
            self._last_sent = current_value
            self.packets_sent += 1
            return True

        delta = abs(current_value - self._last_sent)
        if delta > self.threshold:
            self._last_sent = current_value
            self.packets_sent += 1
            return True

        self.packets_saved += 1
        return False

    @property
    def efficiency(self) -> float:
        """อัตราการประหยัด Packet (0.0–1.0)"""
        total = self.packets_sent + self.packets_saved
        return self.packets_saved / total if total > 0 else 0.0


# ═══════════════════════════════════════════════
# 7. Error Concealment — Linear Interpolation
# ═══════════════════════════════════════════════
def interpolate_lost_packet(prev_pos: Tuple[float, float, float],
                             curr_pos: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    พยากรณ์ตำแหน่งที่หายไปจาก Packet Loss (Linear Interpolation)

    สูตร: P_next = P_current + (P_current − P_previous)
    ใช้ที่ฝั่ง Receiver เพื่อให้สัญญาณความรู้สึกไหลลื่น
    """
    return tuple(curr + (curr - prev) for prev, curr in zip(prev_pos, curr_pos))


# ═══════════════════════════════════════════════
# Pipeline ครบวงจร: สัญญาณกายภาพ → SXNPPayload
# ═══════════════════════════════════════════════
def build_payload(
    pressure_n:   float,
    bpm:          int,
    position:     str,
    noise_filter: MovingAverageFilter,
    delta_enc:    DeltaEncoder,
) -> Tuple[Optional[SXNPPayload], bool]:
    """
    Pipeline แปลงสัญญาณชีวภาพทุก Domain เป็น SXNPPayload เดียว

    คืนค่า: (payload, should_transmit)
    - payload=None หมายความว่า Delta Encoding กรองออก (ไม่ส่ง)
    """
    # 1. Physical → intensity
    raw_intensity  = physical_domain(pressure_n)

    # 5. Signal Conditioning
    intensity      = noise_filter.update(raw_intensity)

    # 6. Delta Encoding
    if not delta_enc.should_transmit(intensity):
        return None, False

    # 2. Biological → packet rate
    rate_hz        = biological_domain(intensity)

    # 3. Neurological → sector_id
    sector_id      = get_sector_id(position)

    # 4. Security → bio_token
    bio_token      = security_domain(bpm)

    payload = SXNPPayload(
        intensity=intensity,
        packet_rate_hz=rate_hz,
        sector_id=sector_id,
        bio_token=bio_token,
    )
    return payload, True
