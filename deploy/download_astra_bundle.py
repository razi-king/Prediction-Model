"""
Download the Astra DB "Secure Connect Bundle" (secure-connect-<db>.zip) with Astra's
official DevOps API, for when the "Download SCB" button in the Astra Portal is disabled.

    python deploy/download_astra_bundle.py

It asks for:
  * the Database ID  (Astra Portal -> your database -> "ID ..." at the top, click the copy icon)
  * your application token (AstraCS:...), typed hidden, never saved anywhere

and saves  C:\\Users\\<you>\\Downloads\\secure-connect-devascend.zip
API used (from the Astra docs):  POST https://api.astra.datastax.com/v2/databases/<DATABASE_ID>/secureBundleURL
"""
import getpass
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import os

db_id = input("Database ID (looks like 9282bb1a-....): ").strip()

# Token: from the ASTRA_DB_TOKEN environment variable if set, else typed in.
# (Windows' hidden password prompt often ignores Ctrl+V, so we fall back to a visible prompt.)
token = os.getenv("ASTRA_DB_TOKEN", "").strip()
if not token:
    token = getpass.getpass("Application token (AstraCS:..., hidden): ").strip()
if not token.startswith("AstraCS:"):
    token = input("Paste the token here instead (it will be visible): ").strip().strip('"')
if not db_id or not token.startswith("AstraCS:"):
    sys.exit("Need the database ID and a token that starts with AstraCS:")

# 1) ask Astra for a short-lived download link (valid ~5 minutes)
req = urllib.request.Request(
    f"https://api.astra.datastax.com/v2/databases/{db_id}/secureBundleURL",
    method="POST",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
except urllib.error.HTTPError as err:
    body = err.read().decode(errors="replace")[:300]
    hints = {401: "token is wrong or expired", 403: "token needs the Database Administrator role",
             404: "Database ID is wrong (copy it from the top of the database page)"}
    sys.exit(f"Astra answered {err.code}: {hints.get(err.code, body)}")

# the API returns one object, or a list (one per region): take the first download link
item = data[0] if isinstance(data, list) else data
url = item.get("downloadURL")
if not url:
    sys.exit(f"No download link in Astra's answer: {data}")

# 2) download the zip itself
# saved next to this script (deploy/); *.zip is in .gitignore, so it can never reach GitHub
out = Path(__file__).resolve().parent / "secure-connect-devascend.zip"
with urllib.request.urlopen(url, timeout=60) as resp:
    out.write_bytes(resp.read())
print(f"Saved {out} ({out.stat().st_size:,} bytes)")
print("Next:  python deploy\\encode_astra_bundle.py \"" + str(out) + "\"")
