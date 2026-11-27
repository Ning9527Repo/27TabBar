#!/usr/bin/env python3
"""Exercise the production capsule-rim pixel coverage function."""
import shutil, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def extract(src, marker):
    start=src.index(marker); brace=src.index('{',start); depth=1; i=brace+1
    while depth:
        depth += (src[i]=='{')-(src[i]=='}'); i+=1
    return src[start:i]

with tempfile.TemporaryDirectory(prefix='platter-edge-') as td:
    d=Path(td); stage=d/'staged'
    subprocess.run(['python3',str(ROOT/'tools/stage.py'),str(stage)],check=True)
    tab=(stage/'TheseusTabBar.swift').read_text()
    method=extract(tab,'    static func ngRimCoverage(').replace('static func ngRimCoverage','static func coverage')
    src='''import Foundation
enum Coverage {
'''+method+'''
}
let axes: [(CGFloat,CGFloat)] = [(1,0),(-1,0),(0,1),(0,-1)]
let diagonal: CGFloat = 1 / CGFloat(2).squareRoot()
let diagonals: [(CGFloat,CGFloat)] = [(diagonal,diagonal),(-diagonal,diagonal),(diagonal,-diagonal),(-diagonal,-diagonal)]
func coverage(_ d: CGFloat, _ n: (CGFloat, CGFloat)) -> CGFloat {
    Coverage.coverage(d, normalX: n.0, normalY: n.1)
}
for n in axes {
    precondition(abs(coverage(0, n) - 0.5) < 1e-9)
    precondition(coverage(-0.5, n) == 1 && coverage(0.5, n) == 0)
}
for n in diagonals {
    precondition(abs(coverage(0, n) - 0.5) < 1e-9)
    precondition(abs(coverage(diagonal / 2, n) - 0.125) < 1e-9)
    precondition(coverage(-0.8, n) == 1 && coverage(0.8, n) == 0)
}
for x in 1...64 {
    let d = CGFloat(x) / 128
    for n in axes + diagonals {
        let inside = coverage(-d, n), outside = coverage(d, n)
        precondition(inside >= 0.5 && inside <= 1 && outside >= 0 && outside <= 0.5)
        precondition(abs(inside + outside - 1) < 1e-8)
        let near = coverage(d - 1, n), far = coverage(d - 2, n)
        precondition(far >= near && near >= outside)
    }
}
print("capsule_rim_coverage_ok axis=4 diagonal=4 samples=512")
'''
    f=d/'test.swift';f.write_text(src);out=d/'test'
    compiler=['xcrun','swiftc'] if shutil.which('xcrun') else ['swiftc']
    subprocess.run([*compiler,'-swift-version','5',str(f),'-o',str(out)],check=True)
    subprocess.run([str(out)],check=True)
