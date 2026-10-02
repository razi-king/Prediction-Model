"""
Turn the Astra DB "secure connect bundle" (a .zip file) into one line of base64 text,
so it can be pasted into a Hugging Face Space secret called ASTRA_DB_SECURE_BUNDLE_B64.

    python deploy/encode_astra_bundle.py path\\to\\secure-connect-devascend.zip

It writes deploy/astra_bundle_b64.txt (ignored by git: it is a secret, never commit it).
"""
import base64
import sys
from pathlib import Path

if len(sys.argv) != 2:
    sys.exit("usage: python deploy/encode_astra_bundle.py <secure-connect-bundle.zip>")

bundle = Path(sys.argv[1])
if not bundle.exists() or bundle.suffix != ".zip":
    sys.exit(f"Not a .zip file: {bundle}")

encoded = base64.b64encode(bundle.read_bytes()).decode("ascii")
out = Path(__file__).resolve().parent / "astra_bundle_b64.txt"
out.write_text(encoded, encoding="ascii")
print(f"Wrote {len(encoded):,} characters to {out}")
print("Copy the WHOLE file content into the Hugging Face secret ASTRA_DB_SECURE_BUNDLE_B64.")
