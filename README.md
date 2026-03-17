# S-XAN Network — S-XNP Protocol v2.0

> **Synaptic eXtended Augmentation Network**  
> โปรเจกต์ระบบเครือข่ายสำหรับการสื่อสารระหว่างอวัยวะชีวภาพและระบบดิจิทัล  
> **กลุ่ม 18** | วิชาเครือข่ายคอมพิวเตอร์

---

## ภาพรวม

S-XAN (Synaptic eXtended Augmentation Network) คือสถาปัตยกรรมเครือข่ายที่ออกแบบมาเพื่อ **แปลงสัญญาณชีวภาพ** จากร่างกายมนุษย์ (แรงกด, จังหวะประสาท, ตำแหน่งร่างกาย, ชีพจร) ให้กลายเป็น **Packet ดิจิทัล** ที่ส่งผ่านโปรโตคอล S-XNP v2.0

```
ร่างกายมนุษย์                     เครือข่ายดิจิทัล
─────────────────────────────────────────────────────
นิ้วกด (45N)  ──[Physical]──▶  float32 intensity = 0.45
เส้นประสาท    ──[Biological]──▶ Packet Rate = 55 Hz  
ตำแหน่งมือ    ──[Neurological]─▶ uint32 sector_id
ชีพจร (72bpm) ──[Security]───▶  bytes bio_token (SHA-256)
                                      │
                              ┌───────▼────────┐
                              │  S-XNP Packet  │
                              │  Header+Payload│
                              └────────────────┘
```

---

## โครงสร้างโปรเจกต์

```
s-xan-network/
├── src/
│   ├── protocol/
│   │   └── sxnp_packet.py        # S-XNP Packet (Header + Payload)
│   ├── domains/
│   │   └── domain_mapping.py     # การแปลงค่าจากทุก Domain
│   └── governance/
│       ├── hitl_controller.py    # HITL Safety & Governance
│       └── network_metrics.py    # วัดผลคุณภาพเครือข่าย
├── tests/
│   └── test_sxan.py              # Test Suite ครบ 52 กรณี
├── docs/
│   ├── ARCHITECTURE.md           # สถาปัตยกรรมระบบ
│   └── ETHICS.md                 # จริยธรรมและกฎหมาย
└── README.md
```

---

## การติดตั้ง

ต้องการเฉพาะ **Python 3.10+** ไม่มี dependencies ภายนอก

```bash
# Clone หรือดาวน์โหลดโปรเจกต์
git clone https://github.com/group18/s-xan-network.git
cd s-xan-network

# รัน Test Suite
python tests/test_sxan.py
```

ผลลัพธ์ที่คาดหวัง:
```
══════════════════════════════════════════════
  สรุปผลการทดสอบ S-XAN Network
══════════════════════════════════════════════
  ✅ ผ่าน:    52/52
  ❌ ไม่ผ่าน:  0/52
══════════════════════════════════════════════
```

---

## Domain Interface Mapping

### 1. Physical Domain — แรงกดนิ้ว → `float32 intensity`

```python
from src.domains.domain_mapping import physical_domain

intensity = physical_domain(pressure_newton=45.0)
# → 0.45  (45N / 100N_max)
```

| Input (N) | Output (intensity) |
|-----------|-------------------|
| 0         | 0.00              |
| 50        | 0.50              |
| 100       | 1.00              |
| >100      | 1.00 (clamp)      |

---

### 2. Biological Domain — intensity → Packet Rate (Hz)

```python
from src.domains.domain_mapping import biological_domain

rate_hz = biological_domain(intensity=0.45)
# → 55.0 Hz  (จำลองความถี่ยิงกระแสประสาท)
# สูตร: Hz = 10 + (100 × I)
```

---

### 3. Neurological Domain — ตำแหน่งมือ → `uint32 sector_id`

```python
from src.domains.domain_mapping import get_sector_id

sector = get_sector_id("นิ้วชี้")
# → 0x020C0500  (region=0x02, X=12, Y=5, Z=0)
```

รูปแบบ `sector_id` (32 bit):
```
[31:24] brain_region_code
[23:16] X coordinate
[15: 8] Y coordinate
[ 7: 0] Z coordinate
```

---

### 4. Security Domain — BPM → `bytes bio_token`

```python
from src.domains.domain_mapping import security_domain, security_domain_ecg

# พื้นฐาน (BPM)
token = security_domain(bpm=72)

# Enhanced (ECG R-Peak Intervals)
token = security_domain_ecg(
    r_peak_intervals=[0.85, 0.84, 0.86, 0.83],
    device_id="DEVICE_001"
)
# → SHA-256 hash 32 bytes (Liveness Detection)
```

---

### 5. Signal Conditioning — Moving Average Filter

```python
from src.domains.domain_mapping import MovingAverageFilter

f = MovingAverageFilter(window_size=5)
smooth = f.update(raw_signal)
# ลด Noise และ Jitter จากกล้ามเนื้อ
```

---

### 6. Transmission Optimization — Delta Encoding

```python
from src.domains.domain_mapping import DeltaEncoder

enc = DeltaEncoder(threshold=0.02)
if enc.should_transmit(current_value):
    # ส่ง Packet เฉพาะเมื่อค่าเปลี่ยนเกิน threshold
    ...

print(f"ประหยัด Packet ได้ {enc.efficiency:.1%}")
```

---

## การสร้าง S-XNP Packet

```python
from src.protocol.sxnp_packet import SXNPPacket, SXNPPayload
from src.domains.domain_mapping import build_payload, MovingAverageFilter, DeltaEncoder

# สร้าง Pipeline
noise_filter = MovingAverageFilter(window_size=5)
delta_enc    = DeltaEncoder(threshold=0.02)

# แปลงสัญญาณ → Payload
payload, should_send = build_payload(
    pressure_n=45.0,
    bpm=72,
    position="นิ้วชี้",
    noise_filter=noise_filter,
    delta_enc=delta_enc,
)

if should_send:
    packet = SXNPPacket(payload=payload)
    raw    = packet.build()           # → bytes พร้อมส่ง
    valid  = packet.validate(raw)     # → True
    print(packet)
    # SXNPPacket(seq=1, intensity=0.450, rate=55.0Hz, sector=0x020c0500)
```

---

## Governance & HITL Safety

```python
from src.governance.hitl_controller import HITLController

ctrl = HITLController(session_id="SESSION_001")

# ต้องยืนยัน Consent ก่อนเสมอ
ok = ctrl.startup("blink_3x")         # หรือ "jaw_clench_2s"

# ตรวจสอบ latency real-time
ctrl.check_latency(latency_ms=18.5)   # False + ตัดการเชื่อมต่อถ้า >200ms

# ตรวจสอบ neural stress
ctrl.check_neural_stress(0.90)        # → SystemState.SAFE_MODE ถ้า >0.85

# Kill-switch ฉุกเฉิน
ctrl.kill_switch("blink_rapid")       # → SystemState.DISCONNECTED ทันที

# Medical approval สำหรับ parameter สำคัญ
ctrl.approve_parameter_change(0.7, approver="Dr. Smith")

# ดู Audit Log
print(ctrl.audit.export_summary())
```

---

## ผลการทดสอบคุณภาพเครือข่าย (Model Maturity ระยะ 3)

```
╔══════════════════════════════════════╗
║  S-XAN Network Quality Report        ║
╠══════════════════════════════════════╣
║  Latency      18.5 ms    < 50.0 ms   ✅ ผ่าน
║  Jitter        1.2 ms    < 5.0 ms    ✅ ผ่าน
║  Packet Loss  0.020 %    < 0.1 %     ✅ ผ่าน
║  Reliability  99.98 %    > 99.9 %    ✅ ผ่าน
╠══════════════════════════════════════╣
║  สรุป: ✅ ผ่านทุกเกณฑ์                  ║
╚══════════════════════════════════════╝
```

---

## Model Maturity

| ระยะ | ชื่อ | รูปแบบ | ทิศทาง | สถานะ |
|------|------|--------|--------|-------|
| 1 | Initial Simulation | JSON | Unidirectional | ✅ เสร็จ |
| 2 | Standardized Protocol | Binary (S-XNP v2.0) | Full-Duplex | ✅ เสร็จ |
| 3 | High-Fidelity Candidate | Binary + Bio-Auth | Full-Duplex | ✅ Live Demo Ready |

---

## Ethics & Regulations

| หัวข้อ | รายละเอียด |
|--------|-----------|
| Neural Privacy | ห้ามดักฟัง/บันทึก Sensory Data เชิงพาณิชย์ |
| Data Ownership | ผู้ใช้เป็นเจ้าของข้อมูล 100% (Ephemeral Processing) |
| IEEE 11073 | มาตรฐานการสื่อสารอุปกรณ์การแพทย์ |
| PDPA / GDPR | Encryption ทุกชั้น + Bio-Auth |
| ISO 13485 | ควบคุมความร้อน ≤ +1°C ต่อเนื้อเยื่อ |
| Neural Rights Law | รองรับกฎหมายสิทธิทางสมองในอนาคต |

---

## สมาชิกกลุ่ม 18

| ชื่อ | รับผิดชอบ |
|------|-----------|
| นายพีรพล แก้วเจริญสันติสุข | Architect — Neural-OSI Design, Interface Contracts |
| นายพีรพัฒน์ แท่นประยุทธ | Engineer — Protocol Design (S-XNP Packet), Domain Interface Mapping |
| นายธนภูมิ แทนทุมมา | Specialist — Neural Spike Encoding, AI Mediator |
| นายพงศ์อนันต์ วงศ์ศรี | Cybersecurity — Bio-Encryption, Kill-switch, Neural Privacy |
| นายพิสิษฐ์ ทรัพย์อุดมโชติ | DevOps — Governance & HITL Safety, Network Quality Metrics |
| นายปุณณวิชญ์ พงษ์สวโรจน์ | Tester/QA — Test Plan, Latency Benchmarks, Final Report |

---

*S-XAN Network v2.0 — กลุ่ม 18*
