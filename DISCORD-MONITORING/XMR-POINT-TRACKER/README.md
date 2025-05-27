# 📈 Qubic XMR Points Tracker

A Python script to track your Qubic identities' `xmrPoints` performance and rankings. Sends hourly summaries to a Discord channel via webhook with colored indicators, ranks, averages, and revenue breakdowns.

---

## 💡 Features

- ✅ Tracks specified Qubic IDs
- ✅ Fetches `xmrPoints`, revenue %, and global ranking
- ✅ Calculates **network average**, **median**, **max**, and your **personal average**
- ✅ Ranks your IDs visually with 🏆/🥈/🥉 emojis
- ✅ Color indicators for over/under performance
- ✅ Highlights **new computors** with ⭐
- ✅ Sends a **Discord-formatted report** every hour
- ✅ Logs every update to a `.log` file

---

## ⚙️ Configuration

Edit these variables in the script before running:

```python
DISCORD_WEBHOOK_URL = 'YOUR_DISCORD_WEBHOOK_URL'
IDS_TO_TRACK = ['ID1', 'ID2', 'ID3']
CHECK_INTERVAL = 3600  # seconds
```

---

## 📦 Requirements

- Python 3.8+
- Install dependencies:

```bash
pip install requests colorama
```

---

## 🚀 Usage

Simply run:

```bash
python xmr_points_tracker.py
```

The script will:

1. Authenticate with the Qubic API using guest credentials
2. Fetch current `xmrPoints` and ranking data
3. Compare your IDs' performance to the network
4. Generate a Discord message
5. Repeat every hour

---

## 🖥 Console Output Example

```
=== XMR Points Network Statistics ===
Total Computors: 674
Network Average: 45.1K
Network Median: 38.4K
Network Max: 98.7K

ID: ABC12345...
Index: 132
XMR Points: 53.2K (53200)
Rank: #42/674 🏆
Revenue: 98.1%
```

---

## 📡 Discord Message Example

```
📊 XMR Points Tracker Report
Network Stats:
• Total Computors: 674
• Network Average: 45.1K
• Network Median: 38.4K
• Network Max: 98.7K

Your Stats:
• Your Average: 52.3K (115% of network avg)
• Active IDs: 3
• Total XMR Points: 157.0K

Your IDs:
🏆 #42 🟢 `ABC12345...` | Index: 132 | XMR: 53.2K (118% of avg) | Rev: 98.1%
...
*Updated: 2025-05-28 01:00:00*
```

---


## 🛑 Stop Gracefully

Use `CTRL + C`. The script handles interrupts and logs the shutdown.

---

## ⚠️ Disclaimer

This script uses public guest credentials provided by `qubic.li`. Use responsibly and verify all data manually.
