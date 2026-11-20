from pathlib import Path
import re

for pub in ['US6657443B2', 'US6831468B2']:
    t = Path(f'data/raw/{pub}.html').read_text(encoding='utf-8')
    m_app = re.search(r'itemprop=["\']applicationNumber["\'][^>]*>([^<]+)<', t)
    print(pub, 'App:', m_app.group(1).strip() if m_app else '?')
    m_cip = re.search(r'Continuation-in-part[^\.]+?\.', t, re.I)
    print(pub, 'CIP:', m_cip.group(0) if m_cip else 'None')
    m_fam = re.search(r'<h2>ID=(\d+)</h2>', t)
    print(pub, 'Google Patents Family ID:', m_fam.group(1) if m_fam else '?')
    print()

