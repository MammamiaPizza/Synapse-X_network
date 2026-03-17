"""
Network Quality Metrics Simulator
จำลองและวัดผลคุณภาพเครือข่าย S-XAN ตาม Model Maturity
กลุ่ม 18
"""

import random
import time
import statistics
from dataclasses import dataclass, field
from typing import List, Dict

# เกณฑ์เป้าหมาย (Target Benchmarks)
TARGET_LATENCY_MS  = 50.0    # ความหน่วงรวม < 50ms
TARGET_JITTER_MS   = 5.0     # ความนิ่งของเวลา < 5ms
TARGET_PACKET_LOSS = 0.001   # ข้อมูลสูญหาย < 0.1%
TARGET_RELIABILITY = 0.999   # ความน่าเชื่อถือ > 99.9%


@dataclass
class NetworkSample:
    """ผลการวัดคุณภาพ 1 ครั้ง"""
    timestamp_ms: int
    latency_ms:   float
    packet_lost:  bool


@dataclass
class QualityReport:
    """รายงานสรุปคุณภาพเครือข่าย"""
    avg_latency_ms:  float
    jitter_ms:       float
    packet_loss_pct: float
    reliability_pct: float
    sample_count:    int
    passed:          Dict[str, bool] = field(default_factory=dict)

    def __post_init__(self):
        self.passed = {
            "latency":     self.avg_latency_ms  < TARGET_LATENCY_MS,
            "jitter":      self.jitter_ms        < TARGET_JITTER_MS,
            "packet_loss": self.packet_loss_pct  < (TARGET_PACKET_LOSS * 100),
            "reliability": self.reliability_pct  > (TARGET_RELIABILITY * 100),
        }

    @property
    def all_passed(self) -> bool:
        return all(self.passed.values())

    def summary(self) -> str:
        lines = ["╔══════════════════════════════════════╗",
                 "║  S-XAN Network Quality Report        ║",
                 "╠══════════════════════════════════════╣"]
        metrics = [
            ("Latency",     f"{self.avg_latency_ms:.1f} ms",  f"< {TARGET_LATENCY_MS} ms",  self.passed["latency"]),
            ("Jitter",      f"{self.jitter_ms:.1f} ms",       f"< {TARGET_JITTER_MS} ms",   self.passed["jitter"]),
            ("Packet Loss", f"{self.packet_loss_pct:.3f} %",  "< 0.1 %",                   self.passed["packet_loss"]),
            ("Reliability", f"{self.reliability_pct:.2f} %",  "> 99.9 %",                  self.passed["reliability"]),
        ]
        for name, result, target, ok in metrics:
            status = "✅ ผ่าน" if ok else "❌ ไม่ผ่าน"
            lines.append(f"║  {name:<12} {result:<10} {target:<12} {status}")
        lines.append("╠══════════════════════════════════════╣")
        overall = "✅ ผ่านทุกเกณฑ์" if self.all_passed else "❌ บางเกณฑ์ไม่ผ่าน"
        lines.append(f"║  สรุป: {overall:<32}║")
        lines.append(f"║  จำนวนตัวอย่าง: {self.sample_count:<24}║")
        lines.append("╚══════════════════════════════════════╝")
        return "\n".join(lines)


class NetworkSimulator:
    """
    จำลองการส่ง Packet ในเครือข่าย S-XAN
    ใช้ค่าจากเอกสาร Model Maturity ระยะที่ 3
    """

    # พารามิเตอร์จำลองตามผลการทดสอบจริง (ระยะที่ 3)
    SIM_LATENCY_MEAN  = 18.5   # ms
    SIM_LATENCY_STD   = 1.2    # ms  (= Jitter ที่วัดได้)
    SIM_LOSS_RATE     = 0.0002  # 0.02%

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self._samples: List[NetworkSample] = []

    def send_packet(self) -> NetworkSample:
        """จำลองการส่ง Packet 1 ชุด"""
        latency  = max(0.0, random.gauss(self.SIM_LATENCY_MEAN, self.SIM_LATENCY_STD))
        lost     = random.random() < self.SIM_LOSS_RATE
        sample   = NetworkSample(
            timestamp_ms=int(time.time() * 1000),
            latency_ms=latency,
            packet_lost=lost,
        )
        self._samples.append(sample)
        return sample

    def run(self, n_packets: int = 1000) -> QualityReport:
        """รันการจำลองและสร้างรายงาน"""
        self._samples.clear()
        for _ in range(n_packets):
            self.send_packet()
        return self.generate_report()

    def generate_report(self) -> QualityReport:
        """สร้าง QualityReport จากตัวอย่างที่เก็บไว้"""
        if not self._samples:
            raise RuntimeError("ยังไม่มีข้อมูล กรุณา run() ก่อน")

        latencies = [s.latency_ms for s in self._samples]
        lost      = sum(1 for s in self._samples if s.packet_lost)
        n         = len(self._samples)

        avg_latency  = statistics.mean(latencies)
        jitter       = statistics.stdev(latencies) if len(latencies) > 1 else 0.0
        loss_pct     = (lost / n) * 100
        reliability  = ((n - lost) / n) * 100

        return QualityReport(
            avg_latency_ms=avg_latency,
            jitter_ms=jitter,
            packet_loss_pct=loss_pct,
            reliability_pct=reliability,
            sample_count=n,
        )
