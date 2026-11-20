import re
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

out = subprocess.check_output(['git', 'add', '-n', '.'], cwd=str(ROOT_DIR), text=True)
files = [line.replace('add ', '').strip("' ") for line in out.strip().splitlines() if line.startswith('add ')]
print(f"Scanning {len(files)} files for sensitive tokens, credentials, and secrets...")

patterns = [
    re.compile(r'ghp_[a-zA-Z0-9]{20,}'),
    re.compile(r'gho_[a-zA-Z0-9]{20,}'),
    re.compile(r'github_pat_[a-zA-Z0-9]{20,}'),
    re.compile(r'BEGIN (?:RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY'),
    re.compile(r'AIza[0-9A-Za-z-_]{35}'),
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),
]

flagged = []
for rel_p in files:
    full_p = ROOT_DIR / rel_p
    try:
        text = full_p.read_text(encoding='utf-8', errors='ignore')
        for pat in patterns:
            match = pat.search(text)
            if match:
                flagged.append((rel_p, pat.pattern, match.group(0)[:15]))
    except Exception as e:
        print(f"Could not read {rel_p}: {e}")

if flagged:
    print("FAILED: Sensitive tokens found:")
    for f in flagged:
        print("  -", f)
else:
    print("PASS: 0 sensitive credentials or tokens found in candidate files.")
