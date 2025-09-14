**Request:** Create a Python-based MetaTrader 5 (MT5) copy trading bot with the following detailed specifications:

 **1. Technology & GUI:**
 * Use the `tkinter` library for the Graphical User Interface.
 * Use the `MetaTrader5` library for all trading connections and actions.
 * Use the `requests` library for Telegram notifications.

 **2. Graphical User Interface (GUI) Features:**
 * **Real-time Dashboard:** Display the Slave account's live Equity, floating P/L ($ and %), and total number of open positions.
 * **Profile Management:** Allow users to create, save, load, and delete trading profiles from a `mt5.json` file.
 * **Account Details:** Input fields for Login, Password, and Server for both Master and Slave accounts.
 * **Symbol Configuration:** Checkboxes to enable/disable major pairs (e.g., XAUUSD, BTCUSD) and a section to add/remove custom symbols.
 * **Risk Management Panel:** Dedicated input fields for all risk parameters.

 **3. Core Logic & Optimization:**
 * **Optimized Sync Mechanism:** The bot should primarily monitor the Master account. It must only connect to the Slave account to execute actions *if and only if* a change (new trade, closed trade, or SL/TP modification) is detected on the Master. This is to minimize latency.
 * **Proportional Lot Sizing:** Automatically calculate the Slave's trade volume based on the equity ratio between the Master and Slave accounts.
* **Accurate Trade Mapping:** Upon a successful trade, use the returned `deal_id` to retrieve the exact `position_id` to ensure 100% accurate mapping between Master and Slave trades.
 * **SL/TP Synchronization:** Automatically update the Stop Loss and Take Profit on Slave positions if they are modified on the Master's corresponding position.
 * **Symbol Mapping:** Support mapping different symbol names between brokers (e.g., `XAUUSD` on Master to `GOLD` on Slave).

 **4. Advanced Risk Management Rules:**
 * **Global P/L Stop:** Automatically close all positions and stop the bot if the Slave account's total P/L reaches a user-defined percentage (for both profit and loss).
 * **Max Volume Cap:** Limit the volume of each copied trade based on a rule: a maximum of 0.05 lots for every $100 of the Slave account's equity.
 * **Order Spacing (Price Distance Filter):** Do not copy a new trade if its entry price is within a user-defined distance (e.g., $3.00) of the last copied trade on the same symbol. This mechanism must reset when there are no more open trades for that symbol.
 * **Position Count Limit:** Do not copy a new trade if the total number of open positions on the Slave account is already equal to or greater than the Master's.
 * **"Master Flat" Failsafe:** If the Master account has zero open positions, the bot must automatically close all remaining positions on the Slave account to ensure a perfect sync.

 **5. Auxiliary Features:**
 * Send critical event notifications via the Telegram Bot API.
 * Log all activities to a local `bot_log.txt` file.
