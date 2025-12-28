#Requires AutoHotkey v2.0

~q::{
    static running := false
    running := !running

    if running
        SetTimer spamQ, 100   ; adjust speed (ms)
    else
        SetTimer spamQ, 0
}

spamQ(){
    Send "{q}"
}