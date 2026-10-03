# -*- coding: utf-8 -*-
r"""work/text/sys_kr.py 번역 → work/text/darksavior_sys.tsv 번역 열 (2026-10-03)
  python tools/apply_sys.py
"""
import csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'work', 'text'))
from sys_kr import KR

P = os.path.join(ROOT, 'work', 'text', 'darksavior_sys.tsv')
rows = list(csv.reader(open(P, encoding='utf-8', newline=''), delimiter='\t', quoting=csv.QUOTE_NONE, escapechar='\\'))
n = 0
for r in rows[1:]:
    i = int(r[0].split(':')[1])
    if i in KR:
        assert '\n' not in KR[i]
        r[2] = KR[i]; r[3] = r[3] or '시스템'; n += 1
w = csv.writer(open(P, 'w', encoding='utf-8', newline=''), delimiter='\t', lineterminator='\n', quoting=csv.QUOTE_NONE, escapechar='\\')
w.writerows(rows)
print('반영', n)
