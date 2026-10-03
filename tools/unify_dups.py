# -*- coding: utf-8 -*-
r"""같은 원문 장면(507·508·509·517 반복)의 번역을 하나로 통일 (2026-10-03, 사용자 «내가 골라 통일»)

  python tools/unify_dups.py [--write]    → work/text/unify_dups_log.tsv

판 고르기: 감점이 가장 적은 판, 같으면 파일 우선순위 508 > 507 > 517 > 509
  감점  · 26칸 넘는 줄 (줄마다 10)
        · {n} 줄바꿈이 낱말 한가운데(앞뒤가 모두 한글이고 원문은 거기서 안 끊김) (곳마다 3)
        · {3:0}(아이템 이름) 뒤 조사를 하나로 못박음(을/를/은/는/이/가 단독) (곳마다 5)
"""
import collections, glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kocheck as K, normalize_ko as N

PRI = {'508': 0, '507': 1, '517': 2, '509': 3}
BP = {'!': '！', '?': '？', ',': '、', '.': '。', '~': 'ー', '-': 'ー', '·': '・'}
FIXED_PART = re.compile(r'\{3:0\}(을|를|은|는|이|가)(?!\()')
MIDWORD = re.compile(r'[가-힣]\{n\}[가-힣]')


def shown(t):
    return ''.join(BP.get(c, c) for c in K.squeeze(t))


def penalty(t, krn):
    L, _ = K.layout(K.squeeze(t), krn, False)
    return 10 * sum(1 for n in L if n > K.LIMIT) + 3 * len(MIDWORD.findall(t)) + 5 * len(FIXED_PART.findall(t))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    write = '--write' in sys.argv
    files = {p: N.rd(p) for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'text', 'darksavior_*.tsv')))}
    R = {r['ID']: r for rows in files.values() for r in rows}
    krn = {int(i[4:]): K.squeeze(r['번역'] or r['원문']) for i, r in R.items() if i.startswith('sys:')}
    by = collections.defaultdict(list)
    for i, r in R.items():
        if not i.startswith('sys'):
            by[r['원문']].append(i)
    log = []; won = collections.Counter()
    for src, ids in by.items():
        if len(ids) < 2 or len({shown(R[i]['번역']) for i in ids}) < 2:
            continue
        best = min(ids, key=lambda i: (penalty(R[i]['번역'], krn), PRI[i[:3]]))
        won[best[:3]] += 1
        for i in ids:
            if R[i]['번역'] != R[best]['번역']:
                log.append((i, best, R[i]['번역'], R[best]['번역']))
                R[i]['번역'] = R[best]['번역']
    print('바뀐 줄 %d · 고른 판 파일별 %s' % (len(log), dict(won)))
    with open(os.path.join(ROOT, 'work', 'text', 'unify_dups_log.tsv'), 'w', encoding='utf-8') as fh:
        fh.write('ID\t고른 판\t전\t후\n')
        for x in log:
            fh.write('\t'.join(x) + '\n')
    if write:
        for p, rows in files.items():
            N.wr(p, rows)
        print('적용 완료')


if __name__ == '__main__':
    main()
