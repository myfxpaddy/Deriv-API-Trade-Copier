import json, time, threading, sys, traceback
from websocket import create_connection

# ===================== CONFIG FOR TRADER AND CLIENT =====================
APP_ID = 1089  # your own App ID
TRADER_ADMIN_TOKEN   = "G5RnGdX6Zc25tsv"    # trader token WITH 'admin' permission (REAL account)
TRADER_READONLY_TOKEN= "YvmZ3o4wydBnNF0" # trader read-only token (REAL account)
FOLLOWER_TOKENS = [
      "FIHEcx6sGC4jXhK",
    # "PUT_FOLLOWER_API_TOKEN_2_WITH_TRADE_PERMISSION",
]
DISABLE_ALLOW_COPIERS_ON_EXIT = False  # set True if you want to auto-turn it off when stopping
# ==============================================================

WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"

def ws_open():
    return create_connection(WS_URL, timeout=30)

def ws_recv_until(ws, want_msg_type=None):
    while True:
        msg = json.loads(ws.recv())
        if msg.get("error"):
            raise RuntimeError(msg["error"])
        if want_msg_type is None or msg.get("msg_type") == want_msg_type or want_msg_type in msg:
            return msg

def authorize(ws, token):
    ws.send(json.dumps({"authorize": token}))
    return ws_recv_until(ws, "authorize")["authorize"]

def call_with_token(token, payload, expect=None):
    ws = ws_open()
    try:
        authorize(ws, token)
        ws.send(json.dumps(payload))
        return ws_recv_until(ws, expect) if expect else ws_recv_until(ws)
    finally:
        ws.close()

def preflight_print(label, auth):
    print(f"{label}: loginid={auth.get('loginid')} type={'VIRTUAL' if auth.get('is_virtual') else 'REAL'} scopes={auth.get('scopes')}")

def get_settings_with(token):
    try:
        resp = call_with_token(token, {"get_settings": 1}, expect="get_settings")
        return resp.get("get_settings", {})
    except Exception as e:
        print("get_settings error:", e); return {}

def set_allow_copiers(token, value: bool):
    v = 1 if value else 0
    resp = call_with_token(token, {"set_settings": 1, "allow_copiers": v})
    print(f"allow_copiers set to {v}: OK")

def copy_start_for_follower(follower_token, trader_readonly_token):
    return call_with_token(follower_token, {"copy_start": trader_readonly_token})

def copy_stop_for_follower(follower_token, trader_readonly_token):
    return call_with_token(follower_token, {"copy_stop": trader_readonly_token})

def stream_trader_transactions(stop_event):
    ws = ws_open()
    try:
        authorize(ws, TRADER_READONLY_TOKEN)
        ws.send(json.dumps({"transactions": 1, "subscribe": 1}))
        print("→ Streaming trader transactions (buy/sell). Ctrl+C to stop...")
        while not stop_event.is_set():
            msg = json.loads(ws.recv())
            if msg.get("msg_type") == "transaction":
                t = msg["transaction"]
                action = t.get("action")
                symbol = t.get("symbol")
                ctype  = t.get("contract_type")
                buy_px = t.get("buy_price")
                amt    = t.get("amount")
                longcode = t.get("longcode")
                print(f"[{action}] {symbol} {ctype} stake={buy_px} Δ={amt} :: {longcode}")
    except Exception as e:
        print("transactions stream error:", e); traceback.print_exc()
    finally:
        try: ws.close()
        except: pass

# -------------------- RUN --------------------
print("Starting: Deriv Copy-Mirror (exact 1:1). Followers:", len(FOLLOWER_TOKENS))

try:
    ws = ws_open()
    trader_admin_auth = authorize(ws, TRADER_ADMIN_TOKEN)
    preflight_print("TRADER_ADMIN_TOKEN", trader_admin_auth)
    ws.close()
except Exception as e:
    print("ADMIN token auth failed (must be REAL account with 'admin' scope):", e); raise

try:
    ws = ws_open()
    trader_ro_auth = authorize(ws, TRADER_READONLY_TOKEN)
    preflight_print("TRADER_READONLY_TOKEN", trader_ro_auth)
    if trader_ro_auth.get("is_virtual"):
        print(" Trader read-only token is VIRTUAL; built-in copier requires REAL master.")
    ws.close()
except Exception as e:
    print("READ-ONLY token auth failed:", e); raise

for i, tok in enumerate(FOLLOWER_TOKENS, 1):
    try:
        ws = ws_open()
        auth = authorize(ws, tok)
        preflight_print(f"FOLLOWER[{i}]", auth)
        if "trade" not in (auth.get("scopes") or []):
            print(f" FOLLOWER[{i}] token missing 'trade' scope — copying will fail.")
        ws.close()
    except Exception as e:
        print(f"Follower[{i}] auth failed:", e)

# Enable allow_copiers with ADMIN token (REAL only)
try:
    set_allow_copiers(TRADER_ADMIN_TOKEN, True)
except Exception as e:
    print("Failed to set allow_copiers=1. This requires REAL account + ADMIN scope.\nError:", e); raise

# Verify
settings = get_settings_with(TRADER_ADMIN_TOKEN)
print("Current settings:", {"allow_copiers": settings.get("allow_copiers")})

# Start copying for followers
started = []
for i, tok in enumerate(FOLLOWER_TOKENS, 1):
    try:
        copy_start_for_follower(tok, TRADER_READONLY_TOKEN)
        print(f"copy_start OK for follower[{i}]")
        started.append(tok)
    except Exception as e:
        print(f"copy_start FAILED for follower[{i}]:", e)

# Stream transactions
stop_flag = threading.Event()
t = threading.Thread(target=stream_trader_transactions, args=(stop_flag,), daemon=True)
t.start()

print("\nAll set. Trade manually on DTrader. This will mirror 1:1 for all started followers.\n"
      "Press Ctrl+C here to stop (it will detach followers cleanly).\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping copy for followers...")
    stop_flag.set()
    for i, tok in enumerate(started, 1):
        try:
            copy_stop_for_follower(tok, TRADER_READONLY_TOKEN)
            print(f"copy_stop OK for follower[{i}]")
        except Exception as e:
            print(f"copy_stop error follower[{i}]:", e)
    if DISABLE_ALLOW_COPIERS_ON_EXIT:
        try:
            set_allow_copiers(TRADER_ADMIN_TOKEN, False)
            print("allow_copiers turned OFF")
        except Exception as e:
            print("Failed to turn off allow_copiers:", e)
    print("Done. Goodbye.")
