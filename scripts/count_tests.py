import subprocess
import sys
from collections import defaultdict

result = subprocess.run(
    [sys.executable, "-m", "pytest", "--collect-only", "-q"],
    capture_output=True,
    text=True,
)

collected = defaultdict(list)
for line in result.stdout.splitlines():
    line = line.strip()
    if "::" in line:
        file_path, test_name = line.split("::", 1)
        collected[file_path].append(test_name)

print(f"TOTAL UNIQUE TESTS COLLECTED: {sum(len(v) for v in collected.values())}\n")
for f_path, t_list in sorted(collected.items()):
    print(f"=== {f_path} ({len(t_list)} tests) ===")
    for t in t_list:
        print(f"  - {t}")
    print()
