import os
import shlex

import ytmusicapi

RAW_FILE = "headers_raw.txt"

if not os.path.exists(RAW_FILE):
    print("File " + RAW_FILE + " not found. Create it in this folder and paste the copied request into it.")
    raise SystemExit(1)

with open(RAW_FILE, encoding="utf-8") as f:
    text = f.read()

headers = []
if text.strip().startswith("curl"):
    parts = shlex.split(text.replace("\\\r\n", " ").replace("\\\n", " "))
    for i in range(len(parts) - 1):
        if parts[i] in ("-H", "--header"):
            headers.append(parts[i + 1])
        if parts[i] in ("-b", "--cookie"):
            headers.append("cookie: " + parts[i + 1])
    text = "\n".join(headers)

ytmusicapi.setup(filepath="headers_auth.json", headers_raw=text)
os.remove(RAW_FILE)
print("Done. headers_auth.json created, " + RAW_FILE + " deleted.")
