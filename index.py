import cv2
import mss
import numpy as np
import time
import keyboard
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import signal
from threading import Event
from helper import ConfigManager, traceback_str, resource_path
import gc
import psutil


DEFAULT_CONFIG = {
    "INTERVAL": 5,
    "ENABLE_EMAIL": True,
    "TO_EMAIL": "xxx@gmail.com",
    "FROM_EMAIL": "xxx@gmail.com",
    "EMAIL_PASSWORD": "xxxx xxxx xxxx xxxx",  # https://myaccount.google.com/apppasswords
    "ENABLE_AUTOHOTKEY": True,  # for AutoHotKey (remelle_macro.ahk).
    "SPAM_KEY": "[+1",  # for AutoHotKey (remelle_macro.ahk).
}

pause_event = Event()
pause_event.set()
ctrl_c_count = 0
last_ctrl_c_time = 0


def signal_handler(signum, frame):
    global ctrl_c_count, last_ctrl_c_time

    current_time = time.time()

    if current_time - last_ctrl_c_time > 1:
        ctrl_c_count = 0

    ctrl_c_count += 1
    last_ctrl_c_time = current_time
    if ctrl_c_count == 1:
        if pause_event.is_set():
            pause_event.clear()
            print("⏸️  PAUSED")
        else:
            pause_event.set()
            print("▶️  RESUMED")
    elif ctrl_c_count >= 2:
        print("🛑 EXITING MONITOR")
        sys.exit(0)


def is_process_running(process_name):
    for proc in psutil.process_iter(["name"]):
        try:
            if process_name.lower() in proc.info["name"].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def write_log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("bot_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def notify(message):
    if not cfm.config["ENABLE_EMAIL"]:
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = cfm.config["FROM_EMAIL"]
        msg["To"] = cfm.config["TO_EMAIL"]
        msg["Subject"] = "Ramelle Monitor Alert: Text Changed"
        msg.attach(MIMEText(message, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(cfm.config["FROM_EMAIL"], cfm.config["EMAIL_PASSWORD"])
        server.send_message(msg)
        server.quit()

        print(f"✓ Email sent successfully at {datetime.now().strftime('%H:%M:%S')}")
        return True
    except Exception as e:
        print(f"✗ Email failed: {traceback_str(e)}")
        return False


reference_templates = [
    {
        "name": "Cookbot",
        "image": cv2.imread(resource_path("images/cookbot_reference.png"), 0),
        "threshold": 0.8,
        "interval_multiplier": 1,
        "detected": False,
        "last_clear_at": 0,
        "exclusive": False,
        "extra": lambda: (
            keyboard.press_and_release(cfm.config["SPAM_KEY"])
            if cfm.config["ENABLE_AUTOHOTKEY"] and cfm.config["SPAM_KEY"]
            else None
        ),
    },
    {
        "name": "Curse",
        "image": cv2.imread(resource_path("images/curse_reference.png"), 0),
        "threshold": 0.8,
        "interval_multiplier": 5,
        "detected": False,
        "last_clear_at": 0,
        "exclusive": False,
        "extra": lambda: None,
    },
    {
        "name": "Dead",
        "image": cv2.imread(resource_path("images/dead_reference.png"), 0),
        "threshold": 0.8,
        "interval_multiplier": 5,
        "detected": False,
        "last_clear_at": 0,
        "exclusive": False,
        "extra": lambda: None,
    },
]

special_checks = [
    {
        "name": "Out game",
        "interval_multiplier": 10,
        "detected": False,
        "check": lambda *args: not is_process_running("Maplestory.exe"),
        "extra": lambda: (pause_event.clear(), print("⏸️  PAUSED")),
    },
    {
        "name": "Empty mob",
        "interval_multiplier": 30,
        "detected": False,
        # when a channel is bugged (mob no longer spawn)
        # rune will also no longer trigger curse
        # average 40m between each curse, we can safely assume it's bugged if > 1 hour has passed since last curse
        "check": lambda *args: (
            (args[0] - reference_templates[1]["last_clear_at"]) * cfm.config["INTERVAL"]
            > 3600
        ),
        "extra": lambda: None,
    },
]


def perform_check(timestamp, current_count):
    try:
        print(f"{timestamp} [INFO] Performing check...")

        for special in special_checks:
            if current_count % special["interval_multiplier"] != 0:
                continue
            if special["check"](current_count):
                print(f"✗ {special['name']} detected!")
                if not special["detected"]:
                    special["extra"]()
                    notify(f"Time: {timestamp}\n{special['name']} detected!")
                    special["detected"] = True
                return
            elif special["detected"]:
                special["detected"] = False

        monitor = sct_instance.monitors[1]
        sct_img = sct_instance.grab(monitor)
        screenshot = np.array(sct_img)
        gray_img = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
        del sct_img, screenshot

        for temp in reference_templates:
            if current_count % temp["interval_multiplier"] != 0:
                continue
            threshold = temp["threshold"]
            res = cv2.matchTemplate(gray_img, temp["image"], cv2.TM_CCOEFF_NORMED)
            loc = np.where(res >= threshold)
            del res

            if (len(loc[0]) > 0 and not temp["exclusive"]) or (
                len(loc[0]) == 0 and temp["exclusive"]
            ):
                print(f"✗ {temp['name']} detected!")
                if not temp["detected"]:
                    write_log(
                        f"Detected {temp['name']}: cnt={current_count}, interval={cfm.config["INTERVAL"]}"
                    )
                    temp["extra"]()
                    notify(f"Time: {timestamp}\n{temp['name']} detected!")
                    temp["detected"] = True
                break
            elif temp["detected"]:
                write_log(
                    f"Cleared {temp['name']}: cnt={current_count}, interval={cfm.config["INTERVAL"]}"
                )
                temp["detected"] = False
                temp["last_clear_at"] = current_count

        else:
            print(f"✓ No issues detected.")
        del gray_img
    except Exception as e:
        print(f"Check Error: {traceback_str(e)}")
    finally:
        gc.collect()


def main_loop():
    cnt = 0
    while True:
        if not pause_event.is_set():
            pause_event.wait(timeout=0.1)
            continue

        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            perform_check(timestamp, cnt)
            time.sleep(cfm.config["INTERVAL"])
        except Exception as e:
            print(f"Error during monitoring: {traceback_str(e)}")
            time.sleep(cfm.config["INTERVAL"])
        finally:
            cnt = (cnt + 1) % 1000000007


if __name__ == "__main__":
    cfm = ConfigManager("config.json", DEFAULT_CONFIG)
    sct_instance = mss.mss()
    signal.signal(signal.SIGINT, signal_handler)
    print("🛡️  Ramelle Bot Detector Started.")
    print("Press Ctrl+C to pause/resume, double Ctrl+C to exit.\n")
    main_loop()
