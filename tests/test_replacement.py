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
    var backgroundView = UIView()
    var barContentInset: CGFloat { usesIOS26Look ? 10.25 : 15 }
    var pillSize: CGSize { CGSize(width: usesIOS26Look ? 74 : 80, height: 53.5) }
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
items[0].accessibilityLabel = "个人收藏"
items[1].title = "游戏"
items[2].title = "  "
items[3].title = "搜索"
bar.items = items; bar.selectedItem = items[1]
bar.controls = (0..<4).map { _ in UIControl() }
bar.controls?[2].nativeTitle = "  App  "
let existingImage = UIImage()
bar.controls?[2].nativeImage = existingImage
SystemTabsBridge.update(bar)
guard let glass = parent.subviews.compactMap({$0 as? TheseusTabBar}).first else { fatalError("No replacement") }
let originalGlass = glass
let ownMask = bar.layer.mask
precondition(ownMask != nil && glass.prepared == 1 && glass.alpha == 1)
precondition(SystemTabsBridge.usesOverlay(bar))
precondition(glass.items[1].title == "游戏" && glass.items[2].title == "App")
precondition(NGTabPresentation.title(nil, "  ", "最近项目") == "最近项目")
precondition(NGTabPresentation.shortLabel("  最近项目  ") == "最近项目")
precondition(NGTabPresentation.shortLabel("最近项目，标签，已选中") == nil)
precondition(glass.items[0].title == "个人收藏" && glass.items[2].icon === existingImage)
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
precondition(glass.items[2].title == "App" && glass.items[2].icon === existingImage)
// UIKit resets its model mask during layout: ownership gets restored.
bar.layer.mask=nil;SystemTabsBridge.update(bar);precondition(bar.layer.mask === ownMask)
bar.window=nil;SystemTabsBridge.update(bar);precondition(bar.layer.mask === ownMask && glass.isHidden)
bar.window=win;SystemTabsBridge.update(bar);precondition(bar.layer.mask === ownMask && !glass.isHidden)
// Pending Metal presentation does not expose the native bar.
precondition(SystemTabsBridge.usesOverlay(bar))
glass.ngGlassDidPresent?();precondition(bar.layer.mask === ownMask)
func drainMain() {
    RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.004))
}
for target in [0,3,1,3,3,0,2,1] {
    let before = nativeActivations
    precondition(glass.ngActivateNative?(target) == target)
    precondition(nativeActivations == before + 1 && bar.selectedItem === items[target])
    precondition(glass.ngActivateNative?(target) == nil && nativeActivations == before + 1)
    drainMain()
    precondition(glass.selectedIndex == target && bar.layer.mask === ownMask)
}
nativeAllowsSelection = false
precondition(glass.ngActivateNative?(0) == 1)
drainMain()
precondition(glass.selectedIndex == 1)
items[0].isEnabled = false
let beforeDisabled = nativeActivations
precondition(glass.ngActivateNative?(0) == nil && nativeActivations == beforeDisabled)
drainMain()
SystemTabsBridge.detach(bar);precondition(bar.layer.mask==nil)
// Drive the actual gesture gate with overlapping recognizer lifetimes.
let press = NSObject(), pan = NSObject()
let pressID = ObjectIdentifier(press), panID = ObjectIdentifier(pan)
var motion = NGTabInteractionGate()
for _ in 0..<100 {
    precondition(motion.begin(pressID))
    precondition(!motion.begin(panID) && !motion.accepts(panID) && !motion.end(panID))
    precondition(motion.accepts(pressID) && motion.end(pressID) && !motion.end(pressID))
    precondition(motion.begin(panID) && motion.accepts(panID))
    motion.clear()
    precondition(!motion.end(panID) && !motion.accepts(panID))
}
// The endpoint is recovered from what is displayed, not the raw drawable size.
let lensBounds = CGRect(x:0,y:0,width:120,height:76)
let visible = CGRect(x:40,y:10,width:60,height:38)
precondition(NGTabPresentation.visibleLens(frame: visible, bounds: lensBounds, inset: CGSize(width:4,height:2))
             == CGRect(x:42,y:11,width:56,height:36))
precondition(NGTabPresentation.visibleLens(frame: visible, bounds: lensBounds, inset: CGSize(width:-2,height:-4))
             == CGRect(x:39,y:8,width:62,height:42))
precondition(NGTabPresentation.visibleLens(frame: visible, bounds: .zero, inset: .zero) == nil)
precondition(NGTabPresentation.visibleLens(frame: .null, bounds: lensBounds, inset: .zero) == nil)
precondition(NGTabPresentation.visibleLens(frame: visible, bounds: lensBounds, inset: CGSize(width:60,height:0)) == nil)
var geometry=TestCapsules();var cases=0
for ios26 in [false,true] {
 geometry.usesIOS26Look = ios26
 for n in 2...5 {
  for width in stride(from:260.0,through:1024.0,by:4) {
    let platter = CGRect(x: ios26 ? 0 : 1.0/3, y: ios26 ? 0.5 : -1.0/6,
                         width: CGFloat(width-28) - (ios26 ? 0 : 2.0/3), height: ios26 ? 62 : 63+1.0/3)
    let strip = NGTabPresentation.slotStrip(platter: platter)
    let slot = strip.width / CGFloat(n)
    for rtl in [false,true] {
      var frames: [CGRect] = []
      for logical in 0..<n {
        let physical = rtl ? n-1-logical : logical
        let frame = CGRect(x: strip.minX+CGFloat(physical)*slot,y:strip.minY,width:slot,height:strip.height)
        let pill = geometry.selectionFrame(for:frame); let lens = geometry.glassFrame(for:frame)
        precondition(abs(pill.minY-platter.minY-4)<0.001 && abs(platter.maxY-pill.maxY-4)<0.001)
        precondition(platter.contains(pill) && abs(pill.width-slot+4)<0.001)
        precondition(abs(pill.midX-frame.midX)<0.001 && abs(pill.midY-frame.midY)<0.001)
        if physical == 0 { precondition(abs(pill.minX-platter.minX-4)<0.001) }
        if physical == n-1 { precondition(abs(platter.maxX-pill.maxX-4)<0.001) }
        precondition(abs(lens.width-pill.width-16)<0.001 && lens.height == 70 && abs(lens.midX-pill.midX)<0.001)
        frames.append(pill)
        cases += 1
      }
      let ordered = frames.sorted { $0.minX < $1.minX }
      for (lhs,rhs) in zip(ordered,ordered.dropFirst()) {
        precondition(abs(rhs.minX-lhs.maxX-4)<0.001 && abs(rhs.width-lhs.width)<0.001)
      }
    }
  }
 }
}
geometry.ngUseHostPosition=false; geometry.usesIOS26Look=false
precondition(geometry.selectionFrame(for:CGRect(x:0,y:0,width:200,height:63)).width==80)
print("replacement_state_standin_ok capsule_cases=\\(cases)")
'''
        bundle=d/'Resources.bundle';bundle.mkdir();(bundle/'default.metallib').write_bytes(b'fixture')
        (bundle/'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'com.ning.tests.resources','CFBundlePackageType':'BNDL'}))
        source=d/'main.swift';source.write_text((ROOT/'tests/ReplacementStandins.swift').read_text()+'\n'+(ROOT/'Sources/TabPresentation.swift').read_text()+'\n'+bridge+'\n'+geometry+'\n'+tests)
        out=d/'test'
        subprocess.run(['xcrun','swiftc','-swift-version','5',str(source),'-o',str(out)],check=True)
        subprocess.run([str(out),str(bundle)],check=True)
if __name__=='__main__':main()
