"""
GCG Trading — TradingView Webhook Receiver
==========================================
Receives alerts from TradingView and sends email notifications.
Deploy on Railway.app for a free permanent public URL.

Setup:
  1. Deploy to Railway (see README)
  2. Set environment variables:
       EMAIL_FROM     = your Gmail address
       EMAIL_TO       = destination email
       EMAIL_PASSWORD = Gmail app password (16-char)
  3. Copy your Railway URL into TradingView alert webhook field
"""

import os
import json
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from flask import Flask, request, jsonify

# ── Config from environment variables ─────────────────────
EMAIL_FROM     = os.environ.get("EMAIL_FROM",     "")
EMAIL_TO       = os.environ.get("EMAIL_TO",       "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
SMTP_SERVER    = "smtp.gmail.com"
SMTP_PORT      = 587
PORT           = int(os.environ.get("PORT", 8080))

# ── Logging ────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("webhook")

app = Flask(__name__)

# ── Email sender ───────────────────────────────────────────
def send_email(subject: str, body: str):
    if not EMAIL_FROM or not EMAIL_PASSWORD:
        log.warning("Email credentials not configured — skipping email")
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
        log.info(f"Email sent: {subject}")
    except Exception as e:
        log.error(f"Email failed: {e}")

# ── Webhook endpoint ───────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # TradingView sends JSON body
        data = request.get_json(force=True, silent=True)
        if not data:
            # Try raw text (some TV plans send plain text)
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

        # Format price and MA
        try:    price_f = f"${float(price):.2f}"
        except: price_f = price
        try:    ma_f = f"${float(ma_val):.2f}"
        except: ma_f = ma_val

        # Emoji based on direction
        if direction == "ABOVE":
            emoji   = "🟢"
            signal  = "crossed ABOVE"
        else:
            emoji   = "🔴"
            signal  = "crossed BELOW"

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
    """Hit /test to send a test email and confirm everything works."""
    send_email(
        "✅ GCG Trading Webhook — Test",
        f"Webhook server is running and email is configured correctly.\nTime: {datetime.now()}"
    )
    return jsonify({"status": "test email sent"}), 200

if __name__ == "__main__":
    log.info(f"GCG Trading webhook server starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
