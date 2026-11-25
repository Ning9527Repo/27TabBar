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
        assert 'ngInvalidatePageFrames(after: 0.24)\n        selectedIndex = index' in tab
        assert 'if confirmed != selectedIndex { ngInvalidatePageFrames(after: 0.15) }' in tab
        assert 'ngUseHostPosition ? 0.06 : Self.pillDetail' in tab
        assert 'if ngUseHostPosition { return isDarkAppearance ? 0.08 : 0.10 }' in tab
        assert tab.count('config.blur.radius = 18') == 2
        assert 'selectionAnimator?.onFrameChanged?(frame)' in tab
        assert 'continuousUpdate && !ngInteractiveLens' in renderer
        assert 'framesInFlight < (ngInteractiveLens ? 1 : Self.maxFramesInFlight)' in renderer
        assert '1.0 / 30.0 - 0.001' in renderer and 'ngLastCapture = now' in renderer
        assert 'let onSnapshot = self.onSnapshot' in renderer
        assert surface.count('self.ngBackdropEpoch == epoch') == 2
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
                assert 'Author: Ning&valzevul\n' in control
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
