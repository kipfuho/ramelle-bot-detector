from PIL import Image, ImageGrab, ImageTk
import cv2
import numpy as np
import easyocr
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread, Event
import sys
import os
import signal
import json
from pathlib import Path
import tkinter as tk
import keyboard
import traceback

# Default Configuration
DEFAULT_CONFIG = {
    "REGIONS": [
        {
            "X": 870,
            "Y": 1045,
            "W": 190,
            "H": 20,
            "COMPARE_MODE": "==",
        },
    ],
    "INTERVAL": 10,
    "ENABLE_EMAIL": True,
    "TO_EMAIL": "xxx@gmail.com",
    "FROM_EMAIL": "xxx@gmail.com",
    "EMAIL_PASSWORD": "xxxx xxxx xxxx xxxx", # https://myaccount.google.com/apppasswords
    "ENABLE_AUTOHOTKEY": True, # for AutoHotKey (spammingQ.ahk).
    "SPAM_KEY": "q", # for AutoHotKey (spammingQ.ahk). This will press the SPAM_KEY when the ocr_monitor stop
}


# Global variables
config = {}
stop_event = Event()
pause_event = Event()
pause_event.set()
ctrl_c_count = 0
last_ctrl_c_time = 0
reader = None


def traceback_str(e: Exception):
    """Convert exception to string with traceback."""
    return ''.join(traceback.format_exception(type(e), e, e.__traceback__))


def small_sleep(seconds):
    """Sleep in small increments, interruptible by Ctrl+C."""
    end_time = time.time() + seconds

    while time.time() < end_time:
        if stop_event.is_set():
            return
        time.sleep(0.1)


def signal_handler(signum, frame):
    """Handle Ctrl+C: single = pause/resume, double = exit."""
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
            print("\n" + "="*60)
            print("⏸️  PAUSED")
            print("Commands:")
            print("  Ctrl+C - Resume")
            print("  Ctrl+C twice - Exit")
            print("  A + Enter - Edit all settings")
            print("  R + Enter - Edit monitor regions")
            print("  M + Enter - Edit monitor settings")
            print("  E + Enter - Edit email settings")
            print("="*60)
        else:
            pause_event.set()
            stop_event.clear()
            print("\n" + "="*60)
            print("▶️  RESUMED")
            print("="*60 + "\n")
    elif ctrl_c_count >= 2:
        print("\n" + "="*60)
        print("🛑 EXITING MONITOR")
        print("="*60)
        stop_event.set()
        sys.exit(0)


def get_config_path():
    """Get path to config file."""
    if getattr(sys, 'frozen', False):
        return Path(os.path.dirname(sys.executable)) / "config.json"
    else:
        return Path(__file__).parent / "config.json"


def get_models_path():
    """Get path to store EasyOCR models."""
    if getattr(sys, 'frozen', False):
        # When running as executable, store models next to the executable
        models_dir = Path(os.path.dirname(sys.executable)) / "easyocr_models"
    else:
        # When running as script, use the script directory
        models_dir = Path(__file__).parent / "easyocr_models"
    
    # Create directory if it doesn't exist
    models_dir.mkdir(parents=True, exist_ok=True)
    return str(models_dir)


def load_config():
    """Load configuration from file or create default."""
    global config
    config_path = get_config_path()
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"✓ Configuration loaded from {config_path}")
            return config
        except Exception as e:
            print(f"⚠ Error loading config: {traceback_str(e)}")
            print("Using default configuration")
    
    config = DEFAULT_CONFIG.copy()
    save_config()
    return config


def save_config():
    """Save current configuration to file."""
    config_path = get_config_path()
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"✓ Configuration saved to {config_path}")
    except Exception as e:
        print(f"✗ Error saving config: {traceback_str(e)}")


class RegionSelector:
    """Interactive region selector using mouse."""
    
    def __init__(self):
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.rect_id = None
        self.selected = False
        
    def select_region(self):
        """Open fullscreen overlay to select region with mouse."""
        print("\n" + "="*60)
        print("📍 INTERACTIVE REGION SELECTOR")
        print("="*60)
        print("Instructions:")
        print("1. A screenshot will appear in 2 seconds")
        print("2. Click and drag to select the region")
        print("3. Release mouse to confirm")
        print("4. Press ESC to cancel")
        print("="*60)
        
        small_sleep(2)
        
        # Take screenshot
        screenshot = ImageGrab.grab()
        
        # Create fullscreen window
        root = tk.Tk()
        root.attributes('-fullscreen', True)
        root.attributes('-topmost', True)
        root.configure(cursor="crosshair")
        
        # Convert PIL image to PhotoImage
        photo = ImageTk.PhotoImage(screenshot)
        
        # Create canvas
        canvas = tk.Canvas(root, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Display screenshot
        canvas.create_image(0, 0, image=photo, anchor=tk.NW)
        
        # Instruction text
        instruction = canvas.create_text(
            root.winfo_screenwidth() // 2, 30,
            text="Click and drag to select region (ESC to cancel)",
            font=("Arial", 16, "bold"),
            fill="red",
            tags="instruction"
        )
        
        def on_mouse_down(event):
            self.start_x = event.x
            self.start_y = event.y
            # Remove instruction text
            canvas.delete("instruction")
        
        def on_mouse_move(event):
            if self.start_x is not None and self.start_y is not None:
                # Delete previous rectangle
                if self.rect_id:
                    canvas.delete(self.rect_id)
                
                # Draw new rectangle
                self.rect_id = canvas.create_rectangle(
                    self.start_x, self.start_y, event.x, event.y,
                    outline="red", width=3, dash=(5, 5)
                )
                
                # Draw dimensions text
                w = abs(event.x - self.start_x)
                h = abs(event.y - self.start_y)
                canvas.delete("dimensions")
                canvas.create_text(
                    self.start_x, self.start_y - 10,
                    text=f"{w}x{h}",
                    font=("Arial", 12, "bold"),
                    fill="red",
                    tags="dimensions",
                    anchor=tk.SW
                )
        
        def on_mouse_up(event):
            self.end_x = event.x
            self.end_y = event.y
            self.selected = True
            root.quit()
            root.destroy()
        
        def on_escape(event):
            self.selected = False
            root.quit()
            root.destroy()
        
        # Bind events
        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_move)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        root.bind("<Escape>", on_escape)
        
        root.mainloop()
        
        if self.selected:
            # Calculate region coordinates
            x = min(self.start_x, self.end_x)
            y = min(self.start_y, self.end_y)
            w = abs(self.end_x - self.start_x)
            h = abs(self.end_y - self.start_y)
            
            print(f"\n✓ Region selected: x={x}, y={y}, w={w}, h={h}")
            
            # Show preview
            preview = screenshot.crop((x, y, x + w, y + h))
            
            # Create preview window
            preview_root = tk.Tk()
            preview_root.title("Region Preview")
            
            # Scale preview if too large
            max_size = 400
            preview_display = preview.copy()
            if preview.width > max_size or preview.height > max_size:
                ratio = min(max_size / preview.width, max_size / preview.height)
                new_size = (int(preview.width * ratio), int(preview.height * ratio))
                preview_display = preview.resize(new_size, Image.LANCZOS)
            
            preview_photo = ImageTk.PhotoImage(preview_display)
            
            label = tk.Label(preview_root, image=preview_photo)
            label.pack()
            
            confirm_frame = tk.Frame(preview_root)
            confirm_frame.pack(pady=10)
            
            confirmed = [False]
            
            def confirm():
                confirmed[0] = True
                preview_root.quit()
                preview_root.destroy()
            
            def cancel():
                confirmed[0] = False
                preview_root.quit()
                preview_root.destroy()
            
            tk.Button(confirm_frame, text="✓ Confirm", command=confirm, 
                     bg="green", fg="white", padx=20, pady=5).pack(side=tk.LEFT, padx=5)
            tk.Button(confirm_frame, text="✗ Cancel", command=cancel,
                     bg="red", fg="white", padx=20, pady=5).pack(side=tk.LEFT, padx=5)
            
            preview_root.mainloop()
            
            if confirmed[0]:
                # Save preview
                preview.save("region_preview.png")
                print("✓ Preview saved to region_preview.png")
                return x, y, w, h
            else:
                print("✗ Region selection cancelled")
                return None
        else:
            print("\n✗ Region selection cancelled")
            return None


def edit_email_config(save_after=True):
    print("--- EMAIL SETTINGS ---")
    enable_email = input(f"Enable email notifications? (yes/no) [{config['ENABLE_EMAIL']}]: ").strip().lower()
    if enable_email in ['yes', 'y', 'true', '1']:
        config['ENABLE_EMAIL'] = True
    elif enable_email in ['no', 'n', 'false', '0']:
        config['ENABLE_EMAIL'] = False
    
    if config['ENABLE_EMAIL']:
        to_email = input(f"To email [{config['TO_EMAIL']}]: ").strip()
        if to_email:
            config['TO_EMAIL'] = to_email
        
        from_email = input(f"From email (Gmail) [{config['FROM_EMAIL']}]: ").strip()
        if from_email:
            config['FROM_EMAIL'] = from_email
        
        password = input(f"Gmail App Password [{'*' * len(config['EMAIL_PASSWORD'])}]: ").strip()
        if password:
            config['EMAIL_PASSWORD'] = password
    if save_after:
        save_config()


def edit_monitor_config(save_after=True):
    print("\n--- MONITOR SETTINGS ---")
    interval = input(f"Check interval (seconds) [{config['INTERVAL']}]: ").strip()
    if interval.isdigit():
        config['INTERVAL'] = int(interval)
    enable_autokey = input(f"Enable AutoHotkey (default True) (y/n): ").strip().lower()
    if enable_autokey.lower() in ['no', 'n', 'false', '0']:
        enable_autokey = False
    else:
        enable_autokey = True
    config['ENABLE_AUTOHOTKEY'] = enable_autokey
    if enable_autokey:
        spam_key = input(f"Spam key (default 'q') [{config['SPAM_KEY']}]: ").strip()
        config['SPAM_KEY'] = spam_key
    if save_after:
        save_config()


def edit_region_config(save_after=True):
    print("\n--- SCREEN REGION ---")
    region_edit_mode = input("Add or edit or delete regions (a/e/d): ").strip()
    if region_edit_mode.lower() == 'a':
        num_regions = input("How many regions to add? ").strip()
        if num_regions.isdigit():
            for _ in range(int(num_regions)):
                print("\nSelect new region:")
                selector = RegionSelector()
                result = selector.select_region()
                if result:
                    x, y, w, h = result
                    compare_mode = input("Compare mode (== or !=) [default !=]: ").strip()
                    if compare_mode not in ['==', '!=']:
                        compare_mode = "!="
                    config['REGIONS'].append({
                        "X": x,
                        "Y": y,
                        "W": w,
                        "H": h,
                        "COMPARE_MODE": compare_mode,
                    })
    elif region_edit_mode.lower() == 'e':
        for region in config['REGIONS']:
            print(f"Current region: x={region['X']}, y={region['Y']}, w={region['W']}, h={region['H']}, mode={region['COMPARE_MODE']}")
            select_region = input("Select region with mouse? (yes/no) [yes]: ").strip().lower()
        
            if select_region not in ['no', 'n', 'false', '0']:
                selector = RegionSelector()
                result = selector.select_region()
                compare_mode = input(f"Compare mode (== or !=) [{region['COMPARE_MODE']}]: ").strip().lower()
                if compare_mode not in ['==', '!=']:
                    compare_mode = region['COMPARE_MODE']
                if result:
                    region['X'], region['Y'], region['W'], region['H'] = result
                    region['COMPARE_MODE'] = compare_mode
    elif region_edit_mode.lower() == 'd':
        for i, region in enumerate(config['REGIONS']):
            print(f"Region {i}: x={region['X']}, y={region['Y']}, w={region['W']}, h={region['H']}, mode={region['COMPARE_MODE']}")
        delete_index = input("Enter index of region to delete: ").strip()
        if delete_index.isdigit() and 0 <= int(delete_index) < len(config['REGIONS']):
            config['REGIONS'].pop(int(delete_index))
    if save_after:
        save_config()


def edit_config_interactive():
    """Interactive configuration editor."""
    print("\n" + "="*60)
    print("⚙️  CONFIGURATION EDITOR")
    print("="*60)
    print("Press Enter to keep current value\n")
    
    # Email settings
    edit_email_config(save_after=False)
    
    # Monitor settings
    edit_monitor_config(save_after=False)

    # Region settings
    edit_region_config(save_after=False)
    
    save_config()
    print("\n✓ Configuration updated!\n")


def advanced_preprocess(image, invert=False):
    """Advanced preprocessing specifically for low contrast text."""
    img_array = np.array(image)
    
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    if invert:
        gray = cv2.bitwise_not(gray)
    
    height, width = gray.shape
    gray = cv2.resize(gray, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
    
    filtered = cv2.bilateralFilter(gray, 5, 50, 50)
    
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(filtered)
    
    kernel = np.ones((2,2), np.uint8)
    morph = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)
    
    _, binary = cv2.threshold(morph, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    kernel2 = np.ones((1,1), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel2)
    
    return Image.fromarray(cleaned)


def capture_and_ocr(x, y, w, h, debug=False):
    """Capture and perform OCR on screen region."""
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    processed = advanced_preprocess(img, invert=True)
    
    result = reader.readtext(
        np.array(processed), 
        detail=0,
        paragraph=False,
        batch_size=1,
    )

    if debug:
        timestamp = int(time.time() * 1000)
        img.save(f"debug_cropped_{timestamp}.jpg")
        processed.save(f"debug_processed_{timestamp}.jpg")
    
    return result[0] if result else ""


def send_email_notification(subject, body, to_email, from_email, password):
    """Send email in background thread - non-blocking."""
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()
        
        print(f"✓ Email sent successfully at {datetime.now().strftime('%H:%M:%S')}")
        return True
    except Exception as e:
        print(f"✗ Email failed: {traceback_str(e)}")
        return False


def send_notify():
    """Send notification (non-blocking if email)."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"\n{'='*60}")
    print(f"🔔 CHANGE DETECTED!")
    print(f"{'='*60}")
    print(f"Time: {timestamp}")
    print(f"{'='*60}\n")
    
    if config['ENABLE_EMAIL']:
        subject = "Ramelle Monitor Alert: Text Changed"
        body = f"Time: {timestamp}\n"
        
        email_thread = Thread(
            target=send_email_notification, 
            args=(subject, body, config['TO_EMAIL'], config['FROM_EMAIL'], config['EMAIL_PASSWORD']),
            daemon=True
        )
        email_thread.start()
        print("📧 Sending email in background...")


def handle_pause_commands():
    """Handle commands while paused."""
    try:
        print("\nEnter command: ", end='', flush=True)
        command = input().strip().lower()
        
        if command == 'a':
            edit_config_interactive()
        elif command == 'r':
            edit_region_config()
        elif command == 'e':
            edit_email_config()
        elif command == 'm':
            edit_monitor_config()
        elif command:
            print(f"Unknown command: {command}")
            
    except Exception as e:
        if not isinstance(e, EOFError) and not isinstance(e, KeyboardInterrupt):
            print(f"Error handle_pause_commands: {traceback_str(e)}")
        pass


def monitor_ocr_changes():
    """Main monitoring loop."""
    global reader
    
    print("=" * 60)
    print("OCR MONITOR STARTED")
    print("=" * 60)
    print(f"Monitoring region: {len(config['REGIONS'])} regions")
    print(f"Check interval: {config['INTERVAL']}s")
    print(f"Email notifications: {'ENABLED' if config['ENABLE_EMAIL'] else 'DISABLED'}")
    print("\nControls:")
    print("  Ctrl+C once: Pause")
    print("  Ctrl+C twice: Exit")
    print("  While paused: R=region, A=all, M=monitor, E=email")
    print("=" * 60 + "\n")
    
    previous_texts = [None] * len(config['REGIONS'])
    check_count = 0

    while True:
        if not pause_event.is_set():
            handle_pause_commands()
            small_sleep(1)
            continue
        
        check_count += 1
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        try:
            bad_regions = []
            for idx, region in enumerate(config['REGIONS']):
                current_text = capture_and_ocr(region['X'], region['Y'], region['W'], region['H'])

                if previous_texts[idx] is None:
                    previous_texts[idx] = current_text
                    continue

                if (region['COMPARE_MODE'] == '==' and current_text == previous_texts[idx]) or \
                   (region['COMPARE_MODE'] == '!=' and current_text != previous_texts[idx]):
                    bad_regions.append((idx, previous_texts[idx], current_text))
                else:
                    previous_texts[idx] = current_text

            if len(bad_regions) > 0:
                for idx, old_text, new_text in bad_regions:
                    print(f"[{timestamp}] ⚠️  Region {idx} changed: '{old_text}' -> '{new_text}'")
                send_notify()
                pause_event.clear()
                if config['ENABLE_AUTOHOTKEY'] and config['SPAM_KEY']:
                    keyboard.press_and_release(config['SPAM_KEY'])
                previous_texts = [None] * len(config['REGIONS'])
                print("\n" + "="*60)
                print("⏸️  AUTO-PAUSED after change detection")
                print("Press Ctrl+C to resume (or R/A/M/E for settings)")
                print("="*60)
                print("\nEnter command: ", end='', flush=True)
                continue
            else:
                print(f"[{timestamp}] ✅ No changes detected (Check #{check_count})")
                small_sleep(config['INTERVAL'])
        except Exception as e:
            print(f"[{timestamp}] Error: {traceback_str(e)}")
            small_sleep(5)  # Wait before retrying after error


if __name__ == "__main__":
    print("Initializing OCR Monitor...")
    
    # Load configuration
    load_config()
    
    # Check if user wants to configure first
    if len(sys.argv) > 1 and sys.argv[1] == "--config":
        edit_config_interactive()
    
    # Initialize EasyOCR with persistent model storage
    print("\nInitializing EasyOCR... (this may take a moment)")
    models_path = get_models_path()
    print(f"Models will be stored in: {models_path}")
    
    # FIXED: Use proper model storage directory that persists
    reader = easyocr.Reader(
        ['en'], 
        gpu=False, 
        model_storage_directory=models_path,
        download_enabled=True  # Ensure models can be downloaded
    )
    print("✓ EasyOCR initialized successfully")

    # Setup signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start monitoring
    monitor_ocr_changes()