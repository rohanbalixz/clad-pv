import hmac, json, time
from hashlib import sha256
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .audit_utils import write_audit

SECRET = b"change-this-demo-secret"  # replace in production
CONTROL = Path("gateway/shims/sunspec_guard/control.json")

class SetCurtailment(BaseModel):
    curtailment: float = Field(ge=0.0, le=1.0)
    nonce: str
    ts: int
    tag: str  # hex

def make_tag(secret: bytes, msg: bytes) -> str:
    return hmac.new(secret, msg, sha256).hexdigest()

app = FastAPI(title="CLAD-PV Secure Control API")

@app.post("/set_curtailment")
def set_curtailment(req: SetCurtailment):
    now = int(time.time())
    if abs(now - req.ts) > 60:
        raise HTTPException(400, "stale timestamp")

    payload = f"{req.curtailment:.6f}|{req.nonce}|{req.ts}".encode()
    if not hmac.compare_digest(req.tag, make_tag(SECRET, payload)):
        raise HTTPException(401, "bad signature")

    CONTROL.parent.mkdir(parents=True, exist_ok=True)
    CONTROL.write_text(json.dumps({"curtailment": float(req.curtailment)}, indent=2))

    # audit (tamper-evident)
    write_audit({
        "action": "set_curtailment",
        "curtailment": float(req.curtailment),
        "nonce": req.nonce,
        "caller": "local",
        "ts": req.ts
    })
    return {"ok": True, "applied": req.curtailment}
