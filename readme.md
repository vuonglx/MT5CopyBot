# Advanced MT5 Copy Trading Bot

This is a powerful, automated copy trading tool for MetaTrader 5, developed in Python. It is designed to efficiently and accurately replicate trades from a master account to a slave account, incorporating a multi-layered, robust risk management system.

The bot features an intuitive Graphical User Interface (GUI) built with Tkinter, allowing users to easily configure, monitor, and control all operations without needing to modify the source code directly.



## ✨ Key Features

### GUI & Monitoring
* **Intuitive Interface:** Easily set up and manage all parameters from a single window.
* **Real-time Dashboard:** Monitor the slave account's live Equity, floating P/L (in $ and %), and the total number of open positions directly on the GUI.
* **Profile Management:** Quickly save and switch between different master-slave account configurations using a `mt5.json` file.
* **Telegram Notifications:** Get instant alerts for critical events and status updates.
* **Detailed Logging:** All activities are logged to a `bot_log.txt` file for easy tracking and debugging.

### Smart & Optimized Copying
* **Efficient Sync Mechanism:** The bot primarily monitors the master account and only connects to the slave account when a change (open, close, or modify trade) is detected. This significantly reduces latency and system load.
* **Proportional Lot Sizing:** Automatically calculates trade volume for the slave account based on the equity ratio, ensuring consistent risk management.
* **Accurate Trade Mapping:** Uses the `deal_id` returned after a trade is executed to retrieve the exact `position_id`, eliminating the risk of mapping to the wrong trade.
* **SL/TP Synchronization:** Automatically updates Stop Loss and Take Profit on slave positions if they are modified on the master account.
* **Flexible Symbol Mapping:** Easily copy trades between brokers that use different instrument names (e.g., `XAUUSD` on one broker and `GOLD` on another).

### Comprehensive Risk Management 🛡️
1.  **Global P/L Stop:** Automatically closes all positions and stops the bot if the slave account's total profit or loss reaches a predefined percentage of the initial equity.
2.  **Max Volume Cap:** Controls risk on every single trade by capping the maximum lot size based on a rule (e.g., max 0.05 lots per $100 of equity).
3.  **Order Spacing Filter:** Prevents over-trading by ignoring new master trades if their entry price is too close to the last copied trade on the same symbol.
4.  **Position Count Limit:** Ensures the number of open positions on your account never exceeds the number of positions on the master account.
5.  **"Master Flat" Failsafe:** As a final layer of protection, if the master account has zero open positions, the bot will automatically close any and all remaining positions on the slave account to ensure a perfect sync.

## Requirements
1.  **Python 3.9+** installed.
2.  **MetaTrader 5 Desktop Terminal** installed and running.
3.  The necessary Python libraries.

## 🚀 Installation & Usage Guide

### Step 1: Install Required Libraries
Open a Command Prompt (CMD) or Terminal in the bot's directory and run this single command to install all dependencies:
```bash
pip install -r requirements.txt
````

### Step 2: **CRITICAL** - Configure MT5 Path

Open the bot's Python file (`.py`) with a code editor (like VS Code, Notepad++, etc.). Find and **change the path** in the following line to point to your `terminal64.exe` or `terminal.exe` file:

```python
MT5_TERMINAL_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe" 
```

### Step 3: Run the Bot

Save the file and run the bot from your terminal:

```bash
python your_bot_file_name.py
```

### Step 4: Using the Interface

1.  **Fill in Details:** Enter the Login, Password, and Server for both the Master and Slave accounts.
2.  **Create a Profile:** Give your configuration a name (e.g., "My Main Copy Setup") and click **Save**.
3.  **Customize Risk:** Adjust the parameters in the "Risk Management" panel to your preference.
4.  **Start Trading:** Click the **"Start Bot"** button. The status log will begin updating, and the dashboard will display live account data.

## ⚠️ Important Disclaimer

  * The MetaTrader 5 desktop software **must be running** on the same machine for the bot to connect.
  * Always **test thoroughly on a demo account** before using on a live account.
  * This tool is provided as-is. You are solely responsible for your own trading decisions and any potential financial losses.
