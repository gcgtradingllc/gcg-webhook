
"""
GCG Trading — TradingView Webhook Receiver
==========================================
Receives alerts from TradingView and sends email notifications via SendGrid.
Deploy on Railway.app for a free permanent public URL.

Setup:
  1. Deploy to Railway (see README)
  2. Set environment variables:
       SENDGRID_API_KEY = your SendGrid API key (starts with SG.)
       EMAIL_FROM       = your verified sender email
       EMAIL_TO         = destination email
  3. Copy your Railway URL into TradingView alert webhook field
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime
from flask import Flask, request, jsonify

# ── Config from environment variables ─────────────────────
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
EMAIL_FROM       = os.environ.get("EMAIL_FROM", "")
EMAIL_TO         = os.environ.get("EMAIL_TO", "")
PORT             = int(os.environ.get("PORT", 8080))

# ── Logging ────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("webhook")

app = Flask(__name__)

# ── Email sender via SendGrid ──────────────────────────────
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

# ── Webhook endpoint ───────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            raw = request.data.decode("utf-8").strip()
            try:
                data = json.loads(raw)
            except Exception:
                data = {"raw": raw}

        log.info(f"Webhook received: {data}")

        ticker    = data.get("ticker",    "UNKNOWN")
        price     = data.get("price",     "?")
        direction = data.get("direction", "?")
        period    = data.get("period",    "?")
        list_type = data.get("list",      "?")
        ma_val    = data.get("ma",        "?")
        time_str  = data.get("time",      datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        try:    price_f = f"${float(price):.2f}"
        except: price_f = price
        try:    ma_f = f"${float(ma_val):.2f}"
        except: ma_f = ma_val

        if direction == "ABOVE":
            emoji  = "🟢"
            signal = "crossed ABOVE"
        else:
            emoji  = "🔴"
            signal = "crossed BELOW"

        subject = f"{emoji} {ticker} {signal} {period}-day MA  [{list_type} list]"
        body = f"""GCG Trading — MA Cross Alert

Ticker    : {ticker}
Signal    : {signal} {period}-day MA
Price     : {price_f}
MA Value  : {ma_f}
List      : {list_type}
Time      : {time_str}

---
Sent by GCG Trading TradingView Webhook
"""
        send_email(subject, body)
        return jsonify({"status": "ok", "ticker": ticker}), 200

    except Exception as e:
        log.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ── Health check ───────────────────────────────────────────
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
        f"Webhook server is running and SendGrid email is configured correctly.\nTime: {datetime.now()}"
    )
    return jsonify({"status": "test email sent"}), 200

if __name__ == "__main__":
    log.info(f"GCG Trading webhook server starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
