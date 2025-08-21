Deriv DTrader 1:1 Copy-Mirror (Manual → Followers, Real-time)

Mirror your manual DTrader (Options: Rise/Fall, etc.) trades to multiple follower accounts in real time using Deriv’s WebSocket Copy Trading endpoints.
No strategy bot, no polling, no contract reconstruction the server mirrors exactly what you place (symbol, contract type, stake, expiry, barriers).

Stack: Python · WebSocket · Jupyter (single-cell)

Features

Exact 1:1 mirroring of manual DTrader options (Rise/Fall etc.)

Single Jupyter cell: run once to enable copying and start streaming

Safe tokens: uses admin token only to flip allow_copiers, and a read-only token for everything else

Multi-follower support

Live transaction stream in the notebook

Requirements

Python 3.9+

pip install websocket-client

Deriv App ID (use 1089 for testing; register your own for prod)

Tokens:

TRADER_ADMIN_TOKEN → REAL account token with admin scope (used to set allow_copiers=1)

TRADER_READONLY_TOKEN → REAL account token with read scope (followers reference this)

FOLLOWER_TOKENS → one or more Trade-scope tokens (followers)

Landing company must match between master and each follower (e.g., both CR…).
Followers can be real; demo followers won’t attach to a real master via built-in copy trading.

Quick Start

Create tokens in your Deriv dashboard:

Master (trader): Admin scope (real account) and Read-only scope (real account)

Followers: Trade scope (real accounts under same landing company)

Open the notebook and paste the single-cell script from this repo.

Edit the CONFIG block:

APP_ID = 1089
TRADER_ADMIN_TOKEN    = "your_admin_token"
TRADER_READONLY_TOKEN = "your_readonly_token"
FOLLOWER_TOKENS = ["follower_trade_token_1", "follower_trade_token_2"]


Run the cell and keep it running while you trade manually on DTrader.

Expected log:

Starting: Deriv Copy-Mirror (exact 1:1). Followers: 2
TRADER_ADMIN_TOKEN: loginid=CR123456 type=REAL scopes=['admin','read']
TRADER_READONLY_TOKEN: loginid=CR123456 type=REAL scopes=['read']
FOLLOWER[1]: loginid=CR654321 type=REAL scopes=['trade']
FOLLOWER[2]: loginid=CR789012 type=REAL scopes=['trade']
allow_copiers set to 1: OK
Current settings: {'allow_copiers': 1}
copy_start OK for follower[1]
copy_start OK for follower[2]
→ Streaming trader transactions (buy/sell). Ctrl+C to stop...


Then place a small Rise/Fall trade on DTrader — you’ll see the [buy] line and the same contract on each follower.

How It Works

The script authorizes the admin token once to call:

{"set_settings": 1, "allow_copiers": 1}


Each follower authorizes its own Trade token and calls:

{"copy_start": "<TRADER_READONLY_TOKEN>"}


Deriv’s servers mirror your manual contracts as placed (no filters) to each follower.

A live transactions subscription prints your buys/sells in the notebook.

Security

Never commit tokens to git. Use env vars or a local .env if you prefer.

Use a true read-only token for TRADER_READONLY_TOKEN (do not grant trade).

Keep the admin token private; it’s only needed to set allow_copiers.

Limitations & Notes

Master must be REAL. allow_copiers isn’t applicable to virtual accounts.

Landing company must match (e.g., CR→CR). Otherwise CopyTradingNotAllowed.

Followers need sufficient balance, limits, and market access to mirror your stakes/contracts.

For all-demo testing, the official copy_start won’t attach. Use a “shadow copier”
(subscribe to a demo master’s transactions and re-issue buy for demo followers) if you need a sandbox.

Troubleshooting

PermissionDenied … requires admin scope: your master token isn’t admin scope → regenerate.

CopyTradingNotAllowed … same landing company: master/follower entities differ → use a follower under the same company.

InsufficientBalance / NotAllowed: follower stake too high, market closed, or regional restriction.

Nothing mirrors? Verify the follower token has trade scope and the follower is REAL under same landing company.

License

MIT. See LICENSE.

Disclaimer: Options trading is risky. This code is provided “as-is” for educational purposes. You are responsible for compliance with Deriv’s terms and your local regulations.
