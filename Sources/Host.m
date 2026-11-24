#import "Host.h"
#import <objc/runtime.h>
#import <dispatch/dispatch.h>
#import <dlfcn.h>
#import <math.h>

// The implementation lives in Swift; this narrow ObjC interface avoids importing a
// generated Swift header into the bridging header's own module.
@interface NGSystemTabsBridge : NSObject
+ (void)update:(UITabBar *)bar;
+ (void)detach:(UITabBar *)bar;
+ (BOOL)usesOverlay:(UITabBar *)bar;
@end

typedef UIView *(*NGHitIMP)(UITabBar *, SEL, CGPoint, UIEvent *);
static NGHitIMP NGOrigHit;

static UIView *NGHit(UITabBar *bar, SEL cmd, CGPoint pt, UIEvent *event) {
    if (NSThread.isMainThread && object_getClass(bar) == UITabBar.class &&
        [NGSystemTabsBridge usesOverlay:bar]) return nil;
    return NGOrigHit(bar, cmd, pt, event);
}

static BOOL NGInstallHit(Class cls) {
    SEL sel = @selector(hitTest:withEvent:);
    Method method = class_getInstanceMethod(cls, sel);
    if (!method || method_getNumberOfArguments(method) != 4) return NO;
    char ret[8] = {0}, point[64] = {0}, event[8] = {0};
    method_getReturnType(method, ret, sizeof(ret));
    method_getArgumentType(method, 2, point, sizeof(point));
    method_getArgumentType(method, 3, event, sizeof(event));
    if (ret[0] != '@' || strcmp(point, @encode(CGPoint)) || event[0] != '@') return NO;
    NGHitIMP orig = (NGHitIMP)method_getImplementation(method);
    if (!orig || orig == NGHit) return NGOrigHit != NULL;
    NGOrigHit = orig;
    if (!class_addMethod(cls, sel, (IMP)NGHit, method_getTypeEncoding(method))) {
        NGOrigHit = (NGHitIMP)method_setImplementation(method, (IMP)NGHit);
    }
    return YES;
}

static const UIControlEvents kNGPrimary = UIControlEventPrimaryActionTriggered;
static BOOL NGHasAction(UIControl *control, UIControlEvents event) {
    for (id target in control.allTargets) {
        if ([control actionsForTarget:target == NSNull.null ? nil : target forControlEvent:event].count) return YES;
    }
    return NO;
}

static UIControlEvents NGActivationEvent(UIControl *control) {
    if (NGHasAction(control, UIControlEventTouchUpInside)) return UIControlEventTouchUpInside;
    return NGHasAction(control, kNGPrimary) ? kNGPrimary : 0;
}

NSArray<UIControl *> *NGSystemTabControls(UITabBar *bar, NSInteger expectedCount) {
    if (expectedCount < 2 || expectedCount > 5 || !bar.window) return nil;
    NSUInteger count = (NSUInteger)expectedCount;
    Class button = NSClassFromString(@"UITabBarButton");
    if (!button) return nil;
    NSMutableArray<UIControl *> *controls = [NSMutableArray arrayWithCapacity:count];
    NSMutableArray<UIView *> *queue = [bar.subviews mutableCopy];
    for (NSUInteger index = 0; index < queue.count && index < 128; index++) {
        UIView *view = queue[index];
        if (view.hidden) continue;
        if ([view isKindOfClass:button] && [view isKindOfClass:UIControl.class]) {
            if (CGRectIsEmpty(view.bounds) || !NGActivationEvent((UIControl *)view)) return nil;
            [controls addObject:(UIControl *)view];
        } else {
            [queue addObjectsFromArray:view.subviews];
        }
        if (queue.count > 128 || controls.count > count) return nil;
    }
    if (controls.count != count) return nil;
    [controls sortUsingComparator:^NSComparisonResult(UIControl *a, UIControl *b) {
        CGFloat x = [a convertPoint:CGPointMake(CGRectGetMidX(a.bounds), CGRectGetMidY(a.bounds)) toView:bar].x;
        CGFloat y = [b convertPoint:CGPointMake(CGRectGetMidX(b.bounds), CGRectGetMidY(b.bounds)) toView:bar].x;
        return x < y ? NSOrderedAscending : (x > y ? NSOrderedDescending : NSOrderedSame);
    }];
    if (bar.effectiveUserInterfaceLayoutDirection == UIUserInterfaceLayoutDirectionRightToLeft) {
        controls = [[controls.reverseObjectEnumerator allObjects] mutableCopy];
    }
    CGFloat last = NAN;
    for (UIControl *control in controls) {
        CGRect frame = [control convertRect:control.bounds toView:bar];
        CGFloat center = CGRectGetMidX(frame);
        if (!isfinite(center) || frame.size.width < 20 || !CGRectContainsPoint(bar.bounds, CGPointMake(center, CGRectGetMidY(frame))) || (isfinite(last) && fabs(last-center) < 15)) return nil;
        last = center;
    }
    return controls;
}

BOOL NGActivateSystemTabControl(UIControl *control) {
    UIControlEvents event = NGActivationEvent(control);
    if (!control.enabled || !control.window || event == 0) return NO;
    [control sendActionsForControlEvents:event];
    return YES;
}

NSString *NGTabResourceBundlePath(void) {
    Dl_info info = {0};
    if (!dladdr((const void *)&NGTabResourceBundlePath, &info) || !info.dli_fname) return nil;
    NSString *file = [NSFileManager.defaultManager stringWithFileSystemRepresentation:info.dli_fname length:strlen(info.dli_fname)];
    return [file.stringByDeletingLastPathComponent stringByAppendingPathComponent:@"TheseusSystemTabsResources.bundle"];
}

static BOOL NGIsBaseBar(UITabBar *bar) {
    return NSThread.isMainThread && object_getClass(bar) == UITabBar.class;
}

static void (*NGOrigLayout)(UITabBar *, SEL);
static void (*NGOrigWindow)(UITabBar *, SEL);
static void (*NGOrigSelected)(UITabBar *, SEL, UITabBarItem *);

static void NGLayout(UITabBar *bar, SEL cmd) {
    NGOrigLayout(bar, cmd);
    if (NGIsBaseBar(bar)) [NGSystemTabsBridge update:bar];
}

static void NGWindow(UITabBar *bar, SEL cmd) {
    NGOrigWindow(bar, cmd);
    if (NGIsBaseBar(bar)) {
        if (!bar.window) [NGSystemTabsBridge detach:bar];
        else [bar setNeedsLayout];
    }
}

static void NGSelected(UITabBar *bar, SEL cmd, UITabBarItem *item) {
    NGOrigSelected(bar, cmd, item);
    if (NGIsBaseBar(bar) && bar.window) [bar setNeedsLayout];
}

static void NGInstall(Class cls, SEL sel, IMP replacement, IMP *original, unsigned nargs) {
    Method method = class_getInstanceMethod(cls, sel);
    if (*original || !method || method_getNumberOfArguments(method) != nargs) return;
    char ret[8] = {0};
    method_getReturnType(method, ret, sizeof(ret));
    if (ret[0] != 'v') return;
    if (nargs == 3) {
        char arg[16] = {0};
        method_getArgumentType(method, 2, arg, sizeof(arg));
        if (arg[0] != '@') return;
    }
    IMP impl = method_getImplementation(method);
    if (!impl || impl == replacement) return;
    *original = impl;
    // Do not alter an inherited implementation on UIView.
    if (!class_addMethod(cls, sel, replacement, method_getTypeEncoding(method))) {
        *original = method_setImplementation(method, replacement);
    }
}

__attribute__((constructor)) static void NGStart(void) {
    NSBundle *main = NSBundle.mainBundle;
    NSString *identifier = main.bundleIdentifier;
    if (![main.bundlePath.pathExtension isEqualToString:@"app"] || !identifier.length ||
        [identifier hasPrefix:@"com.tencent.xin"] || [identifier isEqualToString:@"com.apple.springboard"]) return;
    dispatch_async(dispatch_get_main_queue(), ^{
        Class cls = UITabBar.class;
        if (!NGInstallHit(cls)) return;
        NGInstall(cls, @selector(layoutSubviews), (IMP)NGLayout, (IMP *)&NGOrigLayout, 2);
        NGInstall(cls, @selector(didMoveToWindow), (IMP)NGWindow, (IMP *)&NGOrigWindow, 2);
        NGInstall(cls, @selector(setSelectedItem:), (IMP)NGSelected, (IMP *)&NGOrigSelected, 3);
    });
}
