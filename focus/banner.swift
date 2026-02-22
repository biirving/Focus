#!/usr/bin/env swift
// Focus OS — Full-width banner notification overlay
// Usage: swift banner.swift "Title" "Message" [--sound]

import Cocoa

class BannerWindow: NSWindow {
    init(title: String, message: String, playSound: Bool) {
        guard let screen = NSScreen.main else { exit(1) }
        let screenFrame = screen.frame
        let bannerHeight: CGFloat = 50
        let bannerFrame = NSRect(
            x: screenFrame.origin.x,
            y: screenFrame.origin.y + screenFrame.size.height - bannerHeight,
            width: screenFrame.size.width,
            height: bannerHeight
        )

        super.init(
            contentRect: bannerFrame,
            styleMask: [.borderless],
            backing: .buffered,
            defer: false
        )

        self.level = .statusBar
        self.backgroundColor = .clear
        self.isOpaque = false
        self.hasShadow = true
        self.collectionBehavior = [.canJoinAllSpaces, .stationary]
        self.ignoresMouseEvents = true

        // Translucent background
        let visualEffect = NSVisualEffectView(frame: NSRect(x: 0, y: 0, width: bannerFrame.width, height: bannerHeight))
        visualEffect.material = .hudWindow
        visualEffect.blendingMode = .behindWindow
        visualEffect.state = .active
        self.contentView = visualEffect

        // Title label
        let titleLabel = NSTextField(labelWithString: title)
        titleLabel.font = NSFont.boldSystemFont(ofSize: 14)
        titleLabel.textColor = .white
        titleLabel.frame = NSRect(x: 20, y: 15, width: 200, height: 20)
        visualEffect.addSubview(titleLabel)

        // Message label
        let messageLabel = NSTextField(labelWithString: message)
        messageLabel.font = NSFont.systemFont(ofSize: 13)
        messageLabel.textColor = NSColor.white.withAlphaComponent(0.9)
        messageLabel.frame = NSRect(x: 230, y: 15, width: bannerFrame.width - 250, height: 20)
        messageLabel.lineBreakMode = .byTruncatingTail
        visualEffect.addSubview(messageLabel)

        if playSound {
            NSSound(named: "Funk")?.play()
        }

        self.alphaValue = 0
        self.orderFrontRegardless()

        // Fade in
        NSAnimationContext.runAnimationGroup({ context in
            context.duration = 0.3
            self.animator().alphaValue = 1
        })

        // Auto-dismiss after 3 seconds
        DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) {
            NSAnimationContext.runAnimationGroup({ context in
                context.duration = 0.5
                self.animator().alphaValue = 0
            }, completionHandler: {
                NSApplication.shared.terminate(nil)
            })
        }
    }
}

// --- Main ---
let args = CommandLine.arguments
guard args.count >= 3 else {
    print("Usage: swift banner.swift \"Title\" \"Message\" [--sound]")
    exit(1)
}

let title = args[1]
let message = args[2]
let playSound = args.contains("--sound")

let app = NSApplication.shared
app.setActivationPolicy(.accessory)

let _ = BannerWindow(title: title, message: message, playSound: playSound)
app.run()
