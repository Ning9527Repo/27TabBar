from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / 'fixtures' / '019_visual_methods.swift'
METHODS = ('setupTheseus', 'showTheseus', 'hideTheseus', 'placeLens',
           'updateSelectionViewFrame', 'updatePillShade')

def apply(source):
    legacy = FIXTURE.read_text()
    for name in METHODS:
        marker = f'    private func {name}('
        start = legacy.index(marker)
        depth = 0
        opened = False
        for end in range(start, len(legacy)):
            depth += (legacy[end] == '{') - (legacy[end] == '}')
            if legacy[end] == '{': opened = True
            if opened and depth == 0:
                break
        body = legacy[start:end + 1]
        current = source.index(marker)
        depth = 0
        opened = False
        for stop in range(current, len(source)):
            depth += (source[stop] == '{') - (source[stop] == '}')
            if source[stop] == '{': opened = True
            if opened and depth == 0:
                break
        source = source[:current] + body + source[stop + 1:]
    return source
