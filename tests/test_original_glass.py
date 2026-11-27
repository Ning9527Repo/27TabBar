#!/usr/bin/env python3
"""Verify restored optics against pinned Theseus, not synthetic appearance models."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from stage import stage, VENDOR, verify_vendor
from test_replacement import method


def main():
    verify_vendor()
    with tempfile.TemporaryDirectory(prefix='original-glass-') as temp:
        dst = Path(temp)
        stage(dst)
        upstream = next(VENDOR.rglob('TheseusTabBar.swift')).read_text()
        tab = (dst / 'TheseusTabBar.swift').read_text()
        exact = ('applyLensMaterial(', 'setLensFill(', 'setLensRefraction(',
                 'setLensItemProgress(', 'showCaptureTint(', 'drawLensItems(',
                 'followFinger(', 'setBarLifted(', 'applyBarLift(',
                 'applyBarTransform(', 'applyBarBodyGain(', 'startLensStretch(',
                 'stopLensStretch(', 'setLensStretch(', 'startLensActivity(',
                 'stopLensActivity(')
        for name in exact:
            assert method(tab, name) == method(upstream, name), name
        show = method(tab, 'showTheseus(').replace(
            '(ngUseHostPosition ? min(pillLocal.width, pillLocal.height) : pillLocal.height) / 2',
            'pillLocal.height / 2')
        assert show == method(upstream, 'showTheseus(')
        setup = method(tab, 'setupTheseus(').replace(
            '        if let bar = ngExcludedBar { glassView.setCaptureExcludedViews([bar]) }\n', '')
        assert setup == method(upstream, 'setupTheseus(')
        end = 'private final class LensMorphAnimator'
        begin = 'private final class SelectionAnimator'
        assert tab[tab.index(begin):tab.index(end)] == upstream[upstream.index(begin):upstream.index(end)]
        for name in ('TheseusLensMaterial.swift', 'LensMorph.swift', 'NativeLens26.swift',
                     'TheseusConfiguration.swift', 'VisualEffectFallback.swift'):
            original = next(VENDOR.rglob(name))
            assert (dst / name).read_bytes() == original.read_bytes(), name
        generated = '\n'.join(p.read_text() for p in dst.glob('*.swift'))
        for unwanted in ('ngCapsuleBackdrop', 'solidBackdrop', 'drawSoftbox',
                         'neutralGlassColor', 'ngSolidSelection', 'ngHostedPlatter'):
            assert unwanted not in generated, unwanted
        for name in ('BackgroundCaptureDraw.swift', 'ViewLayerCapture.swift'):
            capture = (dst / name).read_text()
            assert capture.count('sourceView.layer.render(in: ctx)') == 1
            assert 'solidBackdrop' not in capture
        shader = next(VENDOR.rglob('TheseusShaders.metal'))
        print(json.dumps({'original_optics_methods': len(exact),
                          'original_show_setup_selection_spring': True,
                          'synthetic_backdrops_in_build': False,
                          'shader_sha256': hashlib.sha256(shader.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
