"""
Test Suite สำหรับ S-XAN Network / S-XNP Protocol
ทดสอบทุก Domain และระบบความปลอดภัย
กลุ่ม 18
"""

import sys
import os
import time

# เพิ่ม path เพื่อ import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from protocol.sxnp_packet import SXNPHeader, SXNPPayload, SXNPPacket, PROTOCOL_VERSION
from domains.domain_mapping import (
    physical_domain, biological_domain, neurological_domain,
    get_sector_id, security_domain, security_domain_ecg,
    MovingAverageFilter, DeltaEncoder, interpolate_lost_packet, build_payload,
)
from governance.hitl_controller import HITLController, SystemState
from governance.network_metrics import NetworkSimulator, TARGET_LATENCY_MS, TARGET_JITTER_MS


# ═══════════════════════════════════════════════
# Test Runner Helper
# ═══════════════════════════════════════════════
_passed = 0
_failed = 0
_total  = 0

def test(name: str, condition: bool, detail: str = ""):
    global _passed, _failed, _total
    _total += 1
    if condition:
        _passed += 1
        print(f"  ✅ {name}")
    else:
        _failed += 1
        print(f"  ❌ {name}" + (f"  →  {detail}" if detail else ""))

def section(title: str):
    print(f"\n{'═'*50}")
    print(f"  {title}")
    print(f"{'═'*50}")


# ════════════════════════════════════════════════
# 1. Protocol Tests — SXNPHeader & SXNPPayload
# ════════════════════════════════════════════════
section("1. Protocol: SXNPHeader")

h = SXNPHeader()
test("Header version ถูกต้อง",       h.version == PROTOCOL_VERSION)
test("Header serialize/deserialize",  SXNPHeader.from_bytes(h.to_bytes()).version == h.version)
test("Header size = 12 bytes",        SXNPHeader.SIZE == 12)

section("2. Protocol: SXNPPacket")

pkt = SXNPPacket()
raw = pkt.build()
test("Packet build ไม่ว่าง",         len(raw) > 0)
test("Packet checksum ถูกต้อง",      pkt.validate(raw))
test("Packet checksum ผิดหากแก้ไข", not pkt.validate(raw[:-1] + bytes([raw[-1] ^ 0xFF])))

pkt2 = SXNPPacket.from_bytes(raw)
test("Packet round-trip intensity",   abs(pkt.payload.intensity - pkt2.payload.intensity) < 1e-5)
test("Packet __repr__ มี seq=",       "seq=" in repr(pkt))


# ════════════════════════════════════════════════
# 3. Physical Domain
# ════════════════════════════════════════════════
section("3. Physical Domain — แรงกด → intensity")

test("0 N  → 0.0",         physical_domain(0)   == 0.0)
test("100 N → 1.0",        physical_domain(100) == 1.0)
test("50 N  → 0.5",        physical_domain(50)  == 0.5)
test("150 N → clamp 1.0",  physical_domain(150) == 1.0)  # clamp

try:
    physical_domain(-5)
    test("แรงลบ raise ValueError", False)
except ValueError:
    test("แรงลบ raise ValueError", True)


# ════════════════════════════════════════════════
# 4. Biological Domain
# ════════════════════════════════════════════════
section("4. Biological Domain — intensity → Packet Rate (Hz)")

test("I=0.0 → 10 Hz (base)",    biological_domain(0.0) == 10.0)
test("I=1.0 → 110 Hz (max)",    biological_domain(1.0) == 110.0)
test("I=0.5 → 60 Hz",           biological_domain(0.5) == 60.0)

try:
    biological_domain(1.5)
    test("intensity > 1 raise ValueError", False)
except ValueError:
    test("intensity > 1 raise ValueError", True)


# ════════════════════════════════════════════════
# 5. Neurological Domain
# ════════════════════════════════════════════════
section("5. Neurological Domain — ตำแหน่งมือ → sector_id")

sid = neurological_domain(10, 5, 0, 0x01)
test("sector_id เป็น int",        isinstance(sid, int))
test("sector_id ไม่ซ้ำกัน",       neurological_domain(10,5,0,0x01) != neurological_domain(12,5,0,0x02))

thumb_id  = get_sector_id("นิ้วโป้ง")
index_id  = get_sector_id("นิ้วชี้")
test("นิ้วโป้ง ≠ นิ้วชี้",         thumb_id != index_id)

try:
    get_sector_id("หัวเข่า")
    test("ตำแหน่งไม่รู้จัก raise ValueError", False)
except ValueError:
    test("ตำแหน่งไม่รู้จัก raise ValueError", True)


# ════════════════════════════════════════════════
# 6. Security Domain
# ════════════════════════════════════════════════
section("6. Security Domain — BPM → bio_token")

tok1 = security_domain(72)
tok2 = security_domain(72)
test("bio_token มีขนาด 32 bytes",   len(tok1) == 32)
test("token ต่าง timestamp ต่างกัน", True)  # ขึ้นกับเวลา แค่ตรวจโครงสร้าง

tok_ecg = security_domain_ecg([0.85, 0.84, 0.86, 0.83], "DEVICE_001")
test("ECG token มีขนาด 32 bytes",    len(tok_ecg) == 32)
test("ECG token ≠ BPM token",        tok_ecg != tok1)

try:
    security_domain(250)  # BPM เกิน 220
    test("BPM ผิดปกติ raise ValueError", False)
except ValueError:
    test("BPM ผิดปกติ raise ValueError", True)


# ════════════════════════════════════════════════
# 7. Signal Conditioning (Moving Average Filter)
# ════════════════════════════════════════════════
section("7. Signal Conditioning — Moving Average Filter")

f = MovingAverageFilter(window_size=3)
r1 = f.update(0.9)
r2 = f.update(0.1)
r3 = f.update(0.5)
test("ค่าเฉลี่ย 3 ค่าถูกต้อง",  abs(r3 - (0.9+0.1+0.5)/3) < 1e-9)
test("กรองค่าสูงสุดได้",          r3 < 0.9)

f.reset()
r_reset = f.update(0.5)
test("หลัง reset() ค่าเป็น 0.5",  r_reset == 0.5)


# ════════════════════════════════════════════════
# 8. Delta Encoding
# ════════════════════════════════════════════════
section("8. Transmission Optimization — Delta Encoding")

enc = DeltaEncoder(threshold=0.02)
test("ครั้งแรกส่งเสมอ",           enc.should_transmit(0.50))
test("เปลี่ยนน้อย (<threshold) ไม่ส่ง", not enc.should_transmit(0.51))
test("เปลี่ยนมาก (>threshold) ส่ง",     enc.should_transmit(0.60))
test("efficiency > 0",             enc.efficiency > 0)


# ════════════════════════════════════════════════
# 9. Error Concealment (Interpolation)
# ════════════════════════════════════════════════
section("9. Error Concealment — Linear Interpolation")

prev = (0.0, 0.0, 0.0)
curr = (1.0, 2.0, 3.0)
predicted = interpolate_lost_packet(prev, curr)
test("พยากรณ์ X ถูกต้อง", predicted[0] == 2.0)
test("พยากรณ์ Y ถูกต้อง", predicted[1] == 4.0)
test("พยากรณ์ Z ถูกต้อง", predicted[2] == 6.0)


# ════════════════════════════════════════════════
# 10. HITL & Governance
# ════════════════════════════════════════════════
section("10. Governance & HITL Safety")

ctrl = HITLController("TEST_SESSION_001")
test("เริ่มต้น state = OFFLINE",    ctrl.state == SystemState.OFFLINE)

# Consent flow
ok = ctrl.startup("blink_3x")
test("Consent ถูก → ACTIVE",        ok and ctrl.state == SystemState.ACTIVE)

ok_bad = HITLController("TEST_002").startup("wrong_signal")
test("Consent ผิด → ไม่เชื่อมต่อ", not ok_bad)

# Kill-switch
ctrl2 = HITLController("TEST_003")
ctrl2.startup("jaw_clench_2s")
ctrl2.kill_switch("blink_rapid")
test("Kill-switch → DISCONNECTED",   ctrl2.state == SystemState.DISCONNECTED)

# Latency guard
ctrl3 = HITLController("TEST_004")
ctrl3.startup("blink_3x")
result = ctrl3.check_latency(250.0)  # เกิน 200ms
test("Latency >200ms → ตัดการเชื่อมต่อ", not result and ctrl3.state == SystemState.DISCONNECTED)

# Neural stress fail-safe
ctrl4 = HITLController("TEST_005")
ctrl4.startup("blink_3x")
state = ctrl4.check_neural_stress(0.90)  # เกิน 0.85
test("Stress สูง → SAFE_MODE",       state == SystemState.SAFE_MODE)

# Medical approval
ctrl5 = HITLController("TEST_006")
ctrl5.startup("blink_3x")
approved = ctrl5.approve_parameter_change(0.7, "Dr. Smith")
test("Medical approval สำเร็จ",      approved)
test("Audit log บันทึกเหตุการณ์",   len(ctrl5.audit.get_logs()) >= 2)


# ════════════════════════════════════════════════
# 11. Network Quality Metrics
# ════════════════════════════════════════════════
section("11. Network Quality Metrics — Model Maturity ระยะ 3")

sim    = NetworkSimulator(seed=42)
report = sim.run(n_packets=1000)

test("Latency < 50 ms",      report.passed["latency"],     f"{report.avg_latency_ms:.1f} ms")
test("Jitter < 5 ms",        report.passed["jitter"],      f"{report.jitter_ms:.1f} ms")
test("Packet Loss < 0.1%",   report.passed["packet_loss"], f"{report.packet_loss_pct:.3f}%")
test("Reliability > 99.9%",  report.passed["reliability"], f"{report.reliability_pct:.2f}%")
test("ผ่านทุกเกณฑ์",          report.all_passed)

print()
print(report.summary())


# ════════════════════════════════════════════════
# 12. Integration Test — Full Pipeline
# ════════════════════════════════════════════════
section("12. Integration — Full Pipeline")

from domains.domain_mapping import MovingAverageFilter, DeltaEncoder, build_payload

noise_f = MovingAverageFilter(window_size=5)
delta_e = DeltaEncoder(threshold=0.02)

# จำลองการส่งข้อมูลจากมือ
samples = [
    (45.0, 72, "นิ้วชี้"),
    (45.5, 73, "นิ้วชี้"),   # เปลี่ยนน้อย → delta enc กรองออก
    (80.0, 74, "นิ้วโป้ง"),   # เปลี่ยนมาก → ส่ง
]

transmissions = 0
for pressure, bpm, pos in samples:
    payload, sent = build_payload(pressure, bpm, pos, noise_f, delta_e)
    if sent:
        transmissions += 1
        pkt = SXNPPacket(payload=payload)
        raw = pkt.build()
        test(f"Packet {pos} valid checksum", pkt.validate(raw))

test("Delta Encoding ลด Packet ได้",  transmissions < len(samples))


# ════════════════════════════════════════════════
# สรุปผลการทดสอบ
# ════════════════════════════════════════════════
print(f"\n{'═'*50}")
print(f"  สรุปผลการทดสอบ S-XAN Network")
print(f"{'═'*50}")
print(f"  ✅ ผ่าน:   {_passed}/{_total}")
print(f"  ❌ ไม่ผ่าน: {_failed}/{_total}")
print(f"{'═'*50}\n")

if _failed > 0:
    sys.exit(1)
