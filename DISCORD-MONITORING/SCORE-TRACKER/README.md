# 🧠 Qubic ID Performance Monitor

This Python script tracks your Qubic identities' score performance, solution rates, and network metrics. It generates a full-color summary as a **PNG image** and sends it to your Discord via webhook every hour.

---

## 🔍 Features

- ✅ Fetches real-time Qubic score stats via `qubic.li` API
- ✅ Highlights performance of your specified IDs
- ✅ Detects **IDLE state** if no score increase for 25+ minutes
- ✅ Estimates **new ID unlock progress** and time required
- ✅ Calculates **safe ID limits** based on current performance
- ✅ Logs data locally and sends a **clean Discord image report**

---

## 📦 Requirements

- Python 3.8+
- Install dependencies:

```bash
pip install requests colorama pillow
```

---

## ⚙️ Configuration

Edit the following at the top of the script:

```python
WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL"
YOUR_IDS = ['ID1', 'ID2', 'ID3']  # Replace with your identities
```
---

## 📌 Notes

- Epochs reset **every Wednesday at 12:00 UTC**
- Network currently has **676 max slots**
- Script estimates `solutions/hour` per ID for accurate forecasting

---

## 🛑 Stop the Script

Use `CTRL + C` — graceful shutdown is handled with logging.

---

## ⚠️ Disclaimer

This tool uses public guest credentials on `qubic.li`. Always monitor your identities manually for verification. Use responsibly.
