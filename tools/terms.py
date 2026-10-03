# -*- coding: utf-8 -*-
r"""이름·용어 표기 갈림 찾기 (2026-10-03)

  python tools/terms.py      → work/text/terms.tsv (용어, 줄 수, 표기별 줄 수, 예)
원문 가타카나 낱말(2자 이상, ー・ 포함)마다, 그 낱말이 든 줄의 번역에서
«가타카나를 대충 한글로 옮긴 꼴»과 가장 닮은 한글 낱말을 뽑아 표기별로 센다.
"""
import collections, difflib, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kocheck as K

KANA = {}
_T = ('ア아イ이ウ우エ에オ오カ카キ키ク쿠ケ케コ코サ사シ시ス스セ세ソ소タ타チ치ツ츠テ테ト토ナ나ニ니ヌ누ネ네ノ노'
      'ハ하ヒ히フ후ヘ헤ホ호マ마ミ미ム무メ메モ모ヤ야ユ유ヨ요ラ라リ리ル루レ레ロ로ワ와ヲ오ン은'
      'ガ가ギ기グ구ゲ게ゴ고ザ자ジ지ズ즈ゼ제ゾ조ダ다ヂ지ヅ즈デ데ド도バ바ビ비ブ부ベ베ボ보パ파ピ피プ푸ペ페ポ포'
      'ァ아ィ이ゥ우ェ에ォ오ャ야ュ유ョ요ッ읏ヴ부ー으')
for a, b in zip(_T[0::2], _T[1::2]):
    KANA[a] = b
TERM = re.compile(r'[ァ-ヴー・]{2,}')
WORD = re.compile(r'[가-힣A-Za-z0-9・ ]+')
PART = re.compile(r'(은|는|이|가|을|를|의|에게|에서|에|와|과|도|로|으로|란|라는|이라는|님|이다|야|아|여|한테|까지|부터|만)$')


def rough(t):
    return ''.join(KANA.get(c, '') for c in t if c != '・')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    R = K.load()
    occ = collections.defaultdict(list)
    for i, r in R.items():
        if not r['번역'].strip():
            continue
        for t in set(TERM.findall(r['원문'])):
            if t.strip('ー・'):
                occ[t].append(i)
    out = []
    for t, ids in occ.items():
        if len(ids) < 2:
            continue
        rt = rough(t)
        forms = collections.Counter(); ex = {}
        for i in ids:
            words = []
            for w in WORD.findall(K.TOK.sub(' ', R[i]['번역'])):
                for x in w.split():
                    x = PART.sub('', x) or x
                    words.append(x)
            if not words:
                continue
            best = max(words, key=lambda w: difflib.SequenceMatcher(None, w, rt).ratio())
            if difflib.SequenceMatcher(None, best, rt).ratio() < 0.34:
                best = '?'
            forms[best] += 1; ex.setdefault(best, i)
        real = [f for f in forms if f != '?']
        if len(real) > 1:
            out.append((t, len(ids), forms, ex))
    out.sort(key=lambda x: -x[1])
    p = os.path.join(ROOT, 'work', 'text', 'terms.tsv')
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write('용어\t줄\t표기(줄 수)\t예\n')
        for t, n, forms, ex in out:
            fh.write('%s\t%d\t%s\t%s\n' % (t, n, ' / '.join('%s(%d)' % kv for kv in forms.most_common()),
                                           ' '.join('%s=%s' % (f, ex[f]) for f in forms if f != '?')))
    print('표기가 갈린 용어 %d → %s' % (len(out), p))
    for t, n, forms, ex in out[:60]:
        print('%-14s %3d  %s' % (t, n, ' / '.join('%s(%d)' % kv for kv in forms.most_common(6))))


if __name__ == '__main__':
    main()
