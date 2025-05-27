# 📊 Qubic Score Monitor

A fully terminal-based Qubic monitoring tool built with the [`rich`](https://github.com/Textualize/rich) library to visualize node and identity stats in real time. Runs in a continuous loop, fetching Qubic network data every 5 minutes and displaying it with progress bars, panels, and real-time metrics.

---

## 🚀 Features

- 🔒 Authenticates with `qubic.li` API (guest login)
- 🎨 Fully colored terminal UI using `rich`
- 📈 Real-time visualization of:
  - Epoch progress and remaining time
  - Network solution rate and averages
  - Computor and candidate stats
  - Your active ID ranks, scores, rates
  - Progress toward new IDs
- 🧮 Computes:
  - Your total solution rate
  - Safe number of IDs to run
  - Projected average score at epoch end
- 🖼 Progress bars, colored rankings, and status indicators
---

## 🛠 Requirements

- Python 3.8+
- Install dependencies:

```bash
pip install requests rich colorama
```

---

## ⚙️ Configuration

At the top of the script, set your tracked identity IDs:

```python
YOUR_IDS = ['ID1', 'ID2', 'ID3']
```

---

## 💻 Usage

Run the script in your terminal:

```bash
python score_monitor.py
```

- Updates every 5 minutes
- Clears and redraws terminal output on each refresh
- Press `CTRL + C` to quit gracefully

---

## 📌 Notes

- Epochs reset weekly on **Wednesdays at 12:00 UTC**
- There are **676 available slots** for computors
- This is a **local terminal tool** and does not send data externally

---

## 🛑 Stopping

Use `CTRL + C` to gracefully exit. The screen will clear and the session will log the shutdown event.

---

## ⚠️ Disclaimer

This tool uses public guest access to `qubic.li` APIs. Use responsibly and always verify with official tools if planning actions based on the output.
