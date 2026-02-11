SAMPLE_RATE_HZ = 1  # 1 sample per second

# Default PLC Tag Set (digital + analog)
DEFAULT_TAGS = {
    "EStop_OK": 1,
    "AutoMode": 1,
    "LineSpeed_fpm": 220.0,
    "TankLevel_pct": 65.0,
    "MotorCurrent_A": 12.5,
    "MotorTemp_C": 48.0,
    "VFD_Fault": 0,
    "CommLoss": 0,
    "ValveInlet_Open": 1,
    "ValveDrain_Open": 0,
    "Pump_Run": 1,
    "Pump_CMD": 1,
    "Pressure_psi": 38.0,
    "Flow_gpm": 120.0,
}

# Alarm Rules (SCADA-style)
DEFAULT_ALARMS = [
    {
        "alarm_id": "ALM_101",
        "tag": "TankLevel_pct",
        "type": "LOW",
        "setpoint": 70.0,

        "severity": 3,
        "message": "Tank level LOW"
    },
    {
        "alarm_id": "ALM_102",
        "tag": "TankLevel_pct",
        "type": "HIGH",
        "setpoint": 92.0,
        "severity": 2,
        "message": "Tank level HIGH"
    },
    {
        "alarm_id": "ALM_201",
        "tag": "MotorTemp_C",
        "type": "HIGH",
        "setpoint": 85.0,
        "severity": 2,
        "message": "Motor temperature HIGH"
    },
    {
        "alarm_id": "ALM_202",
        "tag": "MotorCurrent_A",
        "type": "HIGH",
        "setpoint": 22.0,
        "severity": 2,
        "message": "Motor current HIGH"
    },
    {
        "alarm_id": "ALM_301",
        "tag": "VFD_Fault",
        "type": "BOOL_TRUE",
        "setpoint": 1,
        "severity": 1,
        "message": "VFD fault active"
    },
    {
        "alarm_id": "ALM_401",
        "tag": "CommLoss",
        "type": "BOOL_TRUE",
        "setpoint": 1,
        "severity": 1,
        "message": "PLC communication lost"
    },
    {
        "alarm_id": "ALM_501",
        "tag": "EStop_OK",
        "type": "BOOL_FALSE",
        "setpoint": 0,
        "severity": 1,
        "message": "E-Stop NOT OK"
    },
]
