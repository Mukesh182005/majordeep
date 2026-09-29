import os
import re

PATTERNS = [
    re.compile(r'(?i)(?:api[_-]?key|secret[_-]?key|auth[_-]?token)\s*[:=]\s*[\'"][0-9a-zA-Z]{20,}[\'"]'),
    re.compile(r'-----BEGIN (?:RSA|EC|OPENSSH|PGP)? PRIVATE KEY-----')
]

found = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ['.git', '.venv', 'node_modules', 'dist', '__pycache__', '.pytest_cache', 'research_archive']]
    for f in files:
        if f.endswith(('.py', '.js', '.jsx', '.json', '.yml', '.yaml', '.md', '.env.example')) and not f == '.env':
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                    for pat in PATTERNS:
                        m = pat.search(content)
                        if m and 'example' not in f.lower() and 'test' not in f.lower():
                            found.append((p, m.group(0)))
            except Exception:
                pass

print(f"Secrets scan completed. Detected potential secrets: {len(found)}")
for p, s in found:
    print(" ", p, "->", s[:30])
