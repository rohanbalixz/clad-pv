import hmac, json, time
from hashlib import sha256
from pathlib import Path

AUDIT_LOG = Path("docs/tables/control_audit.log")
AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
AUDIT_SECRET = b"rotate-this-audit-secret"  # rotate periodically

def _tag(msg: bytes) -> str:
    return hmac.new(AUDIT_SECRET, msg, sha256).hexdigest()

def write_audit(event: dict):
    # Normalize + sign
    event = dict(event)  # copy
    event["ts"] = int(event.get("ts", time.time()))
    payload = json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
    entry = {"event": event, "sig": _tag(payload)}
    with AUDIT_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")
