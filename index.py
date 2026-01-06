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

DEFAULT_CONFIG = {
    "INTERVAL": 5,
    "ENABLE_EMAIL": True,
    "TO_EMAIL": "xxx@gmail.com",
    "FROM_EMAIL": "xxx@gmail.com",
    "EMAIL_PASSWORD": "xxxx xxxx xxxx xxxx",  # https://myaccount.google.com/apppasswords
    "ENABLE_AUTOHOTKEY": True,  # for AutoHotKey (spammingQ.ahk).
    "SPAM_KEY": "[+1",  # for AutoHotKey (remelle_macro.ahk).
}

stop_event = Event()
pause_event = Event()
pause_event.set()
ctrl_c_count = 0
last_ctrl_c_time = 0


def small_sleep(seconds):
    end_time = time.time() + seconds

    while time.time() < end_time:
        if stop_event.is_set():
            return
        time.sleep(0.1)


def signal_handler(signum, frame):
    global ctrl_c_count, last_ctrl_c_time

    current_time = time.time()

    if current_time - last_ctrl_c_time > 1:
        ctrl_c_count = 0

    ctrl_c_count += 1
    last_ctrl_c_time = current_time
    if ctrl_c_count == 1:
        stop_event.set()
        if pause_event.is_set():
            pause_event.clear()
            print("⏸️  PAUSED")
        else:
            pause_event.set()
            stop_event.clear()
            print("▶️  RESUMED")
    elif ctrl_c_count >= 2:
        print("🛑 EXITING MONITOR")
        stop_event.set()
        sys.exit(0)


def notify(message):
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
        "image": cv2.imread(resource_path("cookbot_reference.png"), 0),
        "threshold": 0.8,
        "interval_multiplier": 1,
        "detected": False,
        "extra": lambda: (
            keyboard.press_and_release(cfm.config["SPAM_KEY"])
            if cfm.config["ENABLE_AUTOHOTKEY"] and cfm.config["SPAM_KEY"]
            else None
        ),
    },
    {
        "name": "Curse",
        "image": cv2.imread(resource_path("curse_reference.png"), 0),
        "threshold": 0.8,
        "interval_multiplier": 5,
        "detected": False,
        "extra": lambda: None,
    },
    {
        "name": "Dead",
        "image": cv2.imread(resource_path("dead_reference.png"), 0),
        "threshold": 0.8,
        "interval_multiplier": 5,
        "detected": False,
        "extra": lambda: None,
    },
]


def perform_check(timestamp, current_count):
    try:
        print(f"{timestamp} [INFO] Performing check...")
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            screenshot = np.array(sct_img)
            gray_img = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
            del sct_img, screenshot

            for temp in reference_templates:
                if current_count % temp["interval_multiplier"] != 0:
                    continue
                threshold = temp["threshold"]
                res = cv2.matchTemplate(gray_img, temp["image"], cv2.TM_CCOEFF_NORMED)
                loc = np.where(res >= threshold)
                if len(loc[0]) > 0:
                    print(f"✗ {temp['name']} detected!")
                    if not temp["detected"]:
                        temp["extra"]()
                        notify(f"Time: {timestamp}\n{temp['name']} detected!")
                        temp["detected"] = True
                    del res, gray_img
                    break
            else:
                print(f"✓ No issues detected.")
                for temp in reference_templates:
                    if current_count % temp["interval_multiplier"] != 0:
                        continue
                    temp["detected"] = False
    except Exception as e:
        print(f"Check Error: {traceback_str(e)}")
    finally:
        gc.collect()


def main_loop():
    cnt = 0
    while True:
        if not pause_event.is_set():
            small_sleep(5)
            continue

        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            perform_check(timestamp, cnt)
            time.sleep(cfm.config["INTERVAL"])
        except Exception as e:
            print(f"Error during monitoring: {traceback_str(e)}")
            small_sleep(5)
        finally:
            cnt = (cnt + 1) % 1000000007


if __name__ == "__main__":
    cfm = ConfigManager("config.json", DEFAULT_CONFIG)
    signal.signal(signal.SIGINT, signal_handler)
    print(
        "🛡️  Ramelle Bot Detector Started. Press Ctrl+C to pause/resume, double Ctrl+C to exit."
    )
    main_loop()
