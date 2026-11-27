#!/usr/bin/env python3
"""Offline checks. This is not an iOS runtime/visual test."""
import ast
import gzip
import hashlib
import io
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from stage import stage, verify_vendor
from build import make_deb, PKG, VERSION, verify_tar_layout


def check():
    verify_vendor()
    for file in [*ROOT.glob('tools/*.py'), *ROOT.glob('tests/*.py')]:
        ast.parse(file.read_text(), filename=str(file))
    shader = ROOT/'Vendor/Theseus/Sources/Theseus/Shaders/TheseusShaders.metal'
    original = shader.read_bytes()
    expected_shader = json.loads((ROOT/'Vendor/manifest.json').read_text())['files']['Sources/Theseus/Shaders/TheseusShaders.metal']
    assert hashlib.sha256(original).hexdigest() == expected_shader
    with tempfile.TemporaryDirectory(prefix='systemtabs-source-') as temp:
        temp = Path(temp)
        geometry = temp/'test-native-geometry'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
            str(ROOT/'tests/test_native_geometry.c'),'-lm','-o',str(geometry)], check=True)
        subprocess.run([str(geometry)], check=True)
        a, b = temp/'a', temp/'b'
        stage(a)
        stage(b)
        assert len(list(a.glob('*.swift'))) == 33
        for file in a.glob('*.swift'):
            assert file.read_bytes() == (b/file.name).read_bytes()
        # Malformed/rebased input must not silently produce a partial adapter.
        import stage as adapter
        try:
            adapter.tabbar('changed upstream file')
        except SystemExit:
            pass
        else:
            raise AssertionError('Missing upstream anchors accepted')
        changed = {p.name for p in a.glob('*.swift') if p.read_bytes() != next((ROOT/'Vendor/Theseus/Sources').rglob(p.name)).read_bytes()}
        assert changed == {'TheseusTabBar.swift','TheseusRenderer.swift','TheseusView.swift','CaptureCompensation.swift','BackgroundCaptureDraw.swift','ViewLayerCapture.swift','VisualEffectFallback.swift'}
        tab = (a/'TheseusTabBar.swift').read_text()
        renderer = (a/'TheseusRenderer.swift').read_text()
        surface = (a/'TheseusView.swift').read_text()
        upstream_tab = next((ROOT/'Vendor/Theseus/Sources').rglob('TheseusTabBar.swift')).read_text()
        assert 'if confirmed != selectedIndex { ngInvalidatePageFrames() }' in tab
        assert tab.count('selectionView.ngEnableSolidSelection()') == 1
        assert 'selectionView.ngInvalidateBackdrop' not in tab
        assert 'if !ngUseHostPosition { selectionView.sourceView = source }' in tab
        assert 'if !self.ngUseHostPosition, self.selectionView.sourceView == nil {' in tab
        solid = surface.split('    func ngEnableSolidSelection() {', 1)[1].split('    var ngNonblockingRendering', 1)[0]
        for invariant in ('renderer = nil', 'providesCaptureSnapshot = false', 'sourceView = nil',
                          'fallbackView?.isHidden = true', 'metalLayerView?.isHidden = true',
                          'UIColor(white: tone, alpha: 1)', 'backgroundColor = fill', 'layer.cornerRadius = shape.cornerRadius'):
            assert invariant in solid, invariant
        for method in ('setupRenderer()', 'updateRenderingMode()', 'ngPrepareReplacement()',
                       'ngRefreshPlatter(crossfade: Bool, onReveal: ((Bool) -> Void)? = nil) -> Bool'):
            guard = 'return false' if method.startswith('ngRefreshPlatter') else 'return'
            assert method + ' {\n        guard !ngSolidSelection else { ' + guard + ' }' in surface
        assert 'NGTabPresentation.slotStrip(platter: backgroundView.frame)' in tab
        assert 'NGTabPresentation.capsule(slot: itemFrame)' in tab
        def section(text, marker, end):
            start = text.index(marker)
            return text[start:text.index(end, start)]
        for marker, end in [('    private let selectionView:', '    /// Native iOS 27 pill'),
                            ('        var config = TheseusConfiguration.lens', '        let glassView = TheseusView(configuration: config)')]:
            assert section(tab, marker, end) == section(upstream_tab, marker, end), marker
        hosted = section(tab, '    private func ngInstallHostedChrome()', '    private func ngPlaceHostedPill(')
        assert 'UIVisualEffectView(effect: UIBlurEffect(style: .systemChromeMaterialLight))' in tab
        assert 'ngHostedPlatter.overrideUserInterfaceStyle = .light' in hosted
        assert 'backgroundGlassView.removeFromSuperview()' in hosted
        assert 'ngHostedPlatter' in tab and 'ngFrostedPlatter = ngUseHostPosition' not in tab
        assert 'private func ngBeginHostedDrag(at x: CGFloat)' in tab
        assert 'private func ngMoveHostedDrag(to x: CGFloat)' in tab
        assert 'private func ngFinishHostedDrag(at x: CGFloat)' in tab
        assert 'private func ngCancelHostedDrag(restore: Bool = true)' in tab
        assert 'selectionView.layer.borderWidth = 0' in tab
        assert 'selectionView.layer.borderColor = nil' in tab
        assert 'guard !ngUseHostPosition else { return }' in section(tab, '    private func setBarLifted(', '    private func applyBarLift(')
        assert 'ngHostedPlatter.frame = bodyFrame' in tab
        assert 'ngHostedPlatter.frame' in tab and 'ngHostedPlatter.effect' not in tab
        assert 'applyItemTints(selectedAt: selectedIndex, animated: animate)' in hosted
        assert 'ngTap.require(toFail: pressGesture)' in tab and 'ngTap.require(toFail: panGesture)' in tab
        assert tab.count('if ngUseHostPosition && !ngAcceptGesture(gesture) { return }') == 2
        assert 'ngGestureGate.clear()' in tab
        shrink = section(tab, '    private func hideTheseus()', '    /// Places the lens without resizing')
        assert shrink.index('let shown =') < shrink.index('stopLensStretch()')
        assert 'releaseFrame = shown' in shrink and 'animationBase = base' in shrink
        assert 'LensMorph.transform(mapping: animationBase, onto: frame)' in shrink
        assert 'self.selectionView.alpha = share' not in shrink
        assert 'selectionView.alpha = 1' in shrink and 'self.ngSyncDragPill(glassView)' in shrink
        assert 'glassView.alpha = 1 - share' in shrink
        setup = section(tab, '    private func setupTheseus()', '    private func showTheseus()')
        assert 'glassView.ngHostedDragLens = ngUseHostPosition' in setup
        assert 'glassView.setCaptureExcludedViews([backgroundView, selectionView, itemsContainerView, captureTwinRow].compactMap { $0 })' in setup
        assert 'if ngUseHostPosition { ngBeginHostedDrag(at: location.x); return }' not in tab
        assert 'if ngUseHostPosition { ngMoveHostedDrag(to: convert(location, to: contentView).x); return }' not in tab
        assert 'if ngUseHostPosition { ngFinishHostedDrag(at: convert(CGPoint(x: rawX, y: 0), to: contentView).x); return }' not in tab
        # Hosted long-press keeps the original real Theseus grow/follow/shrink path.
        assert 'private func beginInteraction(at location:' in tab
        assert 'showTheseus()' in tab and 'hideTheseus()' in tab
        assert 'animator.morph(from: startFrame, to: growthTarget' in section(tab, '    private func showTheseus()', '    private func hideTheseus()')
        assert 'glassView.ngHostedDragLens = ngUseHostPosition' in setup
        assert 'ngMakeLensBackdrop(236)' in renderer and 'ngMakeLensBackdrop(65)' in renderer
        assert 'width: 1, height: 1' in renderer
        assert 'config.edgeFeather = ngUseHostPosition ? 1.0 : TheseusTabBar.pillFeather' in setup
        assert 'ngBeginHostedDrag(at: location.x)' not in tab
        assert 'ngMoveHostedDrag(to: convert(location, to: contentView).x)' not in tab
        assert 'ngFinishHostedDrag(at: convert(CGPoint(x: rawX, y: 0), to: contentView).x)' not in tab
        assert '!isShuttingDown, !ngBackdropHeld' in renderer
        fast = section(renderer, '    private func ngRenderHostedLens(', '    // CAMetalLayer acquisition')
        assert 'originalSourceTexture: plate' in fast and 'itemTexture: items' in fast
        assert 'encodeBlurPass(' not in fast and 'captureTexture(' not in fast
        assert 'fixedSize: size' in fast and 'guard encodeRefractionCompositePass' in fast
        assert 'func ngTrackedLensFrame' in tab and 'frame.midX - converted.midX' in tab
        render = section(renderer, '    private func performRender(', '    /// A glass with a lens chain')
        assert render.index('if ngHostedDragLens {') < render.index('NGSystemTabCaptureBegin()')
        assert '0xff000000' in renderer and 'if ngHostedDragLens && shouldUseFallback' in surface
        assert 'direct: ngUseHostPosition' in tab
        assert 'if direct, ngDragCenter.update(x)' in tab and 'centerX = frame.midX' in tab
        assert 'transform.m41 += containerFrame.midX - current.midX' in tab
        assert 'if glassView.bounds != bounds { glassView.bounds = bounds }' in tab
        assert 'metalLayer?.presentsWithTransaction = continuousUpdate && !ngNonblockingRendering' in renderer
        assert 'ngDrawableQueue.async' in renderer and 'self.ngDrawableEpoch == epoch' in renderer
        assert 'ngNonblockingRendering ? ngTakeDrawable(metalLayer) : metalLayer.nextDrawable()' in renderer
        assert renderer.count('limitCompensation: ngNonblockingRendering') == 2
        assert 'if ngNonblockingRendering {\n            ngDrawableEpoch &+= 1\n            ngReadyDrawable = nil\n        } else {\n            waitForGPUCompletion()' in renderer
        assert 'commandBuffer.addCompletedHandler { _ in recycle() }' in renderer
        assert 'let renderScale = currentRefractionQuality.renderScale' in renderer
        assert 'let onSnapshot = self.onSnapshot' in renderer
        assert surface.count('self.ngBackdropEpoch == epoch') == 2
        ordinary = section(tab, '    private func ngInvalidatePageFrames()', '    private var ngRefreshingItems')
        assert 'ngRefreshPlatter(crossfade: false)' in ordinary
        refresh = section(surface, '    func ngRefreshPlatter(', '    func ngPrepareReplacement()')
        assert 'ngSwitchCover' not in surface and 'metal.alpha' not in refresh
        assert 'if crossfade, ngPresented, !isUsingFallback' in refresh
        assert 'ngAppearanceGate.accept(ticket)' in refresh
        assert 'ngAppearanceGate.prepare(dark: dark)' in refresh
        assert 'fade.fromValue = visibleOpacity' in refresh and 'ngAppearanceImage.opacity = shownOpacity' in refresh
        timeout = section(surface, '    private func ngCheckPlatterAppearance(', '    private func ngFinishPlatterAppearance(')
        assert 'self.ngPrepareReplacement()' in timeout and 'self.ngClearPlatterAppearance()' in timeout
        assert 'ngFinishPlatterAppearance(' not in timeout and 'reveal?(true)' not in timeout
        assert 'ngPlatterBecameActive' in surface and '!self.ngBackdropHeld' in timeout
        assert 'visiblePresent(ticket)' in renderer and 'ticket.dark == (hostView.traitCollection.userInterfaceStyle == .dark)' in renderer
        assert 'adaptDarkWeight = target' in tab and 'adaptDarkTarget = target' in tab
        assert 'reveal?(true)' in refresh and 'if notify { reveal?(false) }' in refresh
        assert 'self?.ngFinishHostedPalette(animated: animated)' in tab
        assert 'drawable.addPresentedHandler' in renderer and 'shown.presentedTime > 0' in renderer
        bridge = (ROOT/'Sources/Bridge.swift').read_text()
        style = section(bridge, '    private func syncAppearance(', '    func preserveReplacement(')
        assert 'let style = bar.overrideUserInterfaceStyle' in style and 'traitCollection' not in style
        assert 'fade.fromValue = previous' in solid and 'fade.toValue = fill.cgColor' in solid
        assert 'captureSnapshot = nil\n        captureSnapshotOverride = nil' in surface
        assert 'metalLayerView?.alpha = 0' in surface and 'metalLayerView?.alpha = 1' in surface
        # Exercise real ar/tar writer with explicit fixture bytes for both path variants.
        # These fixture archives are never copied to dist or presented as installable.
        for arch in ('arm64','arm64e'):
            deb, expected = make_deb(b'fixture-dylib-not-executable', b'fixture-metal-not-executable', arch)
            assert deb.startswith(b'!<arch>\n')
            pos, members = 8, {}
            while pos < len(deb):
                header = deb[pos:pos+60]
                assert header[58:] == b'`\n'
                name = header[:16].decode().strip().removesuffix('/')
                length = int(header[48:58])
                members[name] = deb[pos+60:pos+60+length]
                pos += 60+length+(length&1)
            assert pos == len(deb) and members['debian-binary'] == b'2.0\n'
            with tarfile.open(fileobj=io.BytesIO(members['control.tar.gz']), mode='r:gz') as tar:
                control = tar.extractfile('./control').read().decode()
                assert f'Package: {PKG}\n' in control and f'Version: {VERSION}\n' in control
                assert f'Architecture: iphoneos-{arch}\n' in control
                assert 'Name: 27TabBar\n' in control
                assert 'Author: Ning\n' in control and 'Maintainer: Ning\n' in control
            with tarfile.open(fileobj=io.BytesIO(members['data.tar.gz']), mode='r:gz') as tar:
                verify_tar_layout(tar.getmembers(), expected)
                files = {x.name[2:]:tar.extractfile(x).read() for x in tar if x.isfile()}
                assert files == {name:data for name,(data,mode) in expected.items()}
                assert all(name.startswith('var/jb/') == (arch == 'arm64') for name in files)
                pl = next(data for name,data in files.items() if name.endswith('SystemTabs.plist'))
                assert plistlib.loads(pl) == {'Filter':{'Bundles':['com.apple.UIKit']}}
            path = temp/f'fixture-{arch}.deb'
            path.write_bytes(deb)
            if sys.platform == 'linux':
                subprocess.run(['dpkg-deb','--info',str(path)],check=True,stdout=subprocess.DEVNULL)
                subprocess.run(['dpkg-deb','--extract',str(path),str(temp/arch)],check=True,stdout=subprocess.DEVNULL)
                install = temp/(arch+'-install')
                admin = temp/(arch+'-db')
                install.mkdir()
                admin.mkdir()
                (admin/'status').write_text('')
                result = subprocess.run(['dpkg','--root='+str(install),'--admindir='+str(admin),
                    '--force-architecture','--no-triggers','--unpack',str(path)],
                    text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                assert result.returncode == 0, result.stdout
                for name, data in files.items():
                    assert (install/name).read_bytes() == data
    workflow = (ROOT/'.github/workflows/build.yml').read_text()
    assert 'workflow_dispatch:' in workflow and '  push:' not in workflow and '  pull_request:' not in workflow
    print(json.dumps({'vendor_files':37,'staged_swift':33,'shader_sha256':hashlib.sha256(original).hexdigest(),
                      'deterministic_adapter':True,'both_package_path_fixtures':True,'manual_workflow':True}))


if __name__ == '__main__':
    check()
