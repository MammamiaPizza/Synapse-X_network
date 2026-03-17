# สถาปัตยกรรม S-XAN Network

## ภาพรวมสถาปัตยกรรม

S-XAN ใช้โมเดล OSI 7 ชั้น โดยแต่ละชั้นมีหน้าที่จำเพาะสำหรับการสื่อสารชีวภาพ-ดิจิทัล

```
Layer 7 - Application    │ User Consent Interface, Medical Dashboard
Layer 6 - Presentation   │ Domain Encoding (Physical/Bio/Neuro/Security)
Layer 5 - Session        │ HITL Controller, Audit Logger, Consent Manager
Layer 4 - Transport      │ Reliability, Checksum, Packet Loss Detection
Layer 3 - Network        │ Anatomical Addressing (sector_id routing)
Layer 2 - Data Link      │ Delta Encoding, Frame Synchronization
Layer 1 - Physical       │ Neural Sensors, Thermal Management (<+1°C)
```

## S-XNP Packet Format

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
├───────────────┬───────────────┬───────────────────────────────────┤
│    version    │  packet_type  │          sequence_id              │
├───────────────────────────────────────────────────────────────────┤
│                         timestamp_ms                              │
├───────────────────────────────────────────────────────────────────┤
│                           checksum                                │
╠═══════════════════════════════════════════════════════════════════╣
│                      intensity (float32)                          │
├───────────────────────────────────────────────────────────────────┤
│                    packet_rate_hz (float32)                        │
├───────────────────────────────────────────────────────────────────┤
│                        sector_id (uint32)                         │
├───────────────────────────────────────────────────────────────────┤
│                      bio_token (32 bytes)                         │
│                           ...                                     │
├───────────────────────────────────────────────────────────────────┤
│                    neural_stress (float32)                         │
└───────────────────────────────────────────────────────────────────┘
 Header: 12 bytes    Payload: 56 bytes    Total: 68 bytes
```

## Data Flow Pipeline

```
[เซ็นเซอร์กายภาพ]
      │ pressure_newton
      ▼
[Physical Domain]    I = pressure / 100
      │ intensity (0.0–1.0)
      ▼
[Signal Conditioning]   I_smooth = MovingAverage(I, n=5)
      │ filtered_intensity
      ▼
[Delta Encoder]      ส่งเฉพาะ |ΔI| > 0.02
      │ (ผ่าน / กรองออก)
      ▼
[Biological Domain]  Hz = 10 + (100 × I)
      │ packet_rate_hz
      ▼
[Neurological Domain]  sector_id = encode(X, Y, Z, region)
      │ sector_id
      ▼
[Security Domain]    token = SHA256(BPM + timestamp)
      │ bio_token
      ▼
[SXNPPacket.build()]  Header + Payload + CRC32
      │ raw bytes
      ▼
[HITL Controller]    ตรวจสอบ latency + neural_stress
      │ (ผ่าน / kill-switch)
      ▼
[Network Transmission]
```

## sector_id Encoding

```
Bit layout ของ uint32 sector_id:
┌────────────┬────────────┬────────────┬────────────┐
│ [31:24]    │ [23:16]    │ [15:8]     │ [7:0]      │
│ brain_reg  │  X coord   │  Y coord   │  Z coord   │
└────────────┴────────────┴────────────┴────────────┘

Brain Region Codes:
0x01 = นิ้วโป้ง    (Thumb — Primary Motor Cortex Area 4)
0x02 = นิ้วชี้     (Index Finger)
0x03 = นิ้วกลาง   (Middle Finger)
0x04 = นิ้วนาง    (Ring Finger)
0x05 = นิ้วก้อย   (Little Finger)
0x10 = ฝ่ามือ     (Palm — Somatosensory Cortex)
```

## HITL State Machine

```
            startup(consent_ok)
OFFLINE ──────────────────────▶ STANDBY ──▶ ACTIVE
   ▲                                  │         │
   │           shutdown()             │         │ neural_stress > 0.85
   └──────────────────────────────────┘         ▼
                                          SAFE_MODE
                                               │
   kill_switch() / latency > 200ms            │ human_approve()
         │                                     ▼
         ▼                                   ACTIVE
   DISCONNECTED
```
