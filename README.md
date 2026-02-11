# 🚨 PLC + SCADA HMI Tag Monitor Simulator

A Streamlit-based industrial automation project that simulates a **PLC + SCADA/HMI monitoring environment**, including:

- Live tag monitoring  
- Historian logging (SQLite)  
- Alarm engine with ACK + Shelving  
- Trend chart visualization  
- KPI dashboard  
- Exportable maintenance reports  

This project demonstrates workflows used in real-world:

- Manufacturing plants  
- Process automation systems  
- SCADA control rooms  
- Industrial maintenance & reliability teams  

---

## 🚀 Features

### ✅ Live PLC Tag Table
Simulates real-time PLC tag values such as:

- MotorCurrent_A  
- TankLevel_pct  
- LineSpeed_fpm  
- Pump_Run  
- Estop_OK  

Each tag includes a SCADA-style **quality status**.

---

### ✅ Alarm Console (ACK + Shelving)

Includes industrial alarm behavior:

- High / Low alarm thresholds  
- Severity levels  
- Operator acknowledgment (ACK)  
- Alarm shelving (temporary silence)  
- Silence All mode  

---

### ✅ Historian Logging (SQLite)

All tag values are automatically written into a historian database:

- `data/historian.db`

Supports real SCADA concepts like:

- Sampling intervals  
- Historical trending  
- Report generation  

---

### ✅ Trends Dashboard

Select multiple tags and visualize the last 10 minutes of data:

- Multi-tag trending  
- Operator-style monitoring  
- Real-time chart refresh  

---

### ✅ Reports + CSV Export

Export historian + alarm data into CSV format:

- Maintenance reporting  
- Shift handoff logs  
- Reliability documentation  

Exports saved into:

