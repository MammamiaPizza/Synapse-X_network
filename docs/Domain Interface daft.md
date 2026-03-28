# Integrated Domain Mapping & DAFT Validation
**กลุ่ม 18 — S-XAN Network Project**

> **เป้าหมาย:** การเปลี่ยนข้อมูลจากอวัยวะและร่างกายให้เป็นตัวเลขดิจิทัล (S-XNP Protocol) พร้อมระบบตรวจสอบความถูกต้องตามมาตรฐานวิศวกรรมเครือข่าย

---

## 1. Physical Domain — การแปลงแรงกดกายภาพ

### การ Mapping
รับแรงบีบที่นิ้วมือ (Pressure - P) หน่วยเป็นนิวตัน (N) แล้วทำการ Normalize ให้อยู่ในช่วง `0.0` ถึง `1.0` บันทึกลงในฟิลด์ **`float32 intensity`**

$$\text{Intensity} = \frac{\text{แรงกดปัจจุบัน}}{\text{แรงกดสูงสุด (100N)}}$$

### DAFT Validation

| ตัวอักษร | หมวด | รายละเอียด |
|---|---|---|
| **D** | Data Integrity | ตรวจสอบว่าความละเอียดของแรงกด (Precision) ไม่สูญหายระหว่างการแปลงค่าจาก Analog เป็น Digital |
| **T** | Timing | ขั้นตอนการ Normalize ต้องใช้เวลาประมวลผล **< 0.5 ms** เพื่อรักษาความไวของการสัมผัส |

---

## 2. Biological Domain — การแปลงเป็นจังหวะประสาท (Spike)

### การ Mapping
นำค่า Intensity (I) มาเลียนแบบการยิงกระแสไฟฟ้าของประสาทจริง (Frequency Coding) เพื่อกำหนดความถี่ในการส่ง Packet ใน **เลเยอร์ที่ 6 (Presentation)**

$$\text{ความถี่ (Hz)} = 10\text{Hz} + (100\text{Hz} \times \text{Intensity})$$

### DAFT Validation

| ตัวอักษร | หมวด | รายละเอียด |
|---|---|---|
| **F** | Functional Safety | ติดตั้งเกณฑ์ปลอดภัย (Safety Threshold) — หากความถี่ > **110Hz** ระบบต้องจำกัดค่าทันทีเพื่อป้องกันสมองช็อก |
| **A** | Architecture | ยืนยันว่าการสร้างรหัส Spike ต้องเกิดขึ้นภายใน **เลเยอร์ที่ 6** ตามโครงสร้าง Neural-OSI เท่านั้น |

---

## 3. Neurological Domain — การระบุตำแหน่งพิกัดร่างกาย

### การ Mapping
รับตำแหน่งจากเซ็นเซอร์ (นิ้วโป้ง, นิ้วชี้, ฝ่ามือ) มาแปลงเป็นพิกัด 3 มิติ (Anatomical Addressing) บันทึกลงในฟิลด์ **`uint32 sector_id`**

```
Address = [พิกัด X, พิกัด Y, พิกัด Z, รหัสพื้นที่สมอง]
```

### DAFT Validation

| ตัวอักษร | หมวด | รายละเอียด |
|---|---|---|
| **A** | Architecture | ตรวจสอบว่า Routing ใน **เลเยอร์ที่ 3 (Network)** สามารถส่งข้อมูลไปยังพิกัดปลายทางได้อย่างแม่นยำ **100%** |
| **D** | Data Integrity | ตรวจสอบ Addressing Mapping ว่าไม่มีการส่งความรู้สึกผิดตำแหน่ง เช่น สัมผัสนิ้วชี้แต่ส่งไปสมองส่วนนิ้วโป้ง |

---

## 4. Security Domain — การสร้างรหัสผ่านจากชีพจร

### การ Mapping
รับค่าอัตราการเต้นของหัวใจ (BPM) มาเป็นตัวแปรในการสร้างกุญแจสุ่ม (Dynamic Key) บันทึกลงในฟิลด์ **`bytes bio_token`**

```
Token = Hash(ค่า BPM + เวลาปัจจุบัน)
```

### DAFT Validation

| ตัวอักษร | หมวด | รายละเอียด |
|---|---|---|
| **Extended** | Bio-Resilience | ทดสอบการส่งข้อมูลด้วย Token ที่ล้าสมัยหรือผิดพลาด — ระบบใน **เลเยอร์ที่ 5 (Session)** ต้องสั่ง Kill-switch ตัดการเชื่อมต่อทันที |
| **F** | Functional Safety | ยืนยันว่าระบบ Bio-Auth จะไม่ก่อให้เกิด Latency จนส่งผลกระทบต่อความเร็วรวมของเครือข่าย |

---

## ตารางสรุป Integrated Mapping & DAFT Validation

| โดเมน (Domain) | ตรรกะการแปลงค่า (Mapping) | ฟิลด์ใน Packet | การตรวจสอบ (DAFT) |
|---|---|---|---|
| **Physical** | `I = P / 100` | `float32 intensity` | ความแม่นยำและความเร็ว (D & T) |
| **Biological** | Spike Frequency (Hz) | Packet Rate | ความปลอดภัยของสัญญาณ (F) |
| **Neurological** | พิกัด 3D (X, Y, Z) | `uint32 sector_id` | ความถูกต้องของเลเยอร์ (A) |
| **Security** | Dynamic Hash | `bytes bio_token` | การป้องกันการแฮ็ก (Extended) |
