#Requires AutoHotkey v2.0
#SingleInstance Force

global showingHelpTooltip := false
global running := false

; farming
global autoFarmRunning := false
global autoSlimeRunning := false
global autoKalingRunning := false

; qol
global autoBoxRunning := false
global autoSymbolRunning := false
global isAuthenticSymbol := 1
global symbolIndex := 1

; help menu
~[:: {
    global showingHelpTooltip, autoFarmRunning, autoSlimeRunning, autoBoxRunning, autoKalingRunning, isAuthenticSymbol, symbolIndex
    if showingHelpTooltip
        return

    showingHelpTooltip := true

    status := ""

    if autoFarmRunning
        status .= "Auto Farm`n"
    if autoSlimeRunning
        status .= "Auto Slime Farm`n"
    if autoBoxRunning
        status .= "Auto Christmas Box`n"
    if autoKalingRunning
        status .= "Auto Kaling Farm`n"

    if status = ""
        status := "Nothing`n"

    tooltipText :=
        (
            "Hotkeys:
            [ + 1 : Toggle Auto Farm
            [ + 2 : Toggle Auto Slime Farm
            [ + 3 : Toggle Auto Kaling Farm
            ] + 1 : Toggle Auto Christmas Box
            ] + 2 : Toggle Auto Symbol
            \ + 0 : Toggle Symbol Type
            \ + 0-6 : Set Auto Symbol Index (0-6)
            
            Running: " status "
            Symbol Type: " (isAuthenticSymbol ? "Authentic" : "Arcane") "
            Symbol Index: " symbolIndex "
            "
        )

    ToolTip(tooltipText)

    SetTimer(() => (
        ToolTip(),
        showingHelpTooltip := false
    ), -2000)
}

; auto farm
[ & 1:: {
    global running, autoFarmRunning
    if running && !autoFarmRunning
        return
    running := !running
    autoFarmRunning := !autoFarmRunning

    if running {
        SetTimer AutoFarm, 100
    } else {
        SetTimer AutoFarm, 0
    }
}

; auto slime
[ & 2:: {
    global running, autoSlimeRunning
    if running && !autoSlimeRunning
        return
    running := !running
    autoSlimeRunning := !autoSlimeRunning

    if running {
        SetTimer DoSlime, 1000
    } else {
        SetTimer DoSlime, 0
    }
}

; auto kaling
[ & 3:: {
    global running, autoKalingRunning
    if running && !autoKalingRunning
        return
    running := !running
    autoKalingRunning := !autoKalingRunning

    if running {
        SetTimer DoKaling, 1000
    } else {
        SetTimer DoKaling, 0
    }
}

; auto christmas boxes
] & 1:: {
    global running, autoBoxRunning
    if running && !autoBoxRunning
        return
    running := !running
    autoBoxRunning := !autoBoxRunning

    if running {
        SetTimer OpenChristmasBox, 1000
    } else {
        SetTimer OpenChristmasBox, 0
    }
}

; auto arcane symbols
] & 2:: {
    global running, autoSymbolRunning
    if running && !autoSymbolRunning
        return
    running := !running
    autoSymbolRunning := !autoSymbolRunning   

    if running {
        SetTimer AutoSymbol, 1000
    } else {
        SetTimer AutoSymbol, 0
    }
}

; config symbol type
\ & 0::SetSymbolIndex(0)
\ & 1::SetSymbolIndex(1)
\ & 2::SetSymbolIndex(2)
\ & 3::SetSymbolIndex(3)
\ & 4::SetSymbolIndex(4)
\ & 5::SetSymbolIndex(5)
\ & 6::SetSymbolIndex(6)

SpamKey(key, durationMs, sleepDurationInMs := 0) {
    global running
    start := A_TickCount

    while (running && A_TickCount - start < durationMs) {
        Send key
        Sleep 100
    }

    if sleepDurationInMs > 0
        Sleep sleepDurationInMs
}

ClickAndSleep(x1, y1, sleepDurationInMs) {
    global running
    if !running
        return

    Click x1, y1

    if sleepDurationInMs > 0
        Sleep sleepDurationInMs
}

PressKeyAndSleep(key, sleepDurationInMs) {
    global running
    if !running
        return

    Send key
    Sleep sleepDurationInMs
}

HoldKeyAndSleep(key, holdDurationInMs, sleepDurationInMs := 0) {
    global running
    if !running
        return

    if RegExMatch(key, "^\{(.+)\}$", &m)
        key := m[1]

    Send ("{" key " down}")
    start := A_TickCount
    while (running && A_TickCount - start < holdDurationInMs) {
        Sleep 100
    }
    Send ("{" key " up}")

    if sleepDurationInMs > 0
        Sleep sleepDurationInMs
}

AutoFarm() {
    SpamKey("2", 300)	; Buff key
    SpamKey("q", 30000)	; Attack key
}

DoSlime() {
    ; ==== CONFIG: CHANGE THESE ====
    x1 := 1800, y1 := 820   ; statue
    x2 := 1240, y2 := 770   ; statue confirm
    x3 := 1400, y3 := 430   ; portal
    x4 := 1120, y4 := 620   ; portal confirm
    ; ==============================

    ClickAndSleep(x1, y1, 800)
    ClickAndSleep(x2, y2, 5000)
    SpamKey("q", 3200, 800)
    SpamKey("c", 500, 1700)
    ClickAndSleep(x3, y3, 800)
    ClickAndSleep(x4, y4, 1000)
}

; Boxes is placed at "y"
OpenChristmasBox() {
    PressKeyAndSleep("y", 800)
    PressKeyAndSleep("{Right}", 300)
    PressKeyAndSleep("{Enter}", 100)
    PressKeyAndSleep("{Enter}", 800)
    PressKeyAndSleep("{LAlt}", 800)
}

DoKaling() {
    ; ==== CONFIG: CHANGE THESE ====
    x1 := 1350, y1 := 760   ; entrance
    x2 := 1240, y2 := 770   ; entrance confirm
    x3 := 540, y3 := 790   ; exit portal
    ; ==============================

    HoldKeyAndSleep("{Right}", 300)
    SpamKey("{Space}", 2500, 800)
    SpamKey("1", 200) ; potion
    ClickAndSleep(x1, y1, 800)
    ClickAndSleep(x2, y2, 9000)
    ; bird
    SpamKey("2", 300) ; good buff with low cd (in my case divine echo)
    SpamKey("q", 32000, 1000) ; attack 26s, change this based on your dmg
    ; cat
    SpamKey("2", 300)
    SpamKey("q", 30000, 10000)
    ; fish
    SpamKey("2", 300)
    SpamKey("q", 28000)
    SpamKey("2", 800)
    SpamKey("q", 24000, 1000)
    ; skip the rest 2 phases, too inconsistent
    HoldKeyAndSleep("{Left}", 500)
    SpamKey("{Space}", 2500, 800)
    ClickAndSleep(x3, y3, 800)
    PressKeyAndSleep("{LAlt}", 1500)
}

SetSymbolType() {
    global isAuthenticSymbol
    isAuthenticSymbol := !isAuthenticSymbol
}

SetSymbolIndex(index) {
    global symbolIndex
    symbolIndex := index
}

AutoSymbol() {
    global isAuthenticSymbol, symbolIndex
    x1 := 1880, y1 := 1040   ; inventory slot
    x2 := 920, y2 := 570   ; confirm button
    x3 := 900, y3 := 620   ; confirm button 2

    key := ""
    if isAuthenticSymbol
        key := "{Delete}"
    else
        key := "{Insert}"

    SpamKey(key, 800, 300)
    for i, v in [1, 2, 3, 4, 5, 6] {
        if symbolIndex = v {
            break
        }
        PressKeyAndSleep("{Down}", 100)
    }
    PressKeyAndSleep("{Enter}", 800)
    PressKeyAndSleep("100", 100)
    PressKeyAndSleep("{Enter}", 800)
    PressKeyAndSleep("{Right}", 300)
    PressKeyAndSleep("{Enter}", 1500)
    PressKeyAndSleep("{Enter}", 500)
    ClickAndSleep(x1, y1, 50)
    ClickAndSleep(x1, y1, 50)
    ClickAndSleep(x1, y1, 500)
    ClickAndSleep(x2, y2, 300)
    ClickAndSleep(x3, y3, 1500)
}