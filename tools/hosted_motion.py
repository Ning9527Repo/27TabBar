"""Freeze the hosted background platter while the native lens is active."""


def tab(s, rep):
    return rep(s, '    var ngHostIsInteracting: Bool { isDragging || isCollapsingLens }', '''    var ngHostIsInteracting: Bool { isDragging || isCollapsingLens }

    private func ngSyncPlatterHold() {
        if ngUseHostPosition { backgroundGlassView.ngHoldBackdrop(ngHostIsInteracting) }
    }''')


def renderer(s, rep):
    s = rep(s, '    var ngNonblockingRendering = false',
            '    var ngNonblockingRendering = false\n    var ngBackdropHeld = false')
    return rep(s, '        guard !isShuttingDown else { return }',
               '        guard !isShuttingDown, !ngBackdropHeld else { return }')


def surface(s, rep):
    s = rep(s, '    var ngNonblockingRendering = false', '''    var ngNonblockingRendering = false
    private var ngBackdropHeld = false

    func ngHoldBackdrop(_ held: Bool) {
        guard ngBackdropHeld != held else { return }
        ngBackdropHeld = held
        renderer?.ngBackdropHeld = held
        if !held { renderer?.setNeedsRender() }
    }''')
    return rep(s, '        renderer?.ngNonblockingRendering = ngNonblockingRendering', '''        renderer?.ngNonblockingRendering = ngNonblockingRendering
        renderer?.ngBackdropHeld = ngBackdropHeld''')
