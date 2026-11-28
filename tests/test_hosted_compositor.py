#!/usr/bin/env python3
"""Execute extracted production hosted-gesture functions with Foundation stand-ins.
Not a UIKit or device visual test. The animator exposes intermediate ticks.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from stage import stage
from test_replacement import method

STANDINS = r'''
import Foundation
import CoreGraphics
struct TestShape { var cornerRadius: CGFloat = 0 }
final class TestLayer {
    var frame = CGRect.zero
    var cornerRadius: CGFloat = 0
    func presentation() -> TestLayer? { nil }
    func removeAnimation(forKey: String) {}
}
final class TestView {
    var bounds = CGRect.zero
    var center = CGPoint.zero
    var shape = TestShape()
    let layer = TestLayer()
    var frame: CGRect { CGRect(x:center.x-bounds.width/2,y:center.y-bounds.height/2,width:bounds.width,height:bounds.height) }
}
enum CATransaction {
    static func begin() {}
    static func commit() {}
    static func setDisableActions(_ value: Bool) {}
}
enum UIAccessibility { static var isReduceMotionEnabled = false }
final class LensMorphAnimator {
    var isRunning = false
    var start = CGRect.zero
    var target = CGRect.zero
    var onTick: ((CGRect, CGFloat) -> Void)?
    var onComplete: (() -> Void)?
    func morph(from: CGRect, to: CGRect, spring: Int,
               onTick: @escaping (CGRect, CGFloat) -> Void, onComplete: @escaping () -> Void) {
        cancel(); start=from; target=to; self.onTick=onTick; self.onComplete=onComplete; isRunning=true
        tick(0)
    }
    func tick(_ t: CGFloat) {
        guard isRunning else { return }
        let r=CGRect(x:start.minX+(target.minX-start.minX)*t, y:start.minY+(target.minY-start.minY)*t,
                     width:start.width+(target.width-start.width)*t, height:start.height+(target.height-start.height)*t)
        onTick?(r,t)
        if t >= 1 { let done=onComplete; cancel(); done?() }
    }
    func cancel() { isRunning=false; onTick=nil; onComplete=nil }
}
struct TestItem { var ngEnabled = true }
final class TestHosted {
    let selectionView = TestView()
    var isDragging=false, isCollapsingLens=false, isCommittingDrag=false, isUserInteractionEnabled=true
    var selectedIndex=0
    var items=Array(repeating:TestItem(),count:4)
    var slotFrames=(0..<4).map { CGRect(x:CGFloat($0)*100,y:0,width:100,height:63) }
    var ngHostedDragTarget=CGRect.zero
    var ngHostedPressX: CGFloat=0
    var ngHostedDirectDrag=false
    var fingerAnchorOffset: CGFloat=0
    var ngGestureGate=NGTabInteractionGate()
    var lensMorphAnimator: LensMorphAnimator?
    var ngActivateNative: ((Int) -> Int?)?
    static let lensGrowSpring=1, lensShrinkSpring=2
    static let lensOverrun: CGFloat=7.2
    var tintUpdates=0
    var nativeCalls=0
    var allowSelection=true
    func applyItemTints(selectedAt: Int, animated: Bool) { tintUpdates += 1 }
    func selectionFrame(for slot: CGRect) -> CGRect { NGTabPresentation.capsule(slot:slot) }
    func glassFrame(for slot: CGRect) -> CGRect {
        let pill=selectionFrame(for:slot)
        return CGRect(x:pill.midX-(pill.width+16)/2,y:pill.midY-35,width:pill.width+16,height:70)
    }
    func findClosestItemIndex(to point: CGPoint) -> Int {
        slotFrames.indices.min { abs(slotFrames[$0].midX-point.x) < abs(slotFrames[$1].midX-point.x) } ?? 0
    }
    init() {
        ngActivateNative = { [weak self] target in
            guard let self else { return nil }
            self.nativeCalls += 1
            return self.allowSelection ? target : self.selectedIndex
        }
        ngPlaceHostedPill(selectionFrame(for:slotFrames[0]))
    }
'''
TESTS = r'''
func same(_ a: CGFloat, _ b: CGFloat) -> Bool { abs(a-b) < 0.00001 }
var cases=0
for rtl in [false,true] {
 for reduced in [false,true] {
  UIAccessibility.isReduceMotionEnabled=reduced
  for initial in 0..<4 {
   for pressed in 0..<4 {
    for landing in 0..<4 {
     let h=TestHosted()
     if rtl { h.slotFrames.reverse() }
     h.selectedIndex=initial
     h.ngPlaceHostedPill(h.selectionFrame(for:h.slotFrames[initial]))
     let iconFrames=h.slotFrames
     let x=h.slotFrames[pressed].midX
     h.ngBeginHostedDrag(at:x)
     precondition(h.isDragging && !h.isCollapsingLens)
     h.lensMorphAnimator?.tick(0.42)
     let targetX=h.slotFrames[landing].midX
     h.ngMoveHostedDrag(to:targetX)
     h.lensMorphAnimator?.tick(0.68)
     if abs(targetX-x) >= 0.5 { precondition(same(h.selectionView.frame.midX,targetX)) }
     h.lensMorphAnimator?.tick(1)
     precondition(same(h.selectionView.frame.width,h.glassFrame(for:h.slotFrames[pressed]).width))
     precondition(same(h.selectionView.layer.cornerRadius,min(h.selectionView.frame.width,h.selectionView.frame.height)/2))
     h.ngFinishHostedDrag(at:targetX)
     h.lensMorphAnimator?.tick(1)
     precondition(h.selectedIndex==landing && h.nativeCalls==1 && !h.isDragging && !h.isCollapsingLens)
     precondition(h.selectionView.frame==h.selectionFrame(for:h.slotFrames[landing]))
     precondition(iconFrames==h.slotFrames)
     h.ngFinishHostedDrag(at:targetX)
     precondition(h.nativeCalls==1)
     cases += 1
    }
   }
  }
 }
}
UIAccessibility.isReduceMotionEnabled=false
for rejected in [false,true] {
 let h=TestHosted(); h.allowSelection = !rejected
 h.ngBeginHostedDrag(at:50); h.lensMorphAnimator?.tick(1); h.ngMoveHostedDrag(to:350)
 h.ngFinishHostedDrag(at:350); h.lensMorphAnimator?.tick(0.3)
 h.ngBeginHostedDrag(at:150); h.lensMorphAnimator?.tick(0.5)
 let calls=h.nativeCalls
 h.ngCancelHostedDrag(); h.lensMorphAnimator?.tick(1)
 precondition(h.nativeCalls==calls && !h.isDragging && !h.isCollapsingLens)
 precondition(h.selectionView.frame==h.selectionFrame(for:h.slotFrames[h.selectedIndex]))
 precondition(h.selectedIndex==(rejected ? 0 : 3))
}
let h=TestHosted(); h.items[1].ngEnabled=false
h.ngBeginHostedDrag(at:150); precondition(!h.isDragging && h.nativeCalls==0)
h.ngBeginHostedDrag(at:CGFloat.nan); precondition(!h.isDragging)
h.ngBeginHostedDrag(at:50); h.lensMorphAnimator?.tick(1)
let before=h.selectionView.frame
h.ngMoveHostedDrag(to:CGFloat.nan); precondition(h.selectionView.frame==before)
h.ngMoveHostedDrag(to:10000); precondition(same(h.selectionView.frame.midX,357.2))
h.ngMoveHostedDrag(to:-10000); precondition(same(h.selectionView.frame.midX,42.8))
h.ngCancelHostedDrag(); precondition(h.nativeCalls==0)
print("hosted_production_gestures_ok cases=\(cases) cancel_reject_rtl_reduced_motion=ok")
'''

def main():
    with tempfile.TemporaryDirectory(prefix='hosted-gestures-') as tmp:
        d=Path(tmp); stage(d/'staged')
        tab=(d/'staged/TheseusTabBar.swift').read_text()
        signatures=('ngPlaceHostedPill(', 'ngStopHostedPillMotion(', 'ngBeginHostedDrag(',
                    'ngMoveHostedDrag(', 'ngFinishHostedDrag(', 'ngCancelHostedDrag(')
        source=STANDINS+'\n'.join(method(tab,x) for x in signatures)+'\n}\n'
        source+=(ROOT/'Sources/TabPresentation.swift').read_text()+'\n'+TESTS
        (d/'main.swift').write_text(source)
        if '--emit' in sys.argv:
            Path(sys.argv[sys.argv.index('--emit')+1]).write_text(source)
            print('Extracted six production gesture functions')
            return
        subprocess.run(['xcrun','swiftc','-swift-version','5',str(d/'main.swift'),'-o',str(d/'test')],check=True)
        subprocess.run([str(d/'test')],check=True)

if __name__=='__main__': main()
