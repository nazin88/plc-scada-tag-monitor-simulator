from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

import pandas as pd


@dataclass
class AlarmRule:
    alarm_id: str
    tag: str
    type: str          # HIGH / LOW / BOOL_TRUE / BOOL_FALSE
    setpoint: float
    severity: int      # 1 = critical
    message: str


@dataclass
class AlarmState:
    active: bool = False
    acked: bool = False
    shelved_until_utc: Optional[datetime] = None
    last_value: Optional[float] = None
    last_change_utc: Optional[datetime] = None


class AlarmEngine:
    def __init__(self, rules: List[Dict[str, Any]]):
        self.rules = [AlarmRule(**r) for r in rules]
        self.state: Dict[str, AlarmState] = {r.alarm_id: AlarmState() for r in self.rules}

    def reset(self):
        for aid in self.state:
            self.state[aid] = AlarmState()

    def _is_shelved(self, alarm_id: str, now_utc: datetime) -> bool:
        s = self.state[alarm_id].shelved_until_utc
        return s is not None and now_utc < s

    def _trip(self, rule: AlarmRule, value: float) -> bool:
        if rule.type == "HIGH":
            return value >= rule.setpoint
        if rule.type == "LOW":
            return value <= rule.setpoint
        if rule.type == "BOOL_TRUE":
            return int(value) == 1
        if rule.type == "BOOL_FALSE":
            return int(value) == 0
        return False

    def evaluate(self, ts: datetime, tags: Dict[str, float]):
        """
        Returns:
          - alarm_events: list of dicts (RAISED/CLEARED)
          - active_alarms: dict of active states
        """
        now_utc = ts.astimezone(timezone.utc)
        events = []

        for rule in self.rules:
            val = float(tags.get(rule.tag, 0.0))
            st = self.state[rule.alarm_id]
            st.last_value = val

            shelved = self._is_shelved(rule.alarm_id, now_utc)
            tripped = self._trip(rule, val)

            # If shelved, do not raise new alarms
            if shelved and not st.active:
                continue

            # Raise
            if tripped and not st.active:
                st.active = True
                st.acked = False
                st.last_change_utc = now_utc
                events.append({
                    "alarm_id": rule.alarm_id,
                    "tag": rule.tag,
                    "state": "RAISED",
                    "severity": rule.severity,
                    "message": rule.message,
                    "value": val
                })

            # Clear
            if (not tripped) and st.active:
                st.active = False
                st.last_change_utc = now_utc
                events.append({
                    "alarm_id": rule.alarm_id,
                    "tag": rule.tag,
                    "state": "CLEARED",
                    "severity": rule.severity,
                    "message": rule.message,
                    "value": val
                })

        return events, self.get_active()

    # --- Operator actions ---
    def ack(self, alarm_id: str):
        if alarm_id in self.state and self.state[alarm_id].active:
            self.state[alarm_id].acked = True

    def shelve(self, alarm_id: str, minutes: int = 5):
        if alarm_id in self.state:
            self.state[alarm_id].shelved_until_utc = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    # --- Query helpers ---
    def get_active(self) -> Dict[str, AlarmState]:
        return {aid: st for aid, st in self.state.items() if st.active}

    def get_active_ids(self) -> List[str]:
        return [aid for aid, st in self.state.items() if st.active]

    def get_active_df(self) -> pd.DataFrame:
        rows = []
        now_utc = datetime.now(timezone.utc)

        for rule in self.rules:
            stt = self.state[rule.alarm_id]
            if not stt.active:
                continue

            shelved_now = (stt.shelved_until_utc is not None and now_utc < stt.shelved_until_utc)

            rows.append({
                "alarm_id": rule.alarm_id,
                "tag": rule.tag,
                "severity": rule.severity,
                "message": rule.message,
                "acked": "YES" if stt.acked else "NO",
                "shelved": "YES" if shelved_now else "NO",
                "value": stt.last_value
            })

        if not rows:
            return pd.DataFrame()

        return pd.DataFrame(rows).sort_values(["severity", "alarm_id"])
