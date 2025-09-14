import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import MetaTrader5 as mt5
import threading
import time
import json
import os
import math
import requests

# --- CONFIGURATION & GLOBAL VARIABLES ---
CONFIG_FILE = "mt5.json"
LOG_FILE = "bot_log.txt"
BOT_RUNNING = False
INITIAL_SLAVE_EQUITY = 0.0

# IMPORTANT: CHANGE THIS PATH TO YOUR MT5 INSTALLATION DIRECTORY
MT5_TERMINAL_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe" 

SYMBOL_MAPPING = {
    "XAUUSDm": ["XAUUSDm", "XAUUSD", "GOLD"],
    "XAUUSD": ["XAUUSD", "XAUUSDm", "GOLD"],
    "BTCUSDm": ["BTCUSD", "BTCUSDm"],
    "BTCUSD": ["BTCUSDm", "BTCUSD"]
}
HARD_IGNORED_SYMBOLS = []
DEFAULT_ORDER_DEVIATION_POINTS = 20
DEFAULT_CHECK_INTERVAL_SECONDS = 3
DEFAULT_BTCUSD_PRICE_DEVIATION_LIMIT_USD = 100.0
DEFAULT_PRICE_DEVIATION_FOR_OTHERS = 1.0

# --- THREAD-SAFE SHARED DATA FOR GUI UPDATES ---
shared_data = {"slave_equity": 0.0, "slave_profit": 0.0, "pnl_percent": 0.0, "open_positions": 0}
data_lock = threading.Lock()

# --- TKINTER VARIABLES ---
(profile_name_var, profile_combobox, all_config_profiles, gui_check_interval_var, 
 gui_xauusd_var, gui_btcusd_var, gui_btcusd_deviation_var, gui_custom_symbols, 
 listbox_custom_symbols_widget, entry_custom_symbol, entry_custom_symbol_deviation, 
 gui_stop_loss_percent_var, gui_take_profit_percent_var, gui_trailing_drawdown_percent_var, 
 gui_master_stop_loss_percent_var, gui_min_price_distance_var, 
 gui_telegram_bot_token_var, gui_telegram_chat_id_var, log_file_handler) = (None,) * 19
gui_slave_equity_var, gui_slave_profit_var, gui_pnl_percent_var, gui_open_positions_var = (None,) * 4

# --- UTILITY, CONFIG, AND MT5 COMMUNICATION FUNCTIONS ---
def send_telegram_message(message):
    bot_token = gui_telegram_bot_token_var.get().strip()
    chat_id = gui_telegram_chat_id_var.get().strip()
    if not bot_token or not chat_id: return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": f"*{message}*", "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except requests.exceptions.RequestException as e: print(f"Telegram Error: {e}")

def log_message(message, send_to_telegram=False):
    timestamped_message = f"{time.strftime('%H:%M:%S')} - {message}\n"
    if 'text_log' in globals() and text_log.winfo_exists():
        text_log.config(state=tk.NORMAL); text_log.insert(tk.END, timestamped_message); text_log.see(tk.END); text_log.config(state=tk.DISABLED)
    global log_file_handler
    if log_file_handler:
        try:
            log_file_handler.write(f"{time.strftime('%Y-%m-%d')} {timestamped_message}"); log_file_handler.flush()
        except Exception as e: print(f"Log Write Error: {e}")
    if send_to_telegram and BOT_RUNNING: send_telegram_message(message)

def get_active_copy_symbols():
    active_symbols = {}
    if gui_xauusd_var.get(): active_symbols.update({"XAUUSD": DEFAULT_PRICE_DEVIATION_FOR_OTHERS, "XAUUSDm": DEFAULT_PRICE_DEVIATION_FOR_OTHERS, "GOLD": DEFAULT_PRICE_DEVIATION_FOR_OTHERS})
    if gui_btcusd_var.get(): btc_dev = gui_btcusd_deviation_var.get(); active_symbols.update({"BTCUSD": btc_dev, "BTCUSDm": btc_dev})
    for item in gui_custom_symbols: active_symbols[item['symbol']] = item['deviation']
    final = active_symbols.copy()
    for master, slaves in SYMBOL_MAPPING.items():
        if master in active_symbols:
            for slave_sym in slaves:
                if slave_sym not in final: final[slave_sym] = active_symbols[master]
    return {s: d for s, d in final.items() if s not in HARD_IGNORED_SYMBOLS}

def add_custom_symbol_to_list():
    global gui_custom_symbols
    symbol = entry_custom_symbol.get().strip().upper()
    if not symbol: messagebox.showerror("Error", "Please enter a symbol name."); return
    if any(item['symbol'] == symbol for item in gui_custom_symbols): log_message(f"Warning: Symbol '{symbol}' already exists."); return
    gui_custom_symbols.append({'symbol': symbol, 'deviation': 1.0}); update_custom_symbols_listbox()

def remove_custom_symbol_from_list():
    indices = listbox_custom_symbols_widget.curselection()
    if not indices: messagebox.showinfo("Info", "Please select a symbol to remove."); return
    for index in sorted(indices, reverse=True):
        removed = gui_custom_symbols.pop(index); log_message(f"Removed symbol: {removed['symbol']}")
    update_custom_symbols_listbox()

def update_custom_symbols_listbox():
    listbox_custom_symbols_widget.delete(0, tk.END)
    for item in gui_custom_symbols: listbox_custom_symbols_widget.insert(tk.END, f"{item['symbol']} - Dev: {item['deviation']:.2f}")

def load_all_configs():
    global all_config_profiles
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: all_config_profiles = json.load(f)
            if not isinstance(all_config_profiles, list): all_config_profiles = []
        except: all_config_profiles = []
    else: all_config_profiles = []
    update_profile_combobox()
    if all_config_profiles: load_profile_to_gui(profile_combobox.get())
    else: log_message("No profiles found.")

def update_profile_combobox(selected_name=None):
    names = [p.get('profile_name', 'Unnamed') for p in all_config_profiles]
    profile_combobox['values'] = names
    if names: profile_combobox.set(selected_name if selected_name in names else names[0])
    else: profile_combobox.set("")

def clear_gui_fields():
    entry_master_login.delete(0, tk.END); entry_master_password.delete(0, tk.END); entry_master_server.delete(0, tk.END)
    entry_slave_login.delete(0, tk.END); entry_slave_password.delete(0, tk.END); entry_slave_server.delete(0, tk.END)
    gui_check_interval_var.set(DEFAULT_CHECK_INTERVAL_SECONDS)
    gui_xauusd_var.set(True); gui_btcusd_var.set(True)
    gui_btcusd_deviation_var.set(DEFAULT_BTCUSD_PRICE_DEVIATION_LIMIT_USD)
    global gui_custom_symbols; gui_custom_symbols = []; update_custom_symbols_listbox()
    gui_stop_loss_percent_var.set(30.0); gui_take_profit_percent_var.set(30.0)
    gui_trailing_drawdown_percent_var.set(5.0); gui_master_stop_loss_percent_var.set(50.0)
    gui_min_price_distance_var.set(3.0)
    gui_telegram_bot_token_var.set(""); gui_telegram_chat_id_var.set("")
    profile_name_var.set("")

def load_profile_to_gui(profile_name):
    profile = next((p for p in all_config_profiles if p.get('profile_name') == profile_name), None)
    if not profile: return
    clear_gui_fields()
    profile_name_var.set(profile.get('profile_name', ''))
    entry_master_login.insert(0, profile.get('master_login', '')); entry_master_password.insert(0, profile.get('master_password', '')); entry_master_server.insert(0, profile.get('master_server', ''))
    entry_slave_login.insert(0, profile.get('slave_login', '')); entry_slave_password.insert(0, profile.get('slave_password', '')); entry_slave_server.insert(0, profile.get('slave_server', ''))
    gui_check_interval_var.set(profile.get('check_interval_seconds', DEFAULT_CHECK_INTERVAL_SECONDS))
    gui_xauusd_var.set(profile.get('xauusd_checked', True)); gui_btcusd_var.set(profile.get('btcusd_checked', False))
    gui_btcusd_deviation_var.set(profile.get('btcusd_deviation', DEFAULT_BTCUSD_PRICE_DEVIATION_LIMIT_USD))
    global gui_custom_symbols; gui_custom_symbols = profile.get('custom_symbols_list', []); update_custom_symbols_listbox()
    gui_stop_loss_percent_var.set(profile.get('stop_loss_percent', 30.0)); gui_take_profit_percent_var.set(profile.get('take_profit_percent', 100.0))
    gui_trailing_drawdown_percent_var.set(profile.get('trailing_drawdown_percent', 15.0)); gui_master_stop_loss_percent_var.set(profile.get('master_stop_loss_percent', 50.0))
    gui_min_price_distance_var.set(profile.get('min_price_distance', 3.0))
    gui_telegram_bot_token_var.set(profile.get('telegram_bot_token', '')); gui_telegram_chat_id_var.set(profile.get('telegram_chat_id', ''))
    log_message(f"Loaded profile '{profile_name}' into GUI.")

def save_current_profile_to_file():
    profile_name = profile_name_var.get().strip()
    if not profile_name: messagebox.showerror("Error", "Please enter a name for the profile."); return
    profile_data = {"profile_name": profile_name, "master_login": entry_master_login.get().strip(), "master_password": entry_master_password.get().strip(), "master_server": entry_master_server.get().strip(), "slave_login": entry_slave_login.get().strip(), "slave_password": entry_slave_password.get().strip(), "slave_server": entry_slave_server.get().strip(), "check_interval_seconds": gui_check_interval_var.get(), "xauusd_checked": gui_xauusd_var.get(), "btcusd_checked": gui_btcusd_var.get(), "btcusd_deviation": gui_btcusd_deviation_var.get(), "custom_symbols_list": gui_custom_symbols, "stop_loss_percent": gui_stop_loss_percent_var.get(), "take_profit_percent": gui_take_profit_percent_var.get(), "trailing_drawdown_percent": gui_trailing_drawdown_percent_var.get(), "master_stop_loss_percent": gui_master_stop_loss_percent_var.get(), "min_price_distance": gui_min_price_distance_var.get(), "telegram_bot_token": gui_telegram_bot_token_var.get().strip(), "telegram_chat_id": gui_telegram_chat_id_var.get().strip()}
    found_index = next((i for i, p in enumerate(all_config_profiles) if p.get("profile_name") == profile_name), -1)
    if found_index != -1: all_config_profiles[found_index] = profile_data
    else: all_config_profiles.append(profile_data)
    save_all_configs(); update_profile_combobox(selected_name=profile_name)

def save_all_configs():
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(all_config_profiles, f, indent=4)
        log_message("All profiles saved to file.")
    except Exception as e: log_message(f"Error saving config file: {e}")

def delete_selected_profile():
    profile_to_delete = profile_combobox.get()
    if not profile_to_delete: messagebox.showerror("Error", "Please select a profile to delete."); return
    if messagebox.askyesno("Confirm", f"Are you sure you want to delete '{profile_to_delete}'?"):
        global all_config_profiles; all_config_profiles = [p for p in all_config_profiles if p.get('profile_name') != profile_to_delete]
        save_all_configs(); update_profile_combobox()
        if all_config_profiles: load_profile_to_gui(profile_combobox.get())
        else: clear_gui_fields()
        log_message(f"Deleted profile '{profile_to_delete}'.")

def get_mt5_instance(login, password, server):
    if not os.path.exists(MT5_TERMINAL_PATH):
        log_message(f"Error: Invalid MT5 TERMINAL path: {MT5_TERMINAL_PATH}", True); return None
    if not mt5.initialize(path=MT5_TERMINAL_PATH, login=int(login), password=password, server=server, timeout=10000):
        log_message(f"MT5 initialization failed for account {login}: {mt5.last_error()}", True); return None
    return mt5

def get_position_from_deal(mt5_instance, deal_id):
    try:
        deal = mt5_instance.history_deals_get(ticket=deal_id)
        if deal and len(deal) > 0: return deal[0].position_id
    except Exception as e: log_message(f"Error getting position from deal {deal_id}: {e}"); return None

def find_slave_target_symbol(master_symbol, mt5_slave, active_symbols):
    potential_symbols = SYMBOL_MAPPING.get(master_symbol, [master_symbol])
    for symbol in potential_symbols:
        if symbol in active_symbols and mt5_slave.symbol_info(symbol): return symbol
    return None

def calculate_lot_size(symbol_info, master_volume, master_equity, slave_equity):
    if master_equity <= 0 or slave_equity <= 0: return 0.0
    ratio = slave_equity / master_equity; calculated_lot = master_volume * ratio
    if symbol_info:
        min_step = symbol_info.volume_step; min_vol = symbol_info.volume_min
        if min_step > 0: calculated_lot = math.floor(calculated_lot / min_step) * min_step
        return max(min_vol, round(calculated_lot, 2))
    return max(0.01, round(calculated_lot, 2))

# --- TRADE PROCESSING FUNCTIONS ---
def process_closed_trades(mt5_slave, closed_tickets, master_to_slave_tickets, slave_positions):
    for ticket in closed_tickets:
        slave_ticket = master_to_slave_tickets.pop(ticket, None)
        if slave_ticket:
            pos_to_close = next((p for p in slave_positions if p.ticket == slave_ticket), None)
            if pos_to_close:
                log_message(f"Master ticket {ticket} closed. Closing corresponding Slave ticket {slave_ticket}...")
                tick = mt5_slave.symbol_info_tick(pos_to_close.symbol)
                if not tick: continue
                price = tick.bid if pos_to_close.type == mt5.ORDER_TYPE_BUY else tick.ask
                request = {"action": mt5.TRADE_ACTION_DEAL, "position": pos_to_close.ticket, "symbol": pos_to_close.symbol, "volume": pos_to_close.volume, "type": mt5.ORDER_TYPE_SELL if pos_to_close.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY, "price": price, "deviation": DEFAULT_ORDER_DEVIATION_POINTS, "magic": 202408, "comment": "Bot Close"}
                result = mt5_slave.order_send(request)
                if not (result and result.retcode == mt5.TRADE_RETCODE_DONE): log_message(f"Failed to close Slave ticket {slave_ticket}: {result.comment if result else 'N/A'}", True)

def process_new_trades(mt5_slave, new_tickets, master_positions, slave_positions, master_equity, slave_equity, active_symbols, master_to_slave_tickets, last_copied_prices):
    num_master_pos, num_slave_pos = len(master_positions), len(slave_positions)
    for ticket in new_tickets:
        if num_slave_pos >= num_master_pos:
            log_message(f"POSITION LIMIT: Slave ({num_slave_pos}) >= Master ({num_master_pos}). Pausing copy.", False); break
        master_pos = master_positions[ticket]
        target_symbol = find_slave_target_symbol(master_pos.symbol, mt5_slave, active_symbols)
        if not target_symbol: continue
        min_price_distance = gui_min_price_distance_var.get()
        last_price = last_copied_prices.get(target_symbol)
        if last_price is not None and abs(master_pos.price_open - last_price) < min_price_distance:
            log_message(f"SKIPPING (TOO CLOSE): {target_symbol} | Distance: {abs(master_pos.price_open - last_price):.2f} < {min_price_distance:.2f}"); continue
        symbol_info = mt5_slave.symbol_info(target_symbol)
        lot_to_copy = calculate_lot_size(symbol_info, master_pos.volume, master_equity, slave_equity)
        max_vol_step = symbol_info.volume_step if symbol_info and symbol_info.volume_step > 0 else 0.01
        max_volume_allowed = math.floor(((slave_equity / 100) * 0.05) / max_vol_step) * max_vol_step
        if lot_to_copy > max_volume_allowed:
            log_message(f"CAPITAL MANAGEMENT: Lot {lot_to_copy:.2f} > limit {max_volume_allowed:.2f}. Adjusting.", True); lot_to_copy = max_volume_allowed
        if lot_to_copy <= 0: continue
        tick = mt5_slave.symbol_info_tick(target_symbol)
        if not tick: continue
        price = tick.ask if master_pos.type == mt5.POSITION_TYPE_BUY else tick.bid
        request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": target_symbol, "volume": lot_to_copy, "type": mt5.ORDER_TYPE_BUY if master_pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_SELL, "price": price, "sl": master_pos.sl, "tp": master_pos.tp, "deviation": DEFAULT_ORDER_DEVIATION_POINTS, "magic": 202408, "comment": "CopyTrade", "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC}
        result = mt5_slave.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE and result.deal > 0:
            position_id = get_position_from_deal(mt5_slave, result.deal)
            if position_id:
                master_to_slave_tickets[ticket] = position_id
                last_copied_prices[target_symbol] = master_pos.price_open
                log_message(f"Copy successful: {target_symbol} {lot_to_copy:.2f} lots. Master:{ticket} -> Slave:{position_id}", True); num_slave_pos += 1
        else:
            log_message(f"Copy failed: {result.comment if result else 'N/A'}", True)

def synchronize_sl_tp(mt5_slave, master_positions, slave_positions, master_to_slave_tickets):
    slave_pos_dict = {p.ticket: p for p in slave_positions}
    for master_ticket, slave_ticket in master_to_slave_tickets.items():
        master_pos = master_positions.get(master_ticket)
        slave_pos = slave_pos_dict.get(slave_ticket)
        if master_pos and slave_pos and (abs(master_pos.sl - slave_pos.sl) > 1e-5 or abs(master_pos.tp - slave_pos.tp) > 1e-5):
            log_message(f"SL/TP change detected for Master {master_ticket}. Updating Slave {slave_ticket}.")
            request = {"action": mt5.TRADE_ACTION_MODIFY, "position": slave_ticket, "sl": master_pos.sl, "tp": master_pos.tp}
            mt5_slave.order_send(request)

# --- MAIN TRADING THREAD ---
def trading_thread_function(master_login, master_password, master_server, slave_login, slave_password, slave_server):
    global BOT_RUNNING, INITIAL_SLAVE_EQUITY
    log_message("Trading thread started.")
    master_to_slave_tickets, last_copied_prices = {}, {}
    last_master_positions_snapshot = {}
    mt5_slave_init = get_mt5_instance(slave_login, slave_password, slave_server)
    if not mt5_slave_init:
        log_message("Failed to connect to Slave on initialization. Stopping bot.", True); stop_bot_gui(); return
    INITIAL_SLAVE_EQUITY = mt5_slave_init.account_info().equity
    log_message(f"Initial Slave Equity: {INITIAL_SLAVE_EQUITY:.2f}")
    initial_slave_positions = mt5_slave_init.positions_get() or []
    if initial_slave_positions:
        log_message("Initializing price reference for order spacing...")
        symbols = {p.symbol for p in initial_slave_positions}
        for symbol in symbols:
            most_recent = max((p for p in initial_slave_positions if p.symbol == symbol), key=lambda p: p.time_msc)
            last_copied_prices[symbol] = most_recent.price_open
            log_message(f" -> {symbol}: Reference price set to {most_recent.price_open}")
    mt5_slave_init.shutdown()

    while BOT_RUNNING:
        try:
            mt5_master = get_mt5_instance(master_login, master_password, master_server)
            if not mt5_master: time.sleep(10); continue
            master_equity = mt5_master.account_info().equity
            current_master_positions_list = mt5_master.positions_get() or []
            current_master_positions_snapshot = {p.ticket: p for p in current_master_positions_list}
            has_changed = False
            if set(current_master_positions_snapshot.keys()) != set(last_master_positions_snapshot.keys()):
                has_changed = True; log_message("Change detected (Open/Close) on Master.")
            else:
                for ticket, current_pos in current_master_positions_snapshot.items():
                    last_pos = last_master_positions_snapshot.get(ticket)
                    if last_pos and (current_pos.sl != last_pos.sl or current_pos.tp != last_pos.tp):
                        has_changed = True; log_message("Change detected (SL/TP) on Master."); break
            mt5_master.shutdown()

            if has_changed:
                log_message("Starting synchronization with Slave...")
                mt5_slave = get_mt5_instance(slave_login, slave_password, slave_server)
                if not mt5_slave: time.sleep(10); continue
                acc_info = mt5_slave.account_info(); slave_equity, slave_profit = acc_info.equity, acc_info.profit
                slave_positions = mt5_slave.positions_get() or []
                pnl_percent = ((slave_equity - INITIAL_SLAVE_EQUITY) / INITIAL_SLAVE_EQUITY) * 100 if INITIAL_SLAVE_EQUITY > 0 else 0
                with data_lock:
                    shared_data.update({"slave_equity": slave_equity, "slave_profit": slave_profit, "pnl_percent": pnl_percent, "open_positions": len(slave_positions)})
                if INITIAL_SLAVE_EQUITY > 0:
                    stop_loss, take_profit = -abs(gui_stop_loss_percent_var.get()), abs(gui_take_profit_percent_var.get())
                    if pnl_percent <= stop_loss or pnl_percent >= take_profit:
                        log_message(f"GLOBAL P/L LIMIT REACHED ({pnl_percent:.2f}%). Closing all positions and stopping bot.", True)
                        for pos in slave_positions:
                            tick = mt5_slave.symbol_info_tick(pos.symbol); price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
                            request = {"action": mt5.TRADE_ACTION_DEAL, "position": pos.ticket, "symbol": pos.symbol, "volume": pos.volume, "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY, "price": price}
                            mt5_slave.order_send(request)
                        BOT_RUNNING = False
                if not BOT_RUNNING: mt5_slave.shutdown(); stop_bot_gui(); break
                if len(current_master_positions_snapshot) == 0 and len(slave_positions) > 0:
                    log_message("Master has no open positions. Closing all positions on Slave to sync...", True)
                    for pos in slave_positions:
                        tick = mt5_slave.symbol_info_tick(pos.symbol); price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
                        request = {"action": mt5.TRADE_ACTION_DEAL, "position": pos.ticket, "symbol": pos.symbol, "volume": pos.volume, "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY, "price": price, "comment": "Sync Close All"}
                        mt5_slave.order_send(request)
                    master_to_slave_tickets.clear(); last_copied_prices.clear()
                else:
                    active_symbols = get_active_copy_symbols()
                    closed_tickets = set(last_master_positions_snapshot.keys()) - set(current_master_positions_snapshot.keys())
                    new_tickets = set(current_master_positions_snapshot.keys()) - set(last_master_positions_snapshot.keys())
                    process_closed_trades(mt5_slave, closed_tickets, master_to_slave_tickets, slave_positions)
                    slave_positions_after_close = mt5_slave.positions_get() or []
                    process_new_trades(mt5_slave, new_tickets, current_master_positions_snapshot, slave_positions_after_close, master_equity, slave_equity, active_symbols, master_to_slave_tickets, last_copied_prices)
                    final_slave_positions = mt5_slave.positions_get() or []
                    synchronize_sl_tp(mt5_slave, current_master_positions_snapshot, final_slave_positions, master_to_slave_tickets)
                    open_slave_symbols = {p.symbol for p in final_slave_positions}
                    for symbol in list(last_copied_prices.keys()):
                        if symbol not in open_slave_symbols:
                            del last_copied_prices[symbol]; log_message(f"Cleared price reference for {symbol} as there are no open positions.", False)
                mt5_slave.shutdown()
            else:
                log_message("No changes on Master.", False)
            last_master_positions_snapshot = current_master_positions_snapshot
            time.sleep(gui_check_interval_var.get())
        except Exception as e:
            log_message(f"Critical error in main thread: {e}", True)
            if 'mt5_master' in locals() and mt5_master: mt5_master.shutdown()
            if 'mt5_slave' in locals() and mt5_slave: mt5_slave.shutdown()
            time.sleep(10)
    log_message("Trading thread stopped.")

# --- GUI FUNCTIONS ---
def update_gui_dashboard():
    if BOT_RUNNING:
        with data_lock:
            gui_slave_equity_var.set(f"{shared_data['slave_equity']:.2f} USD"); gui_slave_profit_var.set(f"{shared_data['slave_profit']:.2f} USD")
            gui_pnl_percent_var.set(f"{shared_data['pnl_percent']:.2f} %"); gui_open_positions_var.set(str(shared_data['open_positions']))
    root.after(1000, update_gui_dashboard)

def start_bot_gui():
    global BOT_RUNNING, log_file_handler
    if BOT_RUNNING: messagebox.showinfo("Info", "Bot is already running."); return
    try: log_file_handler = open(LOG_FILE, 'a', encoding='utf-8')
    except Exception as e: messagebox.showerror("Error", f"Could not open log file: {e}")
    if not all([entry_master_login.get(), entry_master_password.get(), entry_master_server.get(), entry_slave_login.get(), entry_slave_password.get(), entry_slave_server.get()]):
        messagebox.showerror("Error", "Please fill in all account details."); return
    save_current_profile_to_file()
    BOT_RUNNING = True
    thread_args = (entry_master_login.get().strip(), entry_master_password.get().strip(), entry_master_server.get().strip(), entry_slave_login.get().strip(), entry_slave_password.get().strip(), entry_slave_server.get().strip())
    trading_thread = threading.Thread(target=trading_thread_function, args=thread_args, daemon=True); trading_thread.start()
    btn_start.config(state=tk.DISABLED); btn_stop.config(state=tk.NORMAL)
    for w in [btn_save_profile, btn_delete_profile, profile_combobox]: w.config(state='disabled')

def stop_bot_gui():
    global BOT_RUNNING, log_file_handler
    if not BOT_RUNNING: return
    log_message("Stopping bot...", True); BOT_RUNNING = False
    btn_start.config(state=tk.NORMAL); btn_stop.config(state=tk.DISABLED)
    for w in [btn_save_profile, btn_delete_profile]: w.config(state='normal')
    profile_combobox.config(state='readonly')
    if log_file_handler: log_file_handler.close(); log_file_handler = None

def on_closing():
    if BOT_RUNNING and messagebox.askyesno("Exit", "The bot is running. Do you want to stop the bot and exit?"):
        stop_bot_gui(); root.destroy()
    elif not BOT_RUNNING: root.destroy()

# --- MAIN GUI SETUP ---
if __name__ == "__main__":
    root = tk.Tk(); root.title("MT5 Copy Trading Bot"); root.geometry("1200x820"); root.resizable(False, False)
    root.protocol("WM_DELETE_WINDOW", on_closing)
    tk.Label(root, text="Status Log:").pack(padx=10, pady=5, anchor=tk.W)
    text_log = scrolledtext.ScrolledText(root, width=140, height=15, state=tk.DISABLED, wrap=tk.WORD, font=("Consolas", 9)); text_log.pack(padx=10, pady=5, fill=tk.BOTH, expand=False)
    main_frame = tk.Frame(root); main_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
    left_frame = tk.Frame(main_frame); left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
    right_frame = tk.Frame(main_frame); right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
    dashboard_frame = tk.LabelFrame(left_frame, text="Real-time Dashboard (Slave Account)", padx=10, pady=5); dashboard_frame.pack(padx=5, pady=5, fill=tk.X, anchor=tk.N)
    gui_slave_equity_var, gui_slave_profit_var, gui_pnl_percent_var, gui_open_positions_var = (tk.StringVar(value="0.00 USD"), tk.StringVar(value="0.00 USD"), tk.StringVar(value="0.00 %"), tk.StringVar(value="0"))
    tk.Label(dashboard_frame, text="Current Equity:").grid(row=0, column=0, sticky=tk.W); tk.Label(dashboard_frame, textvariable=gui_slave_equity_var, font=("Arial", 10, "bold")).grid(row=0, column=1, sticky=tk.W)
    tk.Label(dashboard_frame, text="Floating P/L:").grid(row=1, column=0, sticky=tk.W); tk.Label(dashboard_frame, textvariable=gui_slave_profit_var, font=("Arial", 10, "bold")).grid(row=1, column=1, sticky=tk.W)
    tk.Label(dashboard_frame, text="P/L (%):").grid(row=0, column=2, sticky=tk.W, padx=20); tk.Label(dashboard_frame, textvariable=gui_pnl_percent_var, font=("Arial", 10, "bold")).grid(row=0, column=3, sticky=tk.W)
    tk.Label(dashboard_frame, text="Open Positions:").grid(row=1, column=2, sticky=tk.W, padx=20); tk.Label(dashboard_frame, textvariable=gui_open_positions_var, font=("Arial", 10, "bold")).grid(row=1, column=3, sticky=tk.W)
    profile_frame = tk.LabelFrame(left_frame, text="Profile Management", padx=10, pady=5); profile_frame.pack(padx=5, pady=5, fill=tk.X)
    tk.Label(profile_frame, text="Profile Name:").grid(row=0, column=0, sticky=tk.W); profile_name_var = tk.StringVar(); entry_profile_name = tk.Entry(profile_frame, textvariable=profile_name_var, width=30); entry_profile_name.grid(row=0, column=1)
    btn_save_profile = tk.Button(profile_frame, text="Save", command=save_current_profile_to_file); btn_save_profile.grid(row=0, column=2, padx=5)
    tk.Label(profile_frame, text="Select Profile:").grid(row=1, column=0, sticky=tk.W); profile_combobox = ttk.Combobox(profile_frame, width=28, state="readonly"); profile_combobox.grid(row=1, column=1)
    profile_combobox.bind("<<ComboboxSelected>>", lambda e: load_profile_to_gui(profile_combobox.get()))
    btn_delete_profile = tk.Button(profile_frame, text="Delete", command=delete_selected_profile); btn_delete_profile.grid(row=1, column=2, padx=5)
    master_frame = tk.LabelFrame(left_frame, text="Master Account", padx=10, pady=5); master_frame.pack(padx=5, pady=5, fill=tk.X)
    tk.Label(master_frame, text="Login:").grid(row=0, column=0, sticky=tk.W); entry_master_login = tk.Entry(master_frame, width=40); entry_master_login.grid(row=0, column=1)
    tk.Label(master_frame, text="Password:").grid(row=1, column=0, sticky=tk.W); entry_master_password = tk.Entry(master_frame, width=40, show="*"); entry_master_password.grid(row=1, column=1)
    tk.Label(master_frame, text="Server:").grid(row=2, column=0, sticky=tk.W); entry_master_server = tk.Entry(master_frame, width=40); entry_master_server.grid(row=2, column=1)
    slave_frame = tk.LabelFrame(left_frame, text="Slave Account", padx=10, pady=5); slave_frame.pack(padx=5, pady=5, fill=tk.X)
    tk.Label(slave_frame, text="Login:").grid(row=0, column=0, sticky=tk.W); entry_slave_login = tk.Entry(slave_frame, width=40); entry_slave_login.grid(row=0, column=1)
    tk.Label(slave_frame, text="Password:").grid(row=1, column=0, sticky=tk.W); entry_slave_password = tk.Entry(slave_frame, width=40, show="*"); entry_slave_password.grid(row=1, column=1)
    tk.Label(slave_frame, text="Server:").grid(row=2, column=0, sticky=tk.W); entry_slave_server = tk.Entry(slave_frame, width=40); entry_slave_server.grid(row=2, column=1)
    general_frame = tk.LabelFrame(right_frame, text="General Settings & Telegram", padx=10, pady=5); general_frame.pack(padx=5, pady=5, fill=tk.X)
    tk.Label(general_frame, text="Check Interval (s):").grid(row=0, column=0, sticky=tk.W); gui_check_interval_var = tk.DoubleVar(value=DEFAULT_CHECK_INTERVAL_SECONDS); tk.Entry(general_frame, textvariable=gui_check_interval_var, width=10).grid(row=0, column=1, sticky=tk.W)
    tk.Label(general_frame, text="Telegram Bot Token:").grid(row=1, column=0, sticky=tk.W); gui_telegram_bot_token_var = tk.StringVar(); tk.Entry(general_frame, textvariable=gui_telegram_bot_token_var, width=40, show="*").grid(row=1, column=1, columnspan=3, sticky=tk.W)
    tk.Label(general_frame, text="Telegram Chat ID:").grid(row=2, column=0, sticky=tk.W); gui_telegram_chat_id_var = tk.StringVar(); tk.Entry(general_frame, textvariable=gui_telegram_chat_id_var, width=40).grid(row=2, column=1, columnspan=3, sticky=tk.W)
    symbols_frame = tk.LabelFrame(right_frame, text="Symbol Configuration", padx=10, pady=5); symbols_frame.pack(padx=5, pady=5, fill=tk.X)
    gui_xauusd_var = tk.BooleanVar(value=True); tk.Checkbutton(symbols_frame, text="XAUUSD/GOLD", variable=gui_xauusd_var).grid(row=0, column=0, sticky=tk.W)
    gui_btcusd_var = tk.BooleanVar(value=True); tk.Checkbutton(symbols_frame, text="BTCUSD", variable=gui_btcusd_var).grid(row=0, column=1, sticky=tk.W, padx=10)
    tk.Label(symbols_frame, text="BTCUSD Deviation:").grid(row=0, column=2, sticky=tk.W); gui_btcusd_deviation_var = tk.DoubleVar(value=DEFAULT_BTCUSD_PRICE_DEVIATION_LIMIT_USD); tk.Entry(symbols_frame, textvariable=gui_btcusd_deviation_var, width=10).grid(row=0, column=3, sticky=tk.W)
    tk.Label(symbols_frame, text="Custom Symbol:").grid(row=1, column=0, sticky=tk.W); entry_custom_symbol = tk.Entry(symbols_frame, width=15); entry_custom_symbol.grid(row=1, column=1, sticky=tk.W)
    tk.Label(symbols_frame, text="Deviation:").grid(row=1, column=2, sticky=tk.W); entry_custom_symbol_deviation = tk.Entry(symbols_frame, width=10); entry_custom_symbol_deviation.grid(row=1, column=3, sticky=tk.W)
    tk.Button(symbols_frame, text="Add", command=add_custom_symbol_to_list).grid(row=1, column=4, padx=5)
    listbox_custom_symbols_widget = tk.Listbox(symbols_frame, height=3, width=60); listbox_custom_symbols_widget.grid(row=2, column=0, columnspan=4, sticky='ew')
    tk.Button(symbols_frame, text="Remove", command=remove_custom_symbol_from_list).grid(row=2, column=4, padx=5)
    risk_frame = tk.LabelFrame(right_frame, text="Risk Management", padx=10, pady=5); risk_frame.pack(padx=5, pady=5, fill=tk.X)
    tk.Label(risk_frame, text="Stop Loss (%):").grid(row=0, column=0, sticky=tk.W); gui_stop_loss_percent_var = tk.DoubleVar(value=30.0); tk.Entry(risk_frame, textvariable=gui_stop_loss_percent_var, width=10).grid(row=0, column=1, sticky=tk.W)
    tk.Label(risk_frame, text="Take Profit (%):").grid(row=1, column=0, sticky=tk.W); gui_take_profit_percent_var = tk.DoubleVar(value=30.0); tk.Entry(risk_frame, textvariable=gui_take_profit_percent_var, width=10).grid(row=1, column=1, sticky=tk.W)
    tk.Label(risk_frame, text="Trailing Drawdown (%):").grid(row=2, column=0, sticky=tk.W); gui_trailing_drawdown_percent_var = tk.DoubleVar(value=5.0); tk.Entry(risk_frame, textvariable=gui_trailing_drawdown_percent_var, width=10).grid(row=2, column=1, sticky=tk.W)
    tk.Label(risk_frame, text="Master Stop Loss (%):").grid(row=3, column=0, sticky=tk.W); gui_master_stop_loss_percent_var = tk.DoubleVar(value=50.0); tk.Entry(risk_frame, textvariable=gui_master_stop_loss_percent_var, width=10).grid(row=3, column=1, sticky=tk.W)
    tk.Label(risk_frame, text="Min. Price Distance (USD):").grid(row=4, column=0, sticky=tk.W); gui_min_price_distance_var = tk.DoubleVar(value=3.0); tk.Entry(risk_frame, textvariable=gui_min_price_distance_var, width=10).grid(row=4, column=1, sticky=tk.W)
    controls_frame = tk.Frame(root, pady=10); controls_frame.pack(fill=tk.X, padx=10, side=tk.BOTTOM)
    btn_start = tk.Button(controls_frame, text="Start Bot", command=start_bot_gui, width=15, height=2, bg="#4CAF50", fg="white", font=("Arial", 10, "bold")); btn_start.pack(side=tk.LEFT, padx=5, expand=True)
    btn_stop = tk.Button(controls_frame, text="Stop Bot", command=stop_bot_gui, width=15, height=2, bg="#F44336", fg="white", font=("Arial", 10, "bold")); btn_stop.pack(side=tk.LEFT, padx=5, expand=True); btn_stop.config(state=tk.DISABLED)
    load_all_configs()
    update_gui_dashboard()
    root.mainloop()
