"""
GCG Trading — TradingView Webhook Receiver
==========================================
Receives alerts from TradingView and sends email notifications via SendGrid.
Deploy on Railway.app for a free permanent public URL.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime
from flask import Flask, request, jsonify

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
EMAIL_FROM       = os.environ.get("EMAIL_FROM", "")
EMAIL_TO         = os.environ.get("EMAIL_TO", "")
PORT             = int(os.environ.get("PORT", 8080))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("webhook")

app = Flask(__name__)

def send_email(subject: str, body: str):
    if not SENDGRID_API_KEY or not EMAIL_FROM:
        log.warning("SendGrid credentials not configured — skipping email")
        return
    payload = json.dumps({
        "personalizations": [{"to": [{"email": EMAIL_TO}]}],
        "from": {"email": EMAIL_FROM},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}]
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=payload,
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            log.info(f"Email sent via SendGrid: {subject} (status {resp.status})")
    except urllib.error.HTTPError as e:
        log.error(f"SendGrid HTTP error: {e.code} {e.read().decode()}")
    except Exception as e:
        log.error(f"SendGrid error: {e}")

def fmt_price(val):
    try:    return f"${float(val):.2f}"
    except: return val or "—"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            raw = request.data.decode("utf-8").strip()
            try:    data = json.loads(raw)
            except: data = {"raw": raw}

        log.info(f"Webhook received: {data}")

        ticker    = data.get("ticker",    "UNKNOWN")
        price     = data.get("price",     "?")
        direction = data.get("direction", "?")
        period    = data.get("period",    "?")
        list_type = data.get("list",      "?")
        time_str  = data.get("time",      datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ma5       = data.get("5sma",      None)
        ma10      = data.get("10sma",     None)
        ema20     = data.get("20ema",     None)

        if direction == "ABOVE":
            emoji  = "🔴"
            signal = "crossed ABOVE"
        else:
            emoji  = "🟢"
            signal = "crossed BELOW"

        subject = f"{emoji} {ticker} {signal} {period}-day MA  [{list_type}]"

        ma_section = ""
        if ma5 or ma10 or ema20:
            ma_section = f"""
--- Moving Averages ---
5-Day  SMA : {fmt_price(ma5)}
10-Day SMA : {fmt_price(ma10)}
20-Day EMA : {fmt_price(ema20)}
"""

        body = f"""GCG Trading — MA Cross Alert
{'='*40}

Ticker    : {ticker}
Signal    : {signal} {period}-day MA
Price     : {fmt_price(price)}
List      : {list_type}
{ma_section}
Time      : {time_str}

---
Sent by GCG Trading TradingView Webhook
"""
        send_email(subject, body)
        return jsonify({"status": "ok", "ticker": ticker}), 200

    except Exception as e:
        log.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status":    "running",
        "service":   "GCG Trading Webhook Receiver",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route("/test", methods=["GET"])
def test():
    send_email(
        "✅ GCG Trading Webhook — Test",
        f"""GCG Trading — MA Cross Alert
{'='*40}

Ticker    : TEST
Signal    : crossed BELOW 4/8/18-day MA
Price     : $150.00
List      : LONG

--- Moving Averages ---
5-Day  SMA : $151.20
10-Day SMA : $153.40
20-Day EMA : $155.10

Time      : {datetime.now()}

---
Sent by GCG Trading TradingView Webhook
"""
    )
    return jsonify({"status": "test email sent"}), 200

if __name__ == "__main__":
    log.info(f"GCG Trading webhook server starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
