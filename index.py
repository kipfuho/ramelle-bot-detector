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
from helper import ConfigManager, traceback_str, resource_path, write_log
import gc
from dataclasses import dataclass
from typing import Callable, Optional
import requests


@dataclass
class TemplateCheck:
    name: str
    image: cv2.typing.MatLike
    threshold: float = 0.8
    interval_multiplier: int = 1
    detected: bool = False
    last_clear_at: int = 0
    exclusive: bool = False
    extra: Optional[Callable[[], None]] = None


@dataclass
class SpecialCheck:
    name: str
    interval_multiplier: int = 1
    detected: bool = False
    check: Optional[Callable[..., bool]] = None
    extra: Optional[Callable[[], None]] = None


def pause_program() -> None:
    pause_event.clear()
    print("⏸️  PAUSED")


def resume_program() -> None:
    pause_event.set()
    print("▶️  RESUMED")


def signal_handler(signum, frame):
    global last_ctrlc_ms

    current_time_ms = time.time() * 1000

    if current_time_ms - last_ctrlc_ms < 1000:
        print("🛑 EXITING MONITOR")
        sys.exit(0)

    last_ctrlc_ms = current_time_ms
    if pause_event.is_set():
        pause_program()
    else:
        resume_program()


def load_template(path: str) -> cv2.typing.MatLike:
    img = cv2.imread(resource_path(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(path)
    return img


def cookbot_extra():
    if cfm.config.enable_autohotkey and cfm.config.spam_key:
        keyboard.press_and_release(cfm.config.spam_key)


def empty_mob_check(*args):
    # when a channel is bugged (mob no longer spawn)
    # rune will also no longer trigger curse
    # average 30m between each curse, we can safely assume it's bugged if > 35m has passed since last curse
    total_count_since_last_curse = args[0] - template_checks[1].last_clear_at
    return total_count_since_last_curse * cfm.config.interval > 2100


def send_ntfy(message: str, title: str = "Ramelle Alert: Bad thing detected"):
    if not cfm.config.enable_ntfy:
        return False

    try:
        url = f"{cfm.config.ntfy_server.rstrip('/')}/{cfm.config.ntfy_topic}"

        headers = {"Priority": str(cfm.config.ntfy_priority), "Title": title}
        if cfm.config.ntfy_tags:
            headers["Tags"] = ",".join(cfm.config.ntfy_tags)

        if cfm.config.ntfy_auth_token:
            headers["Authorization"] = f"Bearer {cfm.config.ntfy_auth_token}"

        print(f"✓ Notify successfully at {datetime.now().strftime('%H:%M:%S')}")
        requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=5)
        return True
    except Exception as e:
        print(f"✗ Notify failed: {traceback_str(e)}")
        return False


def send_email(message: str, subject: str = "Ramelle Alert: Bad thing detected"):
    if not cfm.config.enable_email:
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = cfm.config.from_email
        msg["To"] = cfm.config.to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(cfm.config.from_email, cfm.config.email_password)
        server.send_message(msg)
        server.quit()

        print(f"✓ Email sent successfully at {datetime.now().strftime('%H:%M:%S')}")
        return True
    except Exception as e:
        print(f"✗ Email failed: {traceback_str(e)}")
        return False


def notify(message):
    if send_ntfy(message):
        return
    if send_email(message):
        return


def perform_check(timestamp, cnt):
    try:
        print(f"{timestamp} [INFO] Performing check {cnt}...")

        for special in special_checks:
            if cnt % special.interval_multiplier != 0:
                continue
            if special.check and special.check(cnt):
                print(f"✗ {special.name} detected!")
                if not special.detected:
                    if special.extra:
                        special.extra()
                    notify(f"Time: {timestamp}\n{special.name} detected!")
                    special.detected = True
                return
            elif special.detected:
                special.detected = False

        monitor = sct_instance.monitors[1]
        sct_img = sct_instance.grab(monitor)
        screenshot = np.array(sct_img)
        gray_img = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
        del sct_img, screenshot

        for template in template_checks:
            if cnt % template.interval_multiplier != 0:
                continue
            threshold = template.threshold
            res = cv2.matchTemplate(gray_img, template.image, cv2.TM_CCOEFF_NORMED)
            is_match = len(np.where(res >= threshold)[0]) > 0
            del res

            if is_match ^ template.exclusive:
                print(f"✗ {template.name} detected!")
                if not template.detected:
                    write_log(
                        f"Detected {template.name}: cnt={cnt}, interval={cfm.config.interval}"
                    )
                    if template.extra:
                        template.extra()
                    notify(f"Time: {timestamp}\n{template.name} detected!")
                    template.detected = True
                break
            elif template.detected:
                write_log(
                    f"Cleared {template.name}: cnt={cnt}, interval={cfm.config.interval}"
                )
                template.detected = False
                template.last_clear_at = cnt

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
            time.sleep(cfm.config.interval)
        except Exception as e:
            print(f"Error during monitoring: {traceback_str(e)}")
            time.sleep(cfm.config.interval)
        finally:
            cnt = (cnt + 1) % 1000000007


if __name__ == "__main__":
    # Init some data
    cfm = config_manager = ConfigManager()
    sct_instance = mss.mss()
    pause_event = Event()
    pause_event.set()
    last_ctrlc_ms = 0
    template_checks = [
        TemplateCheck(
            name="Cookbot",
            image=load_template("images/cookbot_reference.png"),
            extra=cookbot_extra,
        ),
        TemplateCheck(
            name="Curse",
            image=load_template("images/curse_reference.png"),
            interval_multiplier=5,
        ),
        TemplateCheck(
            name="Dead",
            image=load_template("images/dead_reference.png"),
            interval_multiplier=5,
        ),
        TemplateCheck(
            name="Out game",
            image=load_template("images/level_reference.png"),
            interval_multiplier=10,
            exclusive=True,
            extra=pause_program,
        ),
    ]
    special_checks = [
        SpecialCheck(
            name="Empty mob",
            interval_multiplier=30,
            check=empty_mob_check,
        ),
    ]
    signal.signal(signal.SIGINT, signal_handler)
    print("🛡️  Ramelle Bot Detector Started.")
    print("Press Ctrl+C to pause/resume, double Ctrl+C to exit.\n")
    main_loop()
