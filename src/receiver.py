#!/usr/bin/env python3
"""
Authenticated inbound mail receiver.

HTTP contract:
  POST /inbound
  Authorization: Bearer <token>
  X-Envelope-From: sender address (may be empty for a null sender)
  X-Envelope-To: one recipient address
  Body: original raw RFC 5322/MIME message

The paired Cloudflare Worker must send these exact headers.
"""

import hmac
import logging
import os
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# -------- Administrator settings --------
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8787
ENDPOINT_PATH = "/inbound"
ALLOWED_DOMAIN = "example.org"       # CHANGE THIS
TOKEN_FILE = "/etc/mail-ingress-token"
MAX_MESSAGE_BYTES = 25 * 1024 * 1024
SENDMAIL = "/usr/sbin/sendmail"
SENDMAIL_TIMEOUT_SECONDS = 30
# ----------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
LOG = logging.getLogger("mail-ingress")

# Deliberately conservative mailbox syntax. Adjust only if your mail
# system supports address forms this template rejects.
LOCAL_PART_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}$")
DOMAIN_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def load_token():
    token = Path(TOKEN_FILE).read_text(encoding="utf-8").strip()
    if len(token) < 32:
        raise RuntimeError("Ingress token is too short; use a long random secret")
    return token


TOKEN = load_token()
ALLOWED_DOMAIN = ALLOWED_DOMAIN.strip().lower().rstrip(".")


def valid_domain(domain):
    if not domain or len(domain) > 253:
        return False
    labels = domain.split(".")
    return all(DOMAIN_LABEL_RE.fullmatch(label) for label in labels)


if not valid_domain(ALLOWED_DOMAIN):
    raise RuntimeError("ALLOWED_DOMAIN is not a valid DNS domain")


def valid_email_address(address, allow_empty=False):
    """Validate a simple addr-spec; reject display names and header injection."""
    if address == "" and allow_empty:
        return True
    if not address or len(address) > 254:
        return False
    if any(ch in address for ch in "\r\n\t <>(),;:\\[]"):
        return False
    if address.count("@") != 1:
        return False
    local, domain = address.rsplit("@", 1)
    if not LOCAL_PART_RE.fullmatch(local):
        return False
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    return valid_domain(domain)


def recipient_is_allowed(address):
    if not valid_email_address(address):
        return False
    _, domain = address.rsplit("@", 1)
    return domain.lower() == ALLOWED_DOMAIN


class Handler(BaseHTTPRequestHandler):
    server_version = "MailIngress"
    sys_version = ""

    def log_message(self, fmt, *args):
        # Avoid default access logs that can contain sensitive query strings.
        LOG.info("HTTP request handled")

    def respond(self, status, message):
        body = (message + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.respond(405, "Method not allowed")

    def do_HEAD(self):
        self.respond(405, "Method not allowed")

    def do_PUT(self):
        self.respond(405, "Method not allowed")

    def do_DELETE(self):
        self.respond(405, "Method not allowed")

    def do_POST(self):
        if self.path != ENDPOINT_PATH:
            self.respond(404, "Not found")
            return

        auth = self.headers.get("Authorization", "")
        expected = "Bearer " + TOKEN
        if not hmac.compare_digest(auth, expected):
            self.respond(403, "Forbidden")
            return

        # This receiver expects a fixed-length body. The Worker should
        # send Content-Length; chunked transfer encoding is not accepted.
        if self.headers.get("Transfer-Encoding"):
            self.respond(400, "Transfer-Encoding is not supported")
            return

        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length)
        except (TypeError, ValueError):
            self.respond(411, "Content-Length required")
            return

        if length <= 0:
            self.respond(400, "Empty message")
            return
        if length > MAX_MESSAGE_BYTES:
            self.respond(413, "Message too large")
            return

        sender = self.headers.get("X-Envelope-From", "")
        recipient = self.headers.get("X-Envelope-To", "")

        if not valid_email_address(sender, allow_empty=True):
            self.respond(400, "Invalid envelope sender")
            return
        if not recipient_is_allowed(recipient):
            self.respond(400, "Recipient not permitted")
            return

        try:
            message = self.rfile.read(length)
        except Exception:
            LOG.exception("Failed reading request body")
            self.respond(400, "Could not read message")
            return

        if len(message) != length:
            self.respond(400, "Incomplete message body")
            return

        # Use the validated recipient, not a fixed mailbox address.
        # An empty envelope sender represents the SMTP null reverse-path.
        command = [SENDMAIL, "-i"]

        if sender == "":
            command.append("-f<>")
        else:
            command.extend(["-f", sender])
        command.append(recipient)

        try:
            result = subprocess.run(
                command,
                input=message,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=SENDMAIL_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            LOG.error("Postfix handoff timed out")
            self.respond(502, "Mail handoff timed out")
            return
        except OSError:
            LOG.exception("Could not execute local sendmail interface")
            self.respond(502, "Mail handoff unavailable")
            return

        if result.returncode != 0:
            # Do not return Postfix's raw stderr to the remote caller.
            LOG.error("Postfix handoff failed; exit status %s", result.returncode)
            self.respond(502, "Mail handoff failed")
            return

        LOG.info("Message accepted for recipient domain %s", ALLOWED_DOMAIN)
        self.respond(202, "Accepted for local mail processing")


if __name__ == "__main__":
    LOG.info("Starting receiver on %s:%s", LISTEN_HOST, LISTEN_PORT)
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOG.info("Receiver stopping")
    finally:
        server.server_close()
