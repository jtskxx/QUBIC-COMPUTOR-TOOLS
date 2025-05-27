# Qubic QUS Auto Payout Tool

This Python script automates QUS payouts on the [Qubic](https://qubic.org) network. It reads address/amount data (pasted or from Excel), submits transactions using the `qubic-cli`, waits for tick confirmations, verifies transaction status, and optionally retries failures.

---

## Features

- ✅ Schedule transactions `TICK_ADVANCE` ticks ahead
- ✅ Confirm tick before and after sending
- ✅ Verifies each transaction hash on the specified tick
- ✅ Logs every transaction and generates a final report
- ✅ Retries failed transactions
- ✅ Supports pasting data or reading from Excel

---

## Requirements

- Python 3.8+
- Dependencies (install with pip):

```bash
pip install pandas requests psutil openpyxl
```

- Qubic CLI binary (place in the configured path)

---

## Configuration

Edit the script constants:
```python
QUBIC_CLI_PATH = "C:/Users/user/Desktop/qubic-cli/"
DEFAULT_SEED = "YOUR_WALLET_SEED"
DEFAULT_ADDRESS = "YOUR_WALLET_ADDRESS"
TICK_ADVANCE = 20
NODES = ["NODE1", "NODE2", "NODE3", "NODE4"]
```

---

## How to Use

### 1. Run the script

```bash
python auto_payout.py
```

### 2. Choose wallet input

- Use default hardcoded wallet, or
- Load seed/address from file (first two lines).

### 3. Choose input method

- Paste addresses and amounts (`Amount WalletAddress` per line), or
- Load from Excel with columns `amount`, `wallet_address`.

### 4. Confirm transactions

- Displays each planned transaction
- Prompts before starting

### 5. Script runs transaction loop:

- Gets current tick
- Waits for target tick
- Sends and verifies each transaction
- Generates logs and reports
- Optionally retries failures

---

## Example Input Format (pasted):

```
36850869NESBZWPNYFGLECLJQVIETDICMYUCMXJKCIHCTRVPLAUEQPUAJMMLHZXFXIQJ...
15000000NESBZWPNYFGLECLJQVIETDICMYUCMXJKCIHCTRVPLAUEQPUAJMMLHZXFXIQJ...
```

---

## Output Files

- `qus_sender.log`: Full log output
- `transaction_report.txt`: Human-readable transaction summary
- `failed_transactions.json`: List of failed transactions (for retry)

---

## Notes

- The script ensures one-by-one sequential transaction processing to avoid tick collisions.
- Adjust `TICK_ADVANCE` based on network latency.

---

## Disclaimer

Use at your own risk. Always verify your data before sending transactions.
