#pragma once
#include <math.h>
#include <stdbool.h>
#include <stddef.h>

typedef struct { double x, y, width, height; } NGNativeRect;

static inline bool NGNativeRectFinite(NGNativeRect r) {
    return isfinite(r.x) && isfinite(r.y) && isfinite(r.width) && isfinite(r.height)
        && r.width > 0 && r.height > 0;
}

static inline bool NGNativeRectMatches(NGNativeRect a, NGNativeRect b) {
    return NGNativeRectFinite(a) && NGNativeRectFinite(b)
        && fabs(a.x-b.x) < 0.1 && fabs(a.y-b.y) < 0.1
        && fabs(a.width-b.width) < 0.1 && fabs(a.height-b.height) < 0.1;
}

static inline NGNativeRect NGNativeCapsule(NGNativeRect bounds, size_t count) {
    NGNativeRect zero = {0};
    if (!NGNativeRectFinite(bounds) || count < 2 || count > 5 || bounds.width < 260 || bounds.height < 65 || bounds.height > 112) return zero;
    double width = fmin(bounds.width - 28, count * 66.0);
    NGNativeRect frame = {bounds.x + (bounds.width-width)*0.5, bounds.y+2, width, 63};
    return frame;
}

static inline NGNativeRect NGNativeButtonSlot(NGNativeRect capsule, size_t count, size_t visualIndex) {
    NGNativeRect zero = {0};
    if (!NGNativeRectFinite(capsule) || count < 2 || count > 5 || visualIndex >= count) return zero;
    double width = (capsule.width - 30)/count;
    if (width < 44) return zero;
    double inset = fmin((capsule.height - 44)*0.5, 3);
    NGNativeRect frame = {capsule.x + 15 + visualIndex*width, capsule.y + inset,
                          width, capsule.height - inset*2};
    return frame;
}
