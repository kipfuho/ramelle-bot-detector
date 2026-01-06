#Requires AutoHotkey v2.0
#SingleInstance Force

; ================= CONFIG =================
baseSpeed      := 6
maxSpeed       := 25
accelStep      := 1.2
fastMultiplier := 3.0
slowMultiplier := 0.3
tickMs         := 5
scrollAmount   := 1
; ==========================================

enabled := false
currentSpeed := baseSpeed

keys := Map(
    "w", [0, -1],
    "a", [-1, 0],
    "s", [0, 1],
    "d", [1, 0]
)

SetTimer(moveMouse, tickMs)

moveMouse() {
    global keys, baseSpeed, maxSpeed, accelStep
    global fastMultiplier, slowMultiplier
    global currentSpeed, enabled

    if !enabled
        return

    dx := 0, dy := 0
    moving := false

    for key, dir in keys {
        if GetKeyState(key, "P") {
            dx += dir[1]
            dy += dir[2]
            moving := true
        }
    }

    if moving {
        currentSpeed := Min(currentSpeed + accelStep, maxSpeed)
    } else {
        currentSpeed := baseSpeed
        return
    }

    speed := currentSpeed

    if GetKeyState("Shift", "P")
        speed *= fastMultiplier
    if GetKeyState("Ctrl", "P")
        speed *= slowMultiplier

    MouseMove dx * speed, dy * speed, 0, "R"
}

; ================= BLOCKED KEYS =================
#HotIf enabled
w::return
a::return
s::return
d::return

LShift::return
RShift::return
LCtrl::return
RCtrl::return

j::Click "Left"
k::Click "Right"
u::Click "Middle"

i::Send "{WheelUp " scrollAmount "}"
o::Send "{WheelDown " scrollAmount "}"
#HotIf

; ================= TOGGLE =================
ScrollLock::{
    global enabled
    enabled := !enabled
    ToolTip enabled ? "Mouse Control: ON" : "Mouse Control: OFF"
    SetTimer () => ToolTip(), -800
}

; ================= EXIT =================
~Esc & F12::ExitApp
