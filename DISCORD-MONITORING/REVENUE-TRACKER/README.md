# Qubic Revenue Tracker

This Python tool monitors revenue performance of your Qubic IDs via the [Qubic.li API](https://qubic.li) and sends periodic status updates to a Discord channel using a webhook.

---

## 💡 Features

- ✅ Tracks specified Qubic IDs and their revenue percentages
- ✅ Displays network average and personal average
- ✅ Sends formatted updates to a Discord channel
- ✅ Highlights low-performing or new IDs with emojis and colors
- ✅ Runs on an hourly loop (customizable)
- ✅ Logs all events to a file

---

## 📦 Requirements

- Python 3.8+
- Install required packages:

```bash
pip install requests colorama
```

---

## ⚙️ Configuration

Edit these variables in the script:

```python
DISCORD_WEBHOOK_URL = 'YOUR_DISCORD_WEBHOOK_URL'
CHECK_INTERVAL = 3600  # seconds (1 hour default)
IDS_TO_TRACK = ['ID1', 'ID2', 'ID3']
```

---

## 🚀 How to Use

1. Clone or download the script
2. Open `revenue_tracker.py`
3. Replace `DISCORD_WEBHOOK_URL` and `IDS_TO_TRACK` with your own
4. Run the script:

```bash
python revenue_tracker.py
```

---

## 📊 Output Example

Console:
```
=== Network Statistics ===
Network Average: 99.4%
Created At: 2025-05-28T00:00:00Z

ID: ABC12345...
Index: 124
🟢 Revenue: 100.0%
```

Discord message:
```
**Network Average** : 99.4%
**Your Average**    : 98.7%
**Active IDs**      : 3
🔴 `ABC12345...` | Index: 124 | Revenue: **96.5%**
🟢 `XYZ98765...` | Index: 97 | Revenue: **100.0%** ⭐
...
*Updated: 2025-05-28 01:00:00*
```

---

## 📁 Logs

All activity is saved to `revenue_tracker.log` for auditing and debugging.

---

## 🛑 Stop the Script

Press `CTRL + C` to stop it safely. It handles keyboard interrupts gracefully.

---
