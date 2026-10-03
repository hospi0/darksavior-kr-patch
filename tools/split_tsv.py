# -*- coding: utf-8 -*-
r"""번역용 TSV 를 29KB(UTF-8 바이트, 머리줄 포함) 단위로 나눠 my files\tsv\ds_001.tsv … 로 (사용자 요청 시에만 실행)
  순서: sys(이름·아이템·시스템) → 507 → 508 → 509 → 517 를 한 줄기로 이어 자른다(자투리 없음).
  빌더는 work/text/darksavior_*.tsv 를 읽는다 — 번역이 돌아오면 ID 로 합쳐 넣는다.
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'work', 'text')
OUT = os.path.join(ROOT, 'my files', 'tsv')
LIMIT = 29 * 1024
ORDER = ['sys', '507', '508', '509', '517']


def main():
    head = None; lines = []
    for k in ORDER:
        with open(os.path.join(SRC, 'darksavior_%s.tsv' % k), encoding='utf-8', newline='') as fh:
            L = fh.read().splitlines(keepends=True)
        head = head or L[0]; lines += L[1:]
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if re.match(r'ds_\d{3}\.tsv$', f):
            os.remove(os.path.join(OUT, f))
    files = []; cur = []; size = len(head.encode('utf-8'))
    for ln in lines:
        b = len(ln.encode('utf-8'))
        if cur and size + b > LIMIT:
            files.append(cur); cur = []; size = len(head.encode('utf-8'))
        cur.append(ln); size += b
    if cur:
        files.append(cur)
    for i, fl in enumerate(files):
        p = os.path.join(OUT, 'ds_%03d.tsv' % (i + 1))
        with open(p, 'w', encoding='utf-8', newline='') as o:
            o.write(head + ''.join(fl))
        print('%s  %d줄  %d B  %s‥%s' % (os.path.basename(p), len(fl), os.path.getsize(p), fl[0].split('\t')[0], fl[-1].split('\t')[0]))
    print('합계 %d줄 · %d파일' % (len(lines), len(files)))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
