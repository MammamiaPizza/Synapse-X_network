"""
Governance & Human-in-the-Loop (HITL) Safety System
ระบบกำกับดูแลและความปลอดภัยของ S-XAN Network
กลุ่ม 18
"""

import time
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from protocol.sxnp_packet import MAX_LATENCY_MS, NEURAL_STRESS_LIMIT


# ═══════════════════════════════════════════════
# สถานะของระบบ S-XAN
# ═══════════════════════════════════════════════
class SystemState(Enum):
    OFFLINE      = "offline"       # ปิดระบบ
    STANDBY      = "standby"       # รอสัญญาณยืนยัน
    ACTIVE       = "active"        # ทำงานปกติ
    SAFE_MODE    = "safe_mode"     # โหมดความปลอดภัย (ลดสัญญาณ)
    DISCONNECTED = "disconnected"  # ตัดการเชื่อมต่อแล้ว


@dataclass
class AuditEntry:
    """รายการบันทึกเหตุการณ์ (Audit Trail)"""
    timestamp_ms:  int
    event_type:    str
    description:   str
    actor:         str  # "system" | "user" | "medical_staff"
    session_hash:  str  # เข้ารหัสเพื่อความปลอดภัย


class AuditLogger:
    """
    ระบบบันทึกเหตุการณ์ (Audit Trails)
    ทุกการเข้าถึง Session Layer จะถูกบันทึกไว้เพื่อตรวจสอบย้อนกลับ
    ข้อมูลดิบจะ ไม่ถูกบันทึก (Ephemeral) — บันทึกเฉพาะ Event Hash
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._logs: List[AuditEntry] = []

    def log(self, event_type: str, description: str, actor: str = "system"):
        session_hash = hashlib.sha256(
            f"{self.session_id}:{int(time.time())}".encode()
        ).hexdigest()[:16]

        entry = AuditEntry(
            timestamp_ms=int(time.time() * 1000),
            event_type=event_type,
            description=description,
            actor=actor,
            session_hash=session_hash,
        )
        self._logs.append(entry)
        return entry

    def get_logs(self) -> List[AuditEntry]:
        return list(self._logs)

    def export_summary(self) -> str:
        lines = [f"=== Audit Log: {self.session_id} ==="]
        for e in self._logs:
            lines.append(
                f"[{e.timestamp_ms}] {e.event_type} | {e.actor} | {e.description}"
            )
        return "\n".join(lines)


# ═══════════════════════════════════════════════
# Consent Mechanism — ยืนยันความยินยอมก่อนเชื่อมต่อ
# ═══════════════════════════════════════════════
class ConsentManager:
    """
    ระบบยืนยันความยินยอม (User Consent Mechanism)
    ไม่มีการเชื่อมต่ออัตโนมัติโดยที่ผู้ใช้ไม่รู้ตัว
    """

    def __init__(self):
        self._consent_given    = False
        self._consent_timestamp: Optional[int] = None
        self.CONSENT_TIMEOUT_S = 30  # หมดอายุใน 30 วินาที

    def request_consent(self) -> str:
        """สร้างคำขอ Handshake ส่งให้ผู้ใช้"""
        self._consent_given     = False
        self._consent_timestamp = None
        return "⚠️  กรุณายืนยันการเชื่อมต่อ S-XAN: กระพริบตา 3 ครั้ง หรือกัดฟันค้าง 2 วินาที"

    def confirm_consent(self, user_intent_signal: str) -> bool:
        """
        รับสัญญาณจาก User Intent และยืนยันความยินยอม
        user_intent_signal: "blink_3x" | "jaw_clench_2s"
        """
        VALID_SIGNALS = {"blink_3x", "jaw_clench_2s"}
        if user_intent_signal in VALID_SIGNALS:
            self._consent_given     = True
            self._consent_timestamp = int(time.time())
            return True
        return False

    def is_valid(self) -> bool:
        """ตรวจสอบว่า Consent ยังใช้งานได้หรือไม่"""
        if not self._consent_given or self._consent_timestamp is None:
            return False
        elapsed = time.time() - self._consent_timestamp
        return elapsed <= self.CONSENT_TIMEOUT_S

    def revoke(self):
        """ยกเลิก Consent ทันที"""
        self._consent_given    = False
        self._consent_timestamp = None


# ═══════════════════════════════════════════════
# HITL Controller — ควบคุมความปลอดภัยแบบ Real-time
# ═══════════════════════════════════════════════
class HITLController:
    """
    Human-in-the-Loop Safety Controller
    มนุษย์เป็นผู้ตัดสินใจสูงสุดตลอดเวลา

    ฟีเจอร์:
    - Physiological Kill-switch (ตัดทันที)
    - Neural Stress Monitor (Fail-safe Mode)
    - Latency Guard (หยุดเมื่อ >200ms)
    - Medical Parameter Approval
    """

    def __init__(self, session_id: str):
        self.state          = SystemState.OFFLINE
        self.consent        = ConsentManager()
        self.audit          = AuditLogger(session_id)
        self._on_disconnect: List[Callable] = []

        # พารามิเตอร์ที่ต้องอนุมัติโดยแพทย์
        self._max_intensity: float = 0.8
        self._medical_approved      = False

    # ── Life Cycle ──────────────────────────────
    def startup(self, user_intent: str) -> bool:
        """เริ่มระบบ — ต้องได้รับ Consent ก่อนเสมอ"""
        self.state = SystemState.STANDBY
        self.audit.log("STARTUP", "ระบบเริ่มต้น รอการยืนยันจากผู้ใช้", "system")

        if not self.consent.confirm_consent(user_intent):
            self.audit.log("CONSENT_DENIED", "ผู้ใช้ไม่ยืนยัน หรือสัญญาณไม่ถูกต้อง", "user")
            return False

        self.state = SystemState.ACTIVE
        self.audit.log("CONNECTED", "เชื่อมต่อ S-XAN สำเร็จ", "user")
        return True

    def shutdown(self, reason: str = "ผู้ใช้สั่งปิด"):
        """ปิดระบบปกติ"""
        self.consent.revoke()
        self.state = SystemState.OFFLINE
        self.audit.log("SHUTDOWN", reason, "user")
        self._trigger_callbacks()

    # ── Kill-switch ──────────────────────────────
    def kill_switch(self, signal: str):
        """
        Physiological Kill-switch: ตัดการเชื่อมต่อทันทีระดับกายภาพ
        Signals: "blink_rapid" | "jaw_clench_pattern"
        """
        KILL_SIGNALS = {"blink_rapid", "jaw_clench_pattern"}
        if signal in KILL_SIGNALS:
            self.consent.revoke()
            self.state = SystemState.DISCONNECTED
            self.audit.log("KILL_SWITCH", f"ตัดการเชื่อมต่อโดยสัญญาณ: {signal}", "user")
            self._trigger_callbacks()

    # ── Real-time Safety Monitors ────────────────
    def check_latency(self, latency_ms: float) -> bool:
        """
        Incident Management: หยุดทันทีหาก latency > 200ms
        ป้องกันความสับสนของสมองผู้ใช้
        """
        if latency_ms > MAX_LATENCY_MS:
            self.state = SystemState.DISCONNECTED
            self.audit.log(
                "LATENCY_EXCEEDED",
                f"latency={latency_ms:.1f}ms > {MAX_LATENCY_MS}ms — หยุดส่งข้อมูล",
                "system",
            )
            self._trigger_callbacks()
            return False
        return True

    def check_neural_stress(self, stress_level: float) -> SystemState:
        """
        Fail-safe Mode: ลดสัญญาณอัตโนมัติเมื่อ Neural Stress สูงเกินไป
        รอให้มนุษย์เป็นผู้ตัดสินใจว่าจะดำเนินต่อหรือไม่
        """
        if stress_level > NEURAL_STRESS_LIMIT and self.state == SystemState.ACTIVE:
            self.state = SystemState.SAFE_MODE
            self.audit.log(
                "SAFE_MODE",
                f"neural_stress={stress_level:.2f} เกินขีดจำกัด — เปิด Safe Mode",
                "system",
            )
        elif stress_level <= NEURAL_STRESS_LIMIT and self.state == SystemState.SAFE_MODE:
            # รอมนุษย์อนุมัติการกลับสู่ Active Mode
            self.audit.log(
                "SAFE_MODE_READY",
                "ความเครียดลดลงแล้ว รอการอนุมัติจากผู้ดูแล",
                "system",
            )
        return self.state

    def approve_parameter_change(self, new_max_intensity: float, approver: str = "medical_staff") -> bool:
        """
        Medical Oversight: เปลี่ยน parameter ต้องได้รับอนุมัติจากแพทย์
        """
        if not 0.0 < new_max_intensity <= 1.0:
            return False
        self._max_intensity    = new_max_intensity
        self._medical_approved = True
        self.audit.log(
            "PARAM_APPROVED",
            f"max_intensity เปลี่ยนเป็น {new_max_intensity:.2f} อนุมัติโดย {approver}",
            approver,
        )
        return True

    # ── Callback Registration ────────────────────
    def on_disconnect(self, callback: Callable):
        """ลงทะเบียน callback เมื่อระบบตัดการเชื่อมต่อ"""
        self._on_disconnect.append(callback)

    def _trigger_callbacks(self):
        for cb in self._on_disconnect:
            try:
                cb()
            except Exception:
                pass

    # ── Status ───────────────────────────────────
    def get_status(self) -> dict:
        return {
            "state":            self.state.value,
            "consent_valid":    self.consent.is_valid(),
            "max_intensity":    self._max_intensity,
            "medical_approved": self._medical_approved,
            "audit_entries":    len(self.audit.get_logs()),
        }
