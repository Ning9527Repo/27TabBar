#import <UIKit/UIKit.h>

NS_ASSUME_NONNULL_BEGIN
NSArray<UIControl *> * _Nullable NGSystemTabControls(UITabBar *bar, NSInteger expectedCount);
BOOL NGActivateSystemTabControl(UIControl *control);
NSString * _Nullable NGTabResourceBundlePath(void);
NS_ASSUME_NONNULL_END
