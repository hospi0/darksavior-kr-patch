# -*- coding: utf-8 -*-
r"""다크 세이비어 원본 디스크 — 파일 목록·읽기, work/disc/ 에 «불변 사본» 꺼내기 (2026-10-03)
  트랙 1 MODE1/2352, 루트 + D_SAVIOR/ (PROGRAM.000‥535) + DS_CDDA/.
  python tools/disc.py            → 필요한 파일을 work/disc/ 로 (이미 있으면 md5 대조만)
"""
import hashlib, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.append(r'C:\claude\project\anearth-kr-patch\tools')      # cdmode1 (iso.py 가 씀)
import iso

SRC_DIR = r'C:\claude\roms\ss\완료\Dark Savior (Japan)'          # 2026-10-03 사용자가 완료 폴더로 옮김
TRACK1 = os.path.join(SRC_DIR, 'Dark Savior (Japan) (Track 1).bin')
TRACK1_MD5 = 'f2d871c8afa6defb4456e83807f4de07'
DISC = os.path.join(ROOT, 'work', 'disc')
# 한글화에 쓰는 파일: 004 = 글꼴·조판·시스템 문장·허프만 트리(0x00292000 적재) / 507·508·509·517 = 대사(0x002C0000 적재)
WANT = ['D_SAVIOR/PROGRAM.004', 'D_SAVIOR/PROGRAM.507', 'D_SAVIOR/PROGRAM.508', 'D_SAVIOR/PROGRAM.509', 'D_SAVIOR/PROGRAM.517', 'D_SAVIOR/PROGRAM.506', 'D_SAVIOR/PROGRAM.439']


def listing():
    with open(TRACK1, 'rb') as fh:
        return iso.tree(fh)


def read(name):
    with open(TRACK1, 'rb') as fh:
        l, s, _, _ = iso.tree(fh)[name]
        return iso.read_user(fh, l, (s + 2047) // 2048)[:s]


def local(name):
    """work/disc/ 의 불변 사본 (경로의 / 는 _ 로)"""
    return open(os.path.join(DISC, name.replace('/', '_')), 'rb').read()


def main():
    os.makedirs(DISC, exist_ok=True)
    for nm in WANT:
        p = os.path.join(DISC, nm.replace('/', '_'))
        d = read(nm)
        if os.path.exists(p):
            assert open(p, 'rb').read() == d, ('⛔work/disc 사본이 원본과 다르다', nm)
            print('  같음', nm, len(d))
        else:
            open(p, 'wb').write(d); print('  꺼냄', nm, len(d), hashlib.md5(d).hexdigest())


if __name__ == '__main__':
    main()
