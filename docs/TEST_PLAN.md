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
