from typing import Dict, Any


def compute_kpis(latest_ts, tag_snapshot: Dict[str, float], active_alarms) -> Dict[str, Any]:
    comms = "OK" if int(tag_snapshot.get("CommLoss", 0)) == 0 else "LOSS"

    return {
        "active_alarms": len(active_alarms),
        "comms_health": comms,
        "line_speed": float(tag_snapshot.get("LineSpeed_fpm", 0.0)),
        "tank_level": float(tag_snapshot.get("TankLevel_pct", 0.0)),
    }
