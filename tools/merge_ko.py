# -*- coding: utf-8 -*-
r"""사용자 번역 TSV(my files\ds_ko\*.tsv) → work/text/darksavior_*.tsv «번역» 열 병합 (2026-10-03)

  python tools/merge_ko.py            검사만(ID·원문 대조, 제어 코드, 빈칸, sys 충돌)
  python tools/merge_ko.py --write    병합

★받은 번역이라고 검사를 건너뛰지 않는다([[feedback_translation_layout_pipeline]]).
  여기서는 «합치기 전» 사실 확인만 하고, 조판(창 폭·줄 수)은 빌더 검사가 맡는다.
"""
import csv, glob, os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'work', 'text')
USR = os.path.join(ROOT, 'my files', 'ds_ko')
TOK = re.compile(r'\{[^}]*\}')


def rd(p):
    with open(p, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh, delimiter='\t', quoting=csv.QUOTE_NONE, escapechar='\\'))


def load_cur():
    cur, files = {}, {}
    for p in sorted(glob.glob(os.path.join(SRC, 'darksavior_*.tsv'))):
        rows = rd(p)
        files[p] = rows
        for r in rows:
            cur[r['ID']] = r
    return cur, files


def load_usr():
    usr, dup = {}, []
    for p in sorted(glob.glob(os.path.join(USR, '*.tsv'))):
        for r in rd(p):
            if r['ID'] in usr:
                dup.append(r['ID'])
            usr[r['ID']] = r
    return usr, dup


def ctrl_seq(s, keep_n=False):
    """제어 코드 열(줄바꿈 {n} 은 따로 본다)."""
    return [t for t in TOK.findall(s) if keep_n or t != '{n}']


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    write = '--write' in sys.argv
    cur, files = load_cur()
    usr, dup = load_usr()
    print('현재 %d줄 / 받은 번역 %d줄 / 중복 ID %d' % (len(cur), len(usr), len(dup)))
    miss = sorted(set(cur) - set(usr)); extra = sorted(set(usr) - set(cur))
    print('받은 쪽에 없는 ID %d %s / 모르는 ID %d %s' % (len(miss), miss[:5], len(extra), extra[:5]))
    srcdiff = [i for i in usr if i in cur and usr[i]['원문'] != cur[i]['원문']]
    print('원문 열이 다른 줄 %d %s' % (len(srcdiff), srcdiff[:5]))
    empty = [i for i in usr if i in cur and not usr[i]['번역'].strip()]
    print('번역 빈칸 %d %s' % (len(empty), empty[:8]))
    print('구역별', dict(collections.Counter(i.split(':')[0] for i in usr)))
    bad_ctrl = []
    for i, r in usr.items():
        if i not in cur or not r['번역'].strip():
            continue
        if ctrl_seq(r['번역']) != ctrl_seq(cur[i]['원문']):
            bad_ctrl.append(i)
    print('제어 코드({n} 제외) 열이 원문과 다른 줄 %d' % len(bad_ctrl))
    for i in bad_ctrl[:15]:
        print('   %s\n     원문 %s\n     번역 %s' % (i, cur[i]['원문'], usr[i]['번역']))
    sysd = [(i, cur[i]['번역'], usr[i]['번역']) for i in usr
            if i.startswith('sys') and i in cur and cur[i]['번역'] and cur[i]['번역'] != usr[i]['번역']]
    print('sys: 지금 번역과 다른 줄 %d' % len(sysd))
    for x in sysd[:60]:
        print('   %s  지금 %r → 받은 %r' % x)
    if not write:
        print('\n검사만 — 병합 안 함 (--write).')
        return
    n = 0
    for p, rows in files.items():
        for r in rows:
            u = usr.get(r['ID'])
            if u and u['번역'].strip() and u['번역'] != r['번역']:
                r['번역'] = u['번역']; n += 1
        with open(p, 'w', encoding='utf-8', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter='\t',
                               quoting=csv.QUOTE_NONE, escapechar='\\', lineterminator='\n')
            w.writeheader(); w.writerows(rows)
    print('병합 %d줄' % n)


if __name__ == '__main__':
    main()
