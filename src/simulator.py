import random
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

import numpy as np


@dataclass
class TagSimulator:
    tags: Dict[str, float]
    sample_rate_hz: int = 1

    def __post_init__(self):
        self.base = dict(self.tags)
        self.last_snapshot = dict(self.tags)
        self._t = 0

    def reset(self):
        self.tags = dict(self.base)
        self.last_snapshot = dict(self.base)
        self._t = 0

    def step(self, ts: datetime) -> Dict[str, float]:
        """
        Simulates a small process line:
        - Line speed fluctuates
        - Tank level rises/falls based on inlet/drain + pump status
        - Motor current and temp relate to speed + load
        - Random faults: comm loss, VFD fault, estop trip
        """
        self._t += 1

        # --- Random fault injection (rare) ---
        if random.random() < 0.005:
            self.tags["CommLoss"] = 1
        if random.random() < 0.008:
            self.tags["VFD_Fault"] = 1
        if random.random() < 0.003:
            self.tags["EStop_OK"] = 0

        # --- Self-recover some faults (unless estop) ---
        if self.tags["CommLoss"] == 1 and random.random() < 0.25:
            self.tags["CommLoss"] = 0
        if self.tags["VFD_Fault"] == 1 and random.random() < 0.20:
            self.tags["VFD_Fault"] = 0
        if self.tags["EStop_OK"] == 0 and random.random() < 0.10:
            self.tags["EStop_OK"] = 1

        # If comm loss or estop, freeze/stop outputs
        if self.tags["CommLoss"] == 1 or self.tags["EStop_OK"] == 0:
            self.tags["Pump_Run"] = 0
            self.tags["LineSpeed_fpm"] = max(0.0, self.tags["LineSpeed_fpm"] - 30.0)
        else:
            # Speed target drift
            target = 220 + 30 * np.sin(self._t / 30.0)
            self.tags["LineSpeed_fpm"] += (target - self.tags["LineSpeed_fpm"]) * 0.15
            self.tags["LineSpeed_fpm"] += random.uniform(-2.0, 2.0)
            self.tags["LineSpeed_fpm"] = max(0.0, min(350.0, self.tags["LineSpeed_fpm"]))

            # Pump command/run logic
            if self.tags["VFD_Fault"] == 1:
                self.tags["Pump_Run"] = 0
            else:
                self.tags["Pump_Run"] = 1 if self.tags.get("Pump_CMD", 1) == 1 else 0

        # --- Tank level dynamics ---
        inlet = 1 if int(self.tags.get("ValveInlet_Open", 0)) == 1 else 0
        drain = 1 if int(self.tags.get("ValveDrain_Open", 0)) == 1 else 0
        pump = 1 if int(self.tags.get("Pump_Run", 0)) == 1 else 0

        delta = 0.0
        delta += 0.18 * inlet
        delta -= 0.22 * drain
        delta -= 0.10 * pump
        delta += random.uniform(-0.05, 0.05)

        self.tags["TankLevel_pct"] = float(np.clip(self.tags["TankLevel_pct"] + delta, 0.0, 100.0))

        # --- Pressure/flow relate to pump + speed ---
        self.tags["Flow_gpm"] = float(
            np.clip(80 + 0.25 * self.tags["LineSpeed_fpm"] + 25 * pump + random.uniform(-5, 5), 0, 250)
        )
        self.tags["Pressure_psi"] = float(
            np.clip(25 + 0.08 * self.tags["LineSpeed_fpm"] + 18 * pump + random.uniform(-2, 2), 0, 120)
        )

        # --- Motor current/temp relate to speed/load ---
        load = 0.4 + (self.tags["Flow_gpm"] / 250.0)
        self.tags["MotorCurrent_A"] = float(
            np.clip(6 + 0.04 * self.tags["LineSpeed_fpm"] * load + random.uniform(-0.8, 0.8), 0, 40)
        )
        self.tags["MotorTemp_C"] = float(
            np.clip(35 + 1.2 * self.tags["MotorCurrent_A"] + random.uniform(-1.0, 1.0), 20, 120)
        )

        # Snapshot for UI
        self.last_snapshot = dict(self.tags)
        return self.last_snapshot
