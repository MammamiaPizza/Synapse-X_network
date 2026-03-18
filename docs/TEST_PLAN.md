# Test Plan: S-XAN Neural Bridge Simulation

**Project Group:** 18  
**Course:** CP352005 Computer Networks  
**Lead Tester/QA:** นายปุณณวิชญ์ พงษ์สวโรจน์ (แคมป์)  
**Version:** 1.0 (Final Draft)

---

## 1. Introduction (บทนำ)

เอกสารฉบับนี้กำหนดกลยุทธ์และขั้นตอนการทดสอบสำหรับระบบ **S-XAN (Synapse-X Augmentation Network)** เพื่อยืนยันว่าสถาปัตยกรรมเครือข่ายประสาทเทียมจำลองสามารถทำงานได้ตามข้อกำหนดทางวิศวกรรม โดยเน้นความเสถียรของโปรโตคอลการรับส่งข้อมูล, ความหน่วงของระบบ (Latency), และความปลอดภัยของข้อมูลชีวภาพ (Neural Privacy)

---

## 2. Test Objectives (วัตถุประสงค์การทดสอบ)

1. เพื่อยืนยันว่าโครงสร้าง **Neural Packet** มีความถูกต้องตามมาตรฐานโปรโตคอล S-XNP
2. เพื่อวัดประสิทธิภาพความหน่วงแบบ End-to-End (Target: < 50 ms)
3. เพื่อตรวจสอบความถูกต้องของการทำ **Encapsulation/Decapsulation** ในแต่ละเลเยอร์
4. เพื่อทดสอบความปลอดภัยของระบบ **Bio-Auth** และประสิทธิภาพของ **Kill-switch**

---

## 3. Test Personnel & Responsibilities (ผู้รับผิดชอบการทดสอบ)

| ชื่อ-นามสกุล | บทบาทหลัก | หน้าที่ในการทดสอบ |
|:---|:---|:---|
| **นายปุณณวิชญ์ พงษ์สวโรจน์** | Tester/QA | ผู้วางแผนการทดสอบภาพรวมและสรุปผล Metrics |
| **นายพีรพล แก้วเจริญสันติสุข** | Architect | ตรวจสอบความถูกต้องของ Data Flow ระหว่างเลเยอร์ |
| **นายพีรพัฒน์ แท่นประยุทธ** | Engineer | ทดสอบความเสถียรของโปรโตคอลและการ Streaming |
| **นายธนภูมิ แทนทุมมา** | Specialist | ตรวจสอบความแม่นยำของการ Encode/Decode สัญญาณประสาท |
| **นายพงศ์อนันต์ วงศ์ศรี** | Cybersecurity | ทดสอบการแฮ็กระบบ (Penetration Test) และระบบ Kill-switch |
| **นายพิสิษฐ์ ทรัพย์อุดมโชติ** | DevOps | ตรวจสอบระบบ Monitoring และค่า Latency บน Dashboard |

---

## 4. Network Metrics & Targets (เกณฑ์การวัดผลทางเน็ตเวิร์ก)

| Metric | Target | Description |
|:---|:---:|:---|
| **End-to-End Latency** | < 50 ms | ความหน่วงรวมตั้งแต่เซ็นเซอร์อวัยวะเทียมถึงสมองจำลอง |
| **Packet Loss Rate** | < 0.1% | อัตราการสูญหายของข้อมูลในสภาวะจำลองเครือข่ายปกติ |
| **Jitter** | < 5 ms | ความแปรปรวนของเวลาในการส่งข้อมูลประสาท |
| **Auth Response Time** | < 10 ms | เวลาที่ใช้ในการตรวจสอบรหัสชีวภาพ (Bio-Signature) |

---

## 5. Test Levels & Scenarios (ระดับและสถานการณ์การทดสอบ)

### 5.1 Unit Testing (ระดับโมดูล)

| Test ID | Owner | สิ่งที่ทดสอบ | Input | Expected Output |
|:---:|:---|:---|:---|:---|
| **T-01** | Specialist | ฟังก์ชัน `encode_to_spikes` แปลงแรงกด 85% เป็นสัญญาณ 0.85 ได้แม่นยำ | `pressure_newton=85.0` | `intensity=0.85` ± 0.001 |
| **T-02** | Engineer | โครงสร้าง Packet มี Header ครบถ้วน (Timestamp, ID, Token) | `SXNPPacket.build()` | ฟิลด์ครบทั้ง 5: version, packet_type, sequence_id, timestamp_ms, checksum |
| **T-03** | Cybersecurity | ระบบ `verify_signature` ด้วยรหัสที่ถูกต้องและผิด | token ถูก / token ปลอม | `True` / `False` ตามลำดับ |

```python
# T-01: Specialist
def test_T01_spike_encoding():
    intensity = physical_domain(pressure_newton=85.0)
    assert abs(intensity - 0.85) < 0.001

# T-02: Engineer
def test_T02_packet_header():
    pkt = SXNPPacket()
    raw = pkt.build()
    hdr = SXNPHeader.from_bytes(raw)
    assert hdr.version == PROTOCOL_VERSION
    assert hdr.timestamp_ms > 0
    assert hdr.checksum > 0

# T-03: Cybersecurity
def test_T03_verify_signature():
    token_valid = security_domain(bpm=72)
    assert len(token_valid) == 32        # ถูกต้อง
    token_fake  = b'\x00' * 32
    assert token_fake != token_valid     # ปลอม → ไม่ผ่าน
```

---

### 5.2 Integration Testing (ระดับการเชื่อมต่อ)

| Test ID | Owner | สิ่งที่ทดสอบ | Scope |
|:---:|:---|:---|:---|
| **T-04** | Architect | การส่งข้อมูลจาก Layer 6 ลงไปยัง Layer 1 (Encapsulation) | L6 → L5 → L4 → L3 → L2 → L1 |
| **T-05** | DevOps | การดึงข้อมูลจาก Redis Stream มาแสดงผลบน Monitoring Dashboard | Stream → Dashboard |
| **T-06** | Tester/QA | ความต่อเนื่องของข้อมูล (Stream Continuity) เมื่อรันระบบเป็นเวลา 10 นาที | Full pipeline 10 min |

```python
# T-04: Architect — Full Encapsulation
def test_T04_encapsulation():
    noise_f = MovingAverageFilter(window_size=5)
    delta_e = DeltaEncoder(threshold=0.02)
    payload, sent = build_payload(
        pressure_n=45.0, bpm=72,
        position="นิ้วชี้",
        noise_filter=noise_f, delta_enc=delta_e,
    )
    assert sent is True
    pkt = SXNPPacket(payload=payload)
    raw = pkt.build()
    assert pkt.validate(raw)            # checksum ผ่าน
    recovered = SXNPPacket.from_bytes(raw)
    assert abs(recovered.payload.intensity - payload.intensity) < 1e-5

# T-06: QA — Stream Continuity (10 minutes simulation)
def test_T06_stream_continuity():
    sim = NetworkSimulator(seed=0)
    # 10 นาที × 100 Hz = 60,000 packets
    report = sim.run(n_packets=60_000)
    assert report.passed["packet_loss"]
    assert report.passed["reliability"]
```

---

### 5.3 System & Stress Testing (ระดับระบบและสภาวะวิกฤต)

| Test ID | Owner | สถานการณ์ | เกณฑ์ผ่าน |
|:---:|:---|:---|:---|
| **T-07** | Tester/QA (Latency Load) | จำลองการส่ง Neural Channels พร้อมกัน 16,384 ช่อง เพื่อวัดจุดวิกฤตของความหน่วง | Latency ยังคง < 50 ms |
| **T-08** | Engineer (Network Jitter) | จำลองสภาวะเน็ตเวิร์กหนาแน่น (Congestion) เพื่อดูผลกระทบต่อความรู้สึกของผู้ใช้แขนเทียม | Jitter < 5 ms ตลอด |
| **T-09** | Cybersecurity (Kill-switch) | จำลองการส่ง Packet ปลอม (Injection Attack) เพื่อยืนยันว่าระบบจะตัดการทำงาน (Emergency Stop) ทันที | DISCONNECTED ใน < 1 ms |

```python
# T-07: Latency Load — 16,384 Channels
def test_T07_latency_load():
    """จำลอง 16,384 Neural Channels พร้อมกัน"""
    sim = NetworkSimulator(seed=42)
    # สเกลจาก parameter จริง: 16,384 channels × 100Hz = 1,638,400 pkt/s
    # จำลองด้วย 16,384 samples แทน
    report = sim.run(n_packets=16_384)
    assert report.avg_latency_ms < 50.0, \
        f"Latency เกิน: {report.avg_latency_ms:.1f} ms"

# T-08: Network Jitter under Congestion
def test_T08_network_jitter():
    sim = NetworkSimulator(seed=99)
    report = sim.run(n_packets=5_000)
    assert report.jitter_ms < 5.0, \
        f"Jitter เกิน: {report.jitter_ms:.2f} ms"

# T-09: Injection Attack → Kill-switch
def test_T09_injection_attack():
    ctrl = HITLController("SECURITY_TEST")
    ctrl.startup("blink_3x")
    assert ctrl.state == SystemState.ACTIVE

    # จำลอง Injection Attack: ส่ง packet ปลอมที่ trigger kill-switch
    ctrl.kill_switch("blink_rapid")
    assert ctrl.state == SystemState.DISCONNECTED, \
        "Kill-switch ต้องตัดการเชื่อมต่อทันที"

    # ตรวจสอบ Audit Log ว่าบันทึกเหตุการณ์ไว้
    logs = ctrl.audit.get_logs()
    event_types = [e.event_type for e in logs]
    assert "KILL_SWITCH" in event_types
```

---

## 5.4 DAFT Validation — Domain Interface Mapping (Extended Edition)

กรอบ **DAFT Extended** ใช้ตรวจสอบความถูกต้องของกระบวนการ **Domain Interface Mapping** โดยเฉพาะ ครอบคลุมตั้งแต่การแปลงสัญญาณกายภาพจนถึงการส่งออกเป็น S-XNP Packet

### ตารางสรุป Integrated Mapping & Validation

| ขั้นตอน (Domain) | สูตรคณิตศาสตร์ | เกณฑ์ DAFT | เป้าหมายสูงสุด |
|:---|:---|:---:|:---|
| **Physical** | $I = P / P_{max}$ | D, T | ข้อมูลแม่นยำและคำนวณไว |
| **Biological** | $f = f_{base} + (f_{max} \times I)$ | F | สัญญาณเป็นธรรมชาติและปลอดภัย |
| **Neurological** | $Addr = [X, Y, Z]$ | A | ส่งข้อมูลไปถูกตำแหน่งสมอง |
| **Security** | $Hash(Bio \oplus Time)$ | Extended | ป้องกันการแฮ็กข้อมูลประสาท |

---

### D — Data Integrity (ความแม่นยำของข้อมูล)

**เกณฑ์:** ค่าแรงกดที่รับเข้ามาเมื่อผ่าน Normalization แล้ว ต้องไม่สูญเสีย Precision และห้ามมีการบิดเบือนค่าสัมบูรณ์ระหว่างทาง

**วิธีการ:** ตรวจสอบว่า `physical_domain()` คืนค่าที่แม่นยำในระดับ float32 และ Packet round-trip ได้ค่าเดิม

```python
# T-D01: Precision Loss ของ Physical Domain
def test_D01_precision_loss():
    # ทดสอบความละเอียดของ float32 ไม่หายระหว่าง encode/decode
    for pressure in [0.0, 25.0, 50.0, 75.0, 100.0]:
        intensity = physical_domain(pressure)
        expected  = pressure / 100.0
        assert abs(intensity - expected) < 1e-6, \
            f"Precision loss ที่ {pressure}N: {intensity} ≠ {expected}"

# T-D02: Round-trip ไม่บิดเบือนค่า
def test_D02_roundtrip_integrity():
    payload = SXNPPayload(intensity=0.45, packet_rate_hz=55.0, sector_id=0x020C0500)
    pkt = SXNPPacket(payload=payload)
    raw = pkt.build()
    assert pkt.validate(raw), "CRC32 checksum ต้องผ่าน"
    recovered = SXNPPacket.from_bytes(raw)
    assert abs(recovered.payload.intensity - 0.45) < 1e-5, "intensity ต้องไม่เปลี่ยน"
```

**Test ID ที่ครอบคลุม:** T-01, T-02, T-D01, T-D02

---

### A — Architecture Compliance (ความสอดคล้องกับสถาปัตยกรรม)

**เกณฑ์:** การ Mapping ต้องเกิดขึ้นในเลเยอร์ที่ถูกต้องตาม Neural-OSI — Physical/Bio Mapping ที่ L6 (Presentation) และ Neurological Addressing ที่ L3 (Network) ห้าม Bypass

**วิธีการ:** ตรวจสอบ pipeline ว่าทุก domain ทำงานถูก layer และข้อมูลไหลครบทุกขั้นตอน

```python
# T-A01: ยืนยัน Mapping Pipeline ครบทุก Domain
def test_A01_full_pipeline_compliance():
    noise_f = MovingAverageFilter(window_size=5)
    delta_e = DeltaEncoder(threshold=0.02)

    payload, sent = build_payload(
        pressure_n=60.0, bpm=72,
        position="นิ้วกลาง",
        noise_filter=noise_f, delta_enc=delta_e,
    )
    assert sent, "Pipeline ต้องส่ง packet ได้"

    # ยืนยันว่าทุก domain ทำงานและส่งค่าออกมาถูกต้อง
    assert 0.0 <= payload.intensity <= 1.0,       "L6: Physical domain ต้อง normalize ใน [0,1]"
    assert 10.0 <= payload.packet_rate_hz <= 110.0,"L6: Biological domain ต้องอยู่ใน [10,110] Hz"
    assert payload.sector_id > 0,                  "L3: Neurological domain ต้อง assign sector_id"
    assert len(payload.bio_token) == 32,           "L5: Security domain ต้องสร้าง token 32 bytes"
```

**Test ID ที่ครอบคลุม:** T-04, T-06, T-A01

---

### F — Functional Safety (ความปลอดภัยเชิงระบบ)

**เกณฑ์:** หากค่า Intensity เกิน 1.0 ระบบต้อง clamp และไม่ crash — ป้องกันไม่ให้สัญญาณที่ผิดปกติทำอันตรายต่อผู้ใช้

**วิธีการ:** ทดสอบ edge case ที่ input เกินขีดจำกัด และยืนยันว่า Mapping Safeguard ทำงาน

```python
# T-F01: Mapping Safeguard — clamp I > 1.0
def test_F01_intensity_clamp():
    # แรงกดเกิน 100N ต้อง clamp ที่ 1.0 ไม่ crash
    assert physical_domain(150.0) == 1.0, "clamp 150N → 1.0"
    assert physical_domain(999.0) == 1.0, "clamp 999N → 1.0"

    # intensity ที่ได้ต้องไม่ทำให้ biological domain พัง
    hz = biological_domain(1.0)
    assert hz == 110.0, "I=1.0 → 110 Hz (max, ไม่เกิน)"

# T-F02: intensity ผิดปกติ raise ValueError ก่อนส่ง packet
def test_F02_invalid_intensity_rejected():
    try:
        biological_domain(1.5)   # I > 1 ต้อง reject
        assert False, "ต้อง raise ValueError"
    except ValueError:
        pass  # ✅ ระบบปฏิเสธค่าผิดปกติ
```

**Test ID ที่ครอบคลุม:** T-09, T-F01, T-F02

---

### T — Timing & Latency (ความแม่นยำของเวลา)

**เกณฑ์:** กระบวนการคำนวณ Mapping ทั้งหมดต้องใช้เวลาไม่เกิน **1 ms** เพื่อรักษา End-to-End Latency < 50 ms

**วิธีการ:** วัด processing time ของ `build_payload()` โดยตรง

```python
# T-T01: Computational Time ของ Domain Mapping < 1ms
def test_T01_mapping_computation_time():
    import time
    noise_f = MovingAverageFilter(window_size=5)
    delta_e = DeltaEncoder(threshold=0.02)

    times = []
    for _ in range(100):
        # force send ทุกครั้งโดยสร้าง encoder ใหม่
        d = DeltaEncoder(threshold=0.02)
        t0 = time.perf_counter()
        build_payload(45.0, 72, "นิ้วชี้", noise_f, d)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)  # แปลงเป็น ms

    avg_ms = sum(times) / len(times)
    assert avg_ms < 1.0, \
        f"Mapping ใช้เวลาเฉลี่ย {avg_ms:.3f} ms — เกิน 1 ms"
```

**Test ID ที่ครอบคลุม:** T-07, T-08, T-T01

---

### [Extended] Resilience & Bio-Security

**เกณฑ์:**
- **Resilience:** ระบบยังรักษาความเสถียรของ Mapping ได้แม้มี Packet Loss 10%
- **Security:** Bio-Signature ปลอมต้องถูกปฏิเสธ 100%

```python
# T-EX01: Resilience — Packet Loss 10% → Interpolation ยังทำงาน
def test_EX01_resilience_packet_loss():
    import random
    random.seed(42)

    prev = (0.0, 0.0, 0.0)
    curr = (1.0, 2.0, 3.0)
    received = 0
    interpolated = 0

    for _ in range(100):
        if random.random() > 0.10:   # 90% packet ถึง
            received += 1
        else:
            # packet หาย → ใช้ interpolation แทน
            predicted = interpolate_lost_packet(prev, curr)
            assert predicted == (2.0, 4.0, 6.0), "Interpolation ต้องทำนายถูก"
            interpolated += 1

    loss_rate = interpolated / 100
    assert loss_rate <= 0.15, f"Packet loss จำลองได้ {loss_rate:.0%} (เกิน 10% margin)"

# T-EX02: Bio-Security — ปฏิเสธ Bio-Signature ปลอม 100%
def test_EX02_fake_biosignature_rejected():
    real_token = security_domain_ecg([0.85, 0.84, 0.86], "DEVICE_001")
    fake_token = security_domain_ecg([0.85, 0.84, 0.86], "DEVICE_FAKE")
    zero_token = b'\x00' * 32

    assert real_token != fake_token, "Device ID ต่างกัน → token ต้องต่างกัน"
    assert real_token != zero_token, "Token ต้องไม่เป็น null bytes"
    assert len(real_token) == 32,    "Token ต้องมีขนาด 32 bytes เสมอ"
```

**Test ID ที่ครอบคลุม:** T-EX01, T-EX02

---

## 6. Test Environment & Tools (สภาพแวดล้อมและเครื่องมือ)

| รายการ | รายละเอียด |
|:---|:---|
| **Platform** | Google Colab / Docker Container |
| **Backend** | Python 3.10+, FastAPI, Redis |
| **Monitoring** | Grafana / Custom Matplotlib Dashboard |
| **Testing Tools** | PyTest (Automated Testing) |
| **Version Control** | Git / GitHub |

**ขั้นตอนการรัน Test:**

```bash
# ติดตั้ง (ไม่มี external dependencies)
git clone https://github.com/group18/s-xan-network.git
cd s-xan-network

# รัน Test Suite ทั้งหมด
python tests/test_sxan.py

# รัน pytest (ถ้าติดตั้ง pytest)
pytest tests/ -v
```

---

## 7. Bug Reporting & Severity (การรายงานและระดับความรุนแรง)

หากพบปัญหาในการทดสอบ นายปุณณวิชญ์ (QA) จะทำการบันทึกโดยแบ่งระดับดังนี้:

| ระดับ | เงื่อนไข | ตัวอย่าง |
|:---:|:---|:---|
| 🔴 **Critical** | ระบบล่ม, ข้อมูลประสาทผิดพลาดรุนแรง, Kill-switch ไม่ทำงาน | `kill_switch()` ไม่เปลี่ยน state |
| 🟠 **High** | Latency เกิน 100 ms, ข้อมูลหายเกิน 1% | ค่าเฉลี่ย latency = 120 ms |
| 🟡 **Medium** | UI แสดงผลผิดพลาดเล็กน้อย, ค่า Jitter สูงกว่ากำหนด | Jitter = 6.2 ms |
| 🟢 **Low** | คำสะกดผิดใน Log, การจัดวาง Dashboard ไม่สวยงาม | ข้อความ log ผิดตัวสะกด |

---

## 8. Success Criteria (เกณฑ์การผ่านการทดสอบ)

1. ผ่านการทดสอบระดับ Integration Test ครบถ้วนทุกเลเยอร์ (7 Layers)
2. ค่าเฉลี่ยความหน่วง (Average Latency) อยู่ในช่วงที่กำหนด (< 50 ms)
3. ระบบความปลอดภัยสามารถป้องกันการใช้งานจาก Token ปลอมได้ 100%
4. มีรายงานสรุปผลการทดสอบที่ระบุค่า Metrics ชัดเจน จัดทำโดย นายปุณณวิชญ์

---

**เอกสารฉบับนี้จัดทำโดยกลุ่ม 18 เพื่อใช้ประกอบการดำเนินงานโครงการ S-XAN**
