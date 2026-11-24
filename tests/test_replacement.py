#!/usr/bin/env python3
"""Run real Bridge state logic against Foundation view stand-ins, not UIKit."""
import re,sys,subprocess,tempfile,json,plistlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from stage import stage

def method(text,name):
    start=text.index('    private func '+name)
    brace=text.index('{',start);depth=1;i=brace+1
    while depth:
        depth += (text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i].replace('private func','func',1)

def main():
    with tempfile.TemporaryDirectory(prefix='own-replacement-') as d:
        d=Path(d);sources=d/'staged';stage(sources)
        bridge=(ROOT/'Sources/Bridge.swift').read_text().replace('import UIKit','').replace('import QuartzCore','')
        bridge=re.sub(r'@objc(?:\([^)]*\))?\s*','',bridge).replace('@MainActor ','')
        tab=(sources/'TheseusTabBar.swift').read_text()
        geometry='''
struct TestCapsules {
    var ngUseHostPosition = true
    var usesIOS26Look = false
    var pillSize: CGSize { CGSize(width: 80, height: 53.5) }
    static let lensSize = CGSize(width: 96, height: 70)
    static let iOS26LensSize = CGSize(width: 90, height: 70)
'''+method(tab,'selectionFrame(for')+'\n'+method(tab,'glassFrame(for')+'\n}\n'
        tests='''
let win = UIWindow()
win.window = win
win.bounds = CGRect(x:0,y:0,width:430,height:932)
let parent = UIView()
parent.window = win
let bar = UITabBar()
bar.window = win
bar.frame = CGRect(x:0,y:849,width:430,height:83)
bar.bounds = CGRect(x:0,y:0,width:430,height:83)
bar.superview = parent
parent.subviews = [bar]
let items = (0..<4).map { _ in UITabBarItem() }
bar.items = items; bar.selectedItem = items[1]
bar.controls = (0..<4).map { _ in UIControl() }
SystemTabsBridge.update(bar)
guard let glass = parent.subviews.compactMap({$0 as? TheseusTabBar}).first else { fatalError("No replacement") }
let originalGlass = glass
let ownMask = bar.layer.mask
precondition(ownMask != nil && glass.prepared == 1 && glass.alpha == 1)
precondition(SystemTabsBridge.usesOverlay(bar))
// All transitions use the same production update path. No native style is revealed.
for alpha in [CGFloat(0.99),0.7,0.01,0,1] {
    bar.alpha=alpha; SystemTabsBridge.update(bar)
    precondition(bar.layer.mask === ownMask)
    precondition(parent.subviews.contains(where: {$0 === originalGlass}))
}
bar.controls=nil; SystemTabsBridge.update(bar); precondition(bar.layer.mask === ownMask)
bar.selectedItem=nil; SystemTabsBridge.update(bar); precondition(bar.layer.mask === ownMask)
bar.isHidden=true; SystemTabsBridge.update(bar);precondition(bar.layer.mask === ownMask && glass.isHidden)
bar.isHidden=false;bar.controls=(0..<4).map{_ in UIControl()};bar.selectedItem=items[2]
SystemTabsBridge.update(bar);precondition(!glass.isHidden && glass.selectedIndex==2)
// UIKit resets its model mask during layout: ownership gets restored.
bar.layer.mask=nil;SystemTabsBridge.update(bar);precondition(bar.layer.mask === ownMask)
bar.window=nil;SystemTabsBridge.update(bar);precondition(bar.layer.mask === ownMask && glass.isHidden)
bar.window=win;SystemTabsBridge.update(bar);precondition(bar.layer.mask === ownMask && !glass.isHidden)
// Pending Metal presentation does not expose the native bar.
precondition(SystemTabsBridge.usesOverlay(bar))
glass.ngGlassDidPresent?();precondition(bar.layer.mask === ownMask)
SystemTabsBridge.detach(bar);precondition(bar.layer.mask==nil)
var geometry=TestCapsules();var cases=0
for n in 2...5 {
 for width in stride(from:320.0,through:1024.0,by:4) {
    let slot=CGFloat((width-28-30)/Double(n));let frame=CGRect(x:15,y:0,width:slot,height:63)
    let pill=geometry.selectionFrame(for:frame);let lens=geometry.glassFrame(for:frame)
    precondition(pill.width>=80 && pill.width>=slot-4 && pill.height==53.5)
    precondition(lens.width>=pill.width+16 && lens.height==70)
    precondition(abs(pill.midX-frame.midX)<0.001 && abs(lens.midX-frame.midX)<0.001)
    cases += 1
 }
}
geometry.ngUseHostPosition=false
precondition(geometry.selectionFrame(for:CGRect(x:0,y:0,width:200,height:63)).width==80)
print("replacement_state_standin_ok capsule_cases=\\(cases)")
'''
        bundle=d/'Resources.bundle';bundle.mkdir();(bundle/'default.metallib').write_bytes(b'fixture')
        (bundle/'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'com.ning.tests.resources','CFBundlePackageType':'BNDL'}))
        source=d/'main.swift';source.write_text((ROOT/'tests/ReplacementStandins.swift').read_text()+'\n'+bridge+'\n'+geometry+'\n'+tests)
        out=d/'test'
        subprocess.run(['xcrun','swiftc','-swift-version','5',str(source),'-o',str(out)],check=True)
        subprocess.run([str(out),str(bundle)],check=True)
if __name__=='__main__':main()
