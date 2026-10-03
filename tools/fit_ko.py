# -*- coding: utf-8 -*-
r"""창 폭 맞추기 (2026-10-03) — work/text/darksavior_*.tsv «번역» 열

  python tools/fit_ko.py [--write]   → work/text/fit_log.tsv
  ① sys: 번역 줄이 원문 줄(칸)보다 길고, 병합 전 판(work/text/backup_premerge)이 원문 폭 안이면 그 판으로
  ② {13} 좁은 창 = 한 줄 7칸(2026-10-03 실기 스샷 실측 — 「힌트를 묻습니다」 8칸이 잘렸다): 넘는 줄은 고정 문구로, 남으면 손으로
  ③ 대사 26칸 초과: 넘는 줄의 «26칸 안 마지막 띄어쓰기»에 {n} — 그 페이지 줄 수가 원문 페이지보다 많아지면 손으로(보고만)
"""
import glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kocheck as K, normalize_ko as N

NARROW = 7
NARROW_FIX = [('{13}아이템을{n}가지고 있지 않습니다', '{13}아이템이{n}없습니다'),
              ('{13}아이템을 사용한다', '{13}아이템을{n}사용한다'),
              ('{13}잭에게{n}힌트를 묻습니다', '{13}잭에게{n}힌트를{n}묻습니다'),
              ('{n}더 이상은{n}늘어나지 않습니다', '{n}더 이상은{n}늘어나지{n}않습니다')]
# ★손 수정(2026-10-03): 자동 접기로는 한 낱말만 넘어가 원문보다 줄이 늘던 줄 — 원문과 같은 줄 수, 줄마다 26칸 이하
HAND = [
    ('자고 있었는데 눈을 떠 보니{n}이 꼴이구만.', '자고 있었는데{n}눈을 떠 보니 이 꼴이구만.'),
    ('{n}우리 팀에 남아서{n}잔챙이 상대로 느긋하게 현상금 사냥이나 하며 살자！',
     '{n}우리 팀에 남아서 잔챙이 상대로{n}느긋하게 현상금 사냥이나 하며 살자！'),
    ('우리 말고 살아남은 건{n}종신형인 {6:42} 한 명뿐이다. 나머지는 전원 {6:3}에게{n}살해당했다. {6:45}도 파괴돼서 연락이{n}닿지 않았다.',
     '우리 말고 살아남은 건 종신형인{n}{6:42} 한 명뿐이다. 나머지는 전원 {6:3}에게{n}살해당했다. {6:45}도 파괴돼서 연락이{n}닿지 않았다.'),
    ('배지를 갖고 있으면 동료 쪽에서 먼저 말을 걸어올 거다', '배지를 갖고 있으면 동료가 먼저 말을 걸 거다'),
    ('대체 이 섬에서는 무슨 일이 벌어지고 있는 거야…', '대체 이 섬에서 무슨 일이 벌어지는 거야…'),
    ('이 섬의 사람들을 모조리 먹어 치우고 그 뒤에는…', '이 섬 사람들을 모조리 먹어 치우고 그 뒤엔…'),
    ('오늘은 면회가 허락되는 일 년에 한 번뿐인 날인데…', '오늘은 일 년에 한 번 면회가 허락되는 날인데…'),
    ('우리 임무는 허가 없는 자를 통과시키지 않는 것,', '우리 임무는 허가 없는 자를 막는 것,'),
    ('게다가 여자를 데리고 오다니 불경스럽기 짝이 없다', '게다가 여자를 데려오다니 불경하기 짝이 없다'),
    ('하지만 함부로 죽이는 것보단 낫다고 할 수 있겠지.', '하지만 함부로 죽이는 것보단 낫겠지.'),
    ('뭣이, 네놈이{6:2}・야 로구나', '뭣이, 네놈이 {6:2}・야로구나'),
    ('장하다{6:2}・야.', '장하다 {6:2}・야.'),
]


def split_line(seg, krn):
    """한 줄 문자열 → 26칸 안 마지막 공백에서 {n} 넣은 문자열(없으면 None)."""
    best = None
    for m in re.finditer(' ', seg):
        head = seg[:m.start()]
        if max(K.layout(head, krn, False)[0]) <= K.LIMIT:
            best = m.start()
    if best is None:
        return None
    return seg[:best] + '{n}' + seg[best + 1:]


def rewrap(words, n, krn, first=None):
    """낱말 목록 → 정확히 n 줄(각 줄 ≤ LIMIT), 줄 길이가 평균에서 벗어난 정도² 합 최소(고르게). 안 되면 None."""
    W = len(words)
    width = lambda a, b: max(K.layout(K.squeeze(' '.join(words[a:b])), krn, False)[0])
    INF = float('inf'); best = {(W, 0): (0, None)}
    avg = width(0, W) / n
    def f(i, k):
        if (i, k) in best:
            return best[(i, k)][0]
        if k == 0 or i == W:
            return INF
        res = (INF, None)
        lim = first if (i == 0 and first) else K.LIMIT    # 페이지 첫 줄은 화자 이름 자리만큼 짧다
        for j in range(i + 1, W + 1):
            w = width(i, j)
            if w > lim:
                break
            c = f(j, k - 1)
            if c < INF:
                c += (avg - w) ** 2              # 줄 길이를 서로 비슷하게(한도 차이로 첫 줄만 짧아지는 「아무것도 안 | 해도」 방지)
                res = min(res, (c, j))
        best[(i, k)] = res
        return res[0]
    if f(0, n) == INF:
        return None
    lines = []; i = 0; k = n
    while i < W:
        j = best[(i, k)][1]; lines.append(' '.join(words[i:j])); i = j; k -= 1
    return lines


def fix_long(t, krn, jp_lines=4):
    """★넘는 줄 «하나»를 두 줄로 고르게 나눈다(페이지 줄 수 ≤ max(4, 원문 페이지 줄 수)).
    페이지가 이미 꽉 차면 손으로(다음 줄과 합쳐 나누거나 페이지 전체 재배치는 문장 경계를 깨서 안 한다).
    (2026-10-03 한도 26→24 때 — 자동 접기가 「…울게 될{n}거다」처럼 낱말 하나만 떨어뜨렸다)"""
    parts = re.split(r'(\{2\}\{7\}|\{2\}|\{7\}|\{1\})', t)
    cap = max(4, jp_lines)
    w = lambda x: max(K.layout(K.squeeze(x), krn, False)[0])
    out = []
    for p in parts:
        if p and not re.fullmatch(r'\{2\}\{7\}|\{2\}|\{7\}|\{1\}', p):
            ls = p.split('{n}'); i = 0
            while i < len(ls):
                lim = K.FIRST if i == 0 else K.LIMIT
                if w(ls[i]) > lim:
                    q = rewrap(ls[i].split(), 2, krn, lim) if len(ls) < cap else None
                    if q:
                        ls[i:i + 1] = q; i += 2; continue
                i += 1
            p = '{n}'.join(ls)
        out.append(p)
    return ''.join(out)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    write = '--write' in sys.argv
    files = {p: N.rd(p) for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'text', 'darksavior_*.tsv')))}
    R = {r['ID']: r for rows in files.values() for r in rows}
    old = {r['ID']: r for r in N.rd(os.path.join(ROOT, 'work', 'text', 'backup_premerge', 'darksavior_sys.tsv'))}
    jpn = {int(i[4:]): r['원문'] for i, r in R.items() if i.startswith('sys:')}
    krn = {int(i[4:]): K.squeeze(r['번역'] or r['원문']) for i, r in R.items() if i.startswith('sys:')}
    log = []; manual = []
    for i, r in R.items():
        k0 = r['번역']; k = k0
        if i.startswith('sys:'):
            w0 = max(K.layout(r['원문'], jpn, True)[0])
            if max(K.layout(K.squeeze(k), krn, False)[0]) > w0 and old[i]['번역'] and \
                    max(K.layout(K.squeeze(old[i]['번역']), krn, False)[0]) <= max(w0, 2):
                k = old[i]['번역']
        else:
            for a, b in NARROW_FIX + HAND:
                k = k.replace(a, b)
            if k.startswith('{13}') and max(len(re.sub(r'\{[^}]*\}', 'X', x))
                                            for x in k[4:].split('{n}')) > NARROW:
                manual.append((i, k))
            if not k.startswith("{13}") and K.over(k, krn):
                k = fix_long(k, krn, max(K.layout(r["원문"], jpn, True)[1]))
                _, pj = K.layout(r['원문'], jpn, True)
                L, pk = K.layout(K.squeeze(k), krn, False)
                if K.over(k, krn) or len(pk) != len(pj) or any(a > b for a, b in zip(pk, pj)):
                    manual.append((i, k))
        if k != k0:
            log.append((i, k0, k)); r['번역'] = k
    print('바뀐 줄 %d · 손으로 볼 줄 %d' % (len(log), len(manual)))
    for i, k in manual:
        print('  ✋ %s  %s' % (i, k))
    with open(os.path.join(ROOT, 'work', 'text', 'fit_log.tsv'), 'w', encoding='utf-8') as fh:
        fh.write('ID\t전\t후\n')
        for x in log:
            fh.write('\t'.join(x) + '\n')
    if write:
        for p, rows in files.items():
            N.wr(p, rows)
        print('적용 완료')


if __name__ == '__main__':
    main()
