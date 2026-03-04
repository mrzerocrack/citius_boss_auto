import zipfile
import os
import sys
import datetime
import re
import time
import socket
import tempfile
import atexit
from time import sleep, strftime
import random
import secrets
import string
import requests
import json
import psutil
import urllib.request
import pickle
import subprocess
import shutil
from PIL import Image

try:
    import undetected_chromedriver as uc  # optional, dipakai hanya untuk helper path jika tersedia
except Exception:
    uc = None

try:
    import tkinter as tk
    from tkinter import messagebox
except Exception:
    tk = None
    messagebox = None

try:
    import win32api  # type: ignore
except Exception:
    win32api = None

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TEMP_PROFILE_DIRS = []


def _cleanup_temp_profiles():
    for path in TEMP_PROFILE_DIRS:
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass


atexit.register(_cleanup_temp_profiles)


def env_truthy(name, default="0"):
    value = os.environ.get(name, default)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def use_existing_chrome_attach_mode():
    return env_truthy("CHROME_ATTACH_EXISTING", "0")


# =========================
# CONFIG
# =========================
def _windows_registry_chrome_paths():
    if os.name != "nt":
        return []
    try:
        import winreg  # type: ignore
    except Exception:
        return []

    candidates = []
    keys = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
    ]
    for hive, subkey in keys:
        try:
            with winreg.OpenKey(hive, subkey) as handle:
                value, _ = winreg.QueryValueEx(handle, "")
                if value:
                    candidates.append(value)
        except Exception:
            continue
    return candidates


def resolve_chrome_binary():
    candidates = []
    override = os.environ.get("CHROME_BINARY") or os.environ.get("BROWSER_EXECUTABLE_PATH")
    if override:
        candidates.append(override.strip())
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        program_w6432 = os.environ.get("ProgramW6432", r"C:\Program Files")
        program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        candidates.extend(
            [
                shutil.which("chrome"),
                shutil.which("chrome.exe"),
                os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe")
                if local_app_data
                else "",
                os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(program_w6432, "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
            ]
        )
        candidates.extend(_windows_registry_chrome_paths())
        try:
            proc = subprocess.run(["where", "chrome"], capture_output=True, text=True, check=False, timeout=5)
            candidates.extend([line.strip() for line in proc.stdout.splitlines() if line.strip()])
        except Exception:
            pass
        try:
            finder = getattr(uc, "find_chrome_executable", None)
            if uc is not None and callable(finder):
                candidates.append(finder())
        except Exception:
            pass
    else:
        candidates.extend(
            [
                shutil.which("google-chrome"),
                shutil.which("google-chrome-stable"),
                "/opt/google/chrome/chrome",
                shutil.which("chromium"),
                shutil.which("chromium-browser"),
            ]
        )
    seen = set()
    for path in candidates:
        if not path:
            continue
        norm = os.path.normcase(os.path.normpath(path))
        if norm in seen:
            continue
        seen.add(norm)
        if os.path.exists(path):
            return path
    return ""


def _extract_chrome_major(raw):
    m = re.search(r"(\d+)\.\d+\.\d+\.\d+", raw or "")
    if not m:
        return 0
    try:
        return int(m.group(1))
    except Exception:
        return 0


def detect_chrome_major(chrome_bin):
    if not chrome_bin:
        return 0

    if os.name == "nt":
        if win32api is not None:
            try:
                info = win32api.GetFileVersionInfo(chrome_bin, "\\")
                ms = int(info.get("FileVersionMS", 0))
                major = (ms >> 16) & 0xFFFF
                if major > 0:
                    return major
            except Exception:
                pass

        # Windows: baca versi executable langsung agar tidak memicu spawn Chrome.
        escaped = chrome_bin.replace("'", "''")
        ps = f"(Get-Item -LiteralPath '{escaped}').VersionInfo.ProductVersion"
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                text=True,
                check=False,
                timeout=8,
            )
            major = _extract_chrome_major(f"{proc.stdout}\n{proc.stderr}")
            if major > 0:
                return major
        except Exception:
            pass

    try:
        proc = subprocess.run([chrome_bin, "--version"], capture_output=True, text=True, check=False, timeout=8)
        major = _extract_chrome_major(f"{proc.stdout}\n{proc.stderr}")
        if major > 0:
            return major
    except Exception:
        pass
    return 0


def extract_browser_major_from_error(exc):
    try:
        msg = str(exc)
    except Exception:
        return 0
    m = re.search(r"Current browser version is\s+(\d+)\.", msg)
    if not m:
        return 0
    try:
        return int(m.group(1))
    except Exception:
        return 0


def resolve_linux_chrome_profile():
    """Return (user_data_dir, profile_directory) for Linux Chrome profile."""
    env_user_data = (os.environ.get("CHROME_USER_DATA_DIR") or "").strip()
    env_profile_dir = (os.environ.get("CHROME_PROFILE_DIR") or "").strip()
    env_profile_path = (os.environ.get("CHROME_PROFILE_PATH") or "").strip()

    # CHROME_PROFILE_PATH can be either full profile path or user-data-dir.
    if env_profile_path:
        if os.path.isdir(env_profile_path):
            base = os.path.basename(env_profile_path.rstrip("/"))
            if base == "Default" or base.startswith("Profile "):
                return os.path.dirname(env_profile_path), base
            return env_profile_path, env_profile_dir

    if env_user_data and os.path.isdir(env_user_data):
        return env_user_data, env_profile_dir

    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".config", "google-chrome"),
        os.path.join(home, ".config", "google-chrome-stable"),
        os.path.join(home, ".config", "chromium"),
    ]
    for base in candidates:
        if os.path.isdir(base):
            return base, env_profile_dir
    return "", env_profile_dir


def clone_linux_profile(user_data_dir, profile_dir):
    if not user_data_dir or not os.path.isdir(user_data_dir):
        return user_data_dir, profile_dir
    temp_root = tempfile.mkdtemp(prefix="citius_uc_profile_")
    TEMP_PROFILE_DIRS.append(temp_root)

    # File penting global state browser.
    for filename in ("Local State",):
        src = os.path.join(user_data_dir, filename)
        dst = os.path.join(temp_root, filename)
        if os.path.isfile(src):
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass

    # Tentukan folder profile sumber.
    source_profile = profile_dir or "Default"
    src_profile_path = os.path.join(user_data_dir, source_profile)
    if not os.path.isdir(src_profile_path):
        source_profile = "Default"
        src_profile_path = os.path.join(user_data_dir, source_profile)
    if not os.path.isdir(src_profile_path):
        # Tidak ada profile valid, balik ke aslinya.
        return user_data_dir, profile_dir

    dst_profile_path = os.path.join(temp_root, source_profile)
    shutil.copytree(src_profile_path, dst_profile_path, dirs_exist_ok=True)
    return temp_root, source_profile


def find_free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return int(port)


def wait_devtools_ready(port, timeout=35):
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/json/version"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                data = resp.read().decode("utf-8", errors="replace")
                if "webSocketDebuggerUrl" in data:
                    return True
        except Exception:
            pass
        sleep(0.5)
    return False


def _parse_remote_debug_port(cmdline):
    for arg in cmdline or []:
        if not isinstance(arg, str):
            continue
        if arg.startswith("--remote-debugging-port="):
            raw = arg.split("=", 1)[1].strip()
            try:
                port = int(raw)
            except Exception:
                continue
            if 1 <= port <= 65535:
                return port
    return 0


def discover_chrome_debug_ports():
    ports = set()
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            cmdline = proc.info.get("cmdline") or []
            cmdline_text = " ".join(cmdline).lower()
            if not (
                "chrome" in name
                or "chromium" in name
                or "google-chrome" in cmdline_text
                or "chromium" in cmdline_text
            ):
                continue
            port = _parse_remote_debug_port(cmdline)
            if port:
                ports.add(port)
        except Exception:
            continue
    return sorted(ports)


def get_devtools_tab_urls(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1.5) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        if not isinstance(payload, list):
            return []
        urls = []
        for item in payload:
            if isinstance(item, dict):
                url = (item.get("url") or "").strip()
                if url:
                    urls.append(url)
        return urls
    except Exception:
        return []


def find_existing_chrome_debug_port(target_url="", timeout=180):
    target = (target_url or "").strip().lower()
    timeout = max(5, int(timeout))
    deadline = time.time() + timeout
    last_ports = None

    while time.time() < deadline:
        ports = discover_chrome_debug_ports()
        if ports and ports != last_ports:
            print("[INFO] Kandidat remote-debugging port:", ",".join(str(p) for p in ports))
            last_ports = ports

        for port in ports:
            tab_urls = get_devtools_tab_urls(port)
            if not tab_urls:
                continue
            if not target:
                print(f"[INFO] Port attach ditemukan: {port}")
                return port
            for tab_url in tab_urls:
                if target in tab_url.lower():
                    print(f"[INFO] Target URL match di port {port}: {tab_url}")
                    return port
        sleep(1)

    return 0


def make_driver_attach_existing(chrome_bin):
    debug_port_env = (os.environ.get("CHROME_DEBUG_PORT") or "").strip()
    target_url = (os.environ.get("CHROME_ATTACH_TARGET_URL") or "mail.google.com").strip()
    timeout = (os.environ.get("CHROME_ATTACH_TIMEOUT") or "180").strip()
    try:
        timeout_sec = int(timeout)
    except Exception:
        timeout_sec = 180

    debug_port = 0
    if debug_port_env:
        try:
            debug_port = int(debug_port_env)
        except Exception:
            raise RuntimeError(f"CHROME_DEBUG_PORT tidak valid: {debug_port_env}") from None

    if debug_port <= 0:
        print(f"[INFO] Cari Chrome existing untuk attach, target URL: {target_url}")
        debug_port = find_existing_chrome_debug_port(target_url=target_url, timeout=timeout_sec)
        if debug_port <= 0:
            raise RuntimeError(
                "Tidak menemukan Chrome yang bisa di-attach. "
                "Jalankan Chrome manual pakai --remote-debugging-port=<port> "
                "dan buka URL target dulu."
            )

    devtools_ready = wait_devtools_ready(debug_port, timeout=15)
    if not devtools_ready:
        print(
            f"[WARN] DevTools port {debug_port} belum terdeteksi siap via /json/version. "
            "Coba attach langsung."
        )

    attach_options = webdriver.ChromeOptions()
    if chrome_bin:
        attach_options.binary_location = chrome_bin
    attach_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    print(f"[INFO] Attach ke Chrome existing, port={debug_port}")
    try:
        return webdriver.Chrome(options=attach_options)
    except Exception as exc:
        if not devtools_ready:
            raise RuntimeError(
                f"DevTools port {debug_port} tidak siap untuk attach. "
                "Jika pakai Chrome terbaru, jangan gunakan user-data-dir default; "
                "pakai user-data-dir khusus untuk mode remote debugging."
            ) from exc
        raise


def kill_windows_chrome_processes():
    if os.name != "nt":
        return
    for cmd in (
        ["taskkill", "/F", "/IM", "chrome.exe", "/T"],
        ["taskkill", "/F", "/IM", "chromedriver.exe", "/T"],
    ):
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=False)
        except Exception:
            pass
    sleep(1)


def kill_linux_chrome_processes():
    if os.name == "nt":
        return
    killed = 0
    # 1) Coba kill via psutil agar tidak bergantung nama executable tertentu.
    try:
        me = os.getpid()
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                pid = int(proc.info.get("pid") or 0)
                if pid <= 0 or pid == me:
                    continue
                name = (proc.info.get("name") or "").lower()
                cmdline = " ".join(proc.info.get("cmdline") or []).lower()
                is_target = any(token in name for token in ("chrome", "chromedriver", "chromium")) or any(
                    token in cmdline for token in ("google-chrome", "chromedriver", "chromium", "/chrome")
                )
                if not is_target:
                    continue
                proc.kill()
                killed += 1
            except Exception:
                continue
    except Exception:
        pass

    # 2) Fallback tambahan pakai pkill.
    for cmd in (
        ["pkill", "-f", "google-chrome"],
        ["pkill", "-f", "chrome"],
        ["pkill", "-f", "chromium"],
        ["pkill", "-f", "chromedriver"],
    ):
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=False)
        except Exception:
            pass
    sleep(1)
    print(f"[INFO] kill_linux_chrome_processes selesai, target psutil killed={killed}")


def make_driver_windows_attach(chrome_bin, user_data_dir=""):
    if os.name != "nt":
        raise RuntimeError("Mode attach hanya untuk Windows.")
    if not chrome_bin:
        raise RuntimeError("Chrome binary tidak ditemukan.")

    debug_port = find_free_port()
    cmd = [
        chrome_bin,
        f"--remote-debugging-port={debug_port}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if user_data_dir:
        cmd.append(f"--user-data-dir={user_data_dir}")

    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not wait_devtools_ready(debug_port, timeout=35):
        raise RuntimeError(f"DevTools port {debug_port} tidak siap.")

    attach_options = webdriver.ChromeOptions()
    attach_options.binary_location = chrome_bin
    attach_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    driver = webdriver.Chrome(options=attach_options)
    print("[INFO] Fallback attach mode aktif, debugger port:", debug_port)
    return driver


manifest_json = ""
background_js = ""
bot_init = 0

with open("bot_status.txt", "w") as f:
    f.writelines("0")


def set_manifest_json(PROXY_HOST, PROXY_PORT, PROXY_PASS, PROXY_USER):
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """
    return manifest_json


def set_background_js(PROXY_HOST, PROXY_PORT, PROXY_PASS, PROXY_USER):
    background_js = """
    var config = {
            mode: "fixed_servers",
            rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
            },
            bypassList: ["localhost"]
            }
        };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {urls: ["<all_urls>"]},
                ['blocking']
    );
    """ % (PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS)
    return background_js


def shot_api(incident_id, atm_id, problem, token):
    print("shot_api ", incident_id, atm_id, problem)
    url = "https://1gen.citius.co.id/api/shintei/ticket/create/auto"
    myobj = {"incident_id": incident_id, "atm_id": atm_id, "problem": problem}
    headers = {"Authorization": f"Bearer {token}"}
    http_status = None
    response_text = None
    error_detail = None

    while True:
        try:
            x = requests.post(url, data=myobj, headers=headers, timeout=10)
            print("OKEEEE")
            break
        except Exception as e:
            error_detail = str(e)
            print("ULANGGGG", e)
            sleep(5)

    try:
        http_status = x.status_code
        response_text = x.text
        res_json = x.json()
        status = res_json.get("status")
        message = res_json.get("message")
    except Exception as e:
        print("Gagal parsing JSON response:", e)
        status = None
        message = None

    x.close()
    return status, message, http_status, response_text, error_detail


def element_presence(by, by_val, timeout, driver):
    element_present = EC.presence_of_element_located((by, by_val))
    WebDriverWait(driver, timeout).until(element_present)


def check_whitelist_sender_email(email):
    whitelist_email = ["ccugmandiri@gmail.com", "citiusdispatcher@gmail.com"]
    return email in whitelist_email


def get_data_xpath():
    url = "https://1gen.citius.co.id/api/shintei/ticket/mailscrapper_get_xpath"
    x = requests.post(url, data={})
    x.close()
    return json.loads(x.text)


def login(driver_d, data_xpath):
    print(data_xpath["login_username_form"])
    element_presence(By.XPATH, data_xpath["login_username_form"], 30, driver_d)

    driver_d.find_element(By.XPATH, data_xpath["login_username_form"]).send_keys(
        data_xpath["credential_user"] + "\n"
    )
    element_presence(By.XPATH, data_xpath["login_password_form"], 30, driver_d)
    sleep(2)
    driver_d.find_element(By.XPATH, data_xpath["login_password_form"]).send_keys(
        data_xpath["credential_password"] + "\n"
    )

    element_presence(By.XPATH, data_xpath["inbox_button"], 60, driver_d)


def notify_info(message, title="INFO"):
    if win32api is not None:
        try:
            win32api.MessageBox(0, message, title, 0x00001000)
            return
        except Exception:
            pass
    if tk is not None and messagebox is not None:
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            messagebox.showinfo(title, message, parent=root)
            root.destroy()
            return
        except Exception:
            pass
    print(f"[{title}] {message}")


def wait_manual_gmail_login(driver_d):
    login_url = (
        "https://accounts.google.com/v3/signin/identifier?"
        "continue=https%3A%2F%2Fmail.google.com%2Fmail%2F"
        "&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin"
    )
    driver_d.get(login_url)
    while True:
        notify_info("Login manual Gmail dulu. Setelah selesai, klik OK untuk lanjut.", "INFO")
        if has_active_gmail_session(driver_d):
            print("[INFO] Login manual Gmail terdeteksi, lanjut proses.")
            return
        print("[WARN] Sesi Gmail belum aktif. Ulangi login manual.")


def make_driver():
    chrome_bin = resolve_chrome_binary()
    chrome_major = detect_chrome_major(chrome_bin)
    if chrome_major > 0:
        print("AUTO-DETECT CHROME MAJOR:", chrome_major, "binary:", chrome_bin)
    else:
        print("AUTO-DETECT CHROME MAJOR gagal; binary:", chrome_bin or "(tidak ditemukan)")

    if use_existing_chrome_attach_mode():
        return make_driver_attach_existing(chrome_bin)

    # Linux/Ubuntu: pakai UC + profile agar tidak lewat profile picker.
    if os.name != "nt":
        if uc is None:
            raise RuntimeError("undetected-chromedriver belum terpasang. Install: pip install undetected-chromedriver")
        user_data_dir, profile_dir = resolve_linux_chrome_profile()
        if user_data_dir:
            print("[INFO] Linux user-data-dir:", user_data_dir)
        if profile_dir:
            print("[INFO] Linux profile-directory:", profile_dir)

        runtime_user_data = user_data_dir
        runtime_profile_dir = profile_dir
        if os.environ.get("CHROME_CLONE_PROFILE", "1").strip().lower() in {"1", "true", "yes"} and user_data_dir:
            try:
                runtime_user_data, runtime_profile_dir = clone_linux_profile(user_data_dir, profile_dir)
                print("[INFO] Linux runtime cloned user-data-dir:", runtime_user_data)
                if runtime_profile_dir:
                    print("[INFO] Linux runtime cloned profile-directory:", runtime_profile_dir)
            except Exception as exc:
                print("[WARN] Gagal clone profile Linux, pakai profile asli:", exc)

        if os.environ.get("KILL_CHROME_BEFORE_UC", "1").strip().lower() in {"1", "true", "yes"}:
            print("[INFO] Menutup proses chrome/chromedriver lama sebelum UC launch...")
            kill_linux_chrome_processes()

        def build_linux_options():
            opts = uc.ChromeOptions()
            opts.add_argument("--no-first-run")
            opts.add_argument("--no-default-browser-check")
            opts.add_argument("--disable-popup-blocking")
            opts.add_argument("--password-store=basic")
            # Stabilitas Linux (WSL/container/VM)
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--remote-allow-origins=*")
            opts.add_argument("--disable-background-networking")
            if chrome_bin:
                opts.binary_location = chrome_bin
            if runtime_profile_dir:
                opts.add_argument(f"--profile-directory={runtime_profile_dir}")
            return opts

        base_kwargs = {"options": build_linux_options()}
        if chrome_bin:
            base_kwargs["browser_executable_path"] = chrome_bin
        if runtime_user_data:
            # Gunakan parameter resmi UC agar manajemen profile lebih stabil.
            base_kwargs["user_data_dir"] = runtime_user_data
        if chrome_major > 0:
            base_kwargs["version_main"] = chrome_major

        attempt_plan = [
            ("UC attempt-1 use_subprocess=True", {"use_subprocess": True, "drop_version_main": False}),
            ("UC attempt-2 use_subprocess=False", {"use_subprocess": False, "drop_version_main": False}),
            ("UC attempt-3 tanpa version_main", {"use_subprocess": True, "drop_version_main": True}),
        ]
        last_exc = None
        for idx, (label, conf) in enumerate(attempt_plan, start=1):
            kwargs = dict(base_kwargs)
            kwargs["options"] = build_linux_options()
            kwargs["use_subprocess"] = conf["use_subprocess"]
            if conf["drop_version_main"]:
                kwargs.pop("version_main", None)
            try:
                print(f"[INFO] {label}")
                return uc.Chrome(**kwargs)
            except Exception as exc:
                last_exc = exc
                print(f"[WARN] {label} gagal: {exc}")
                if idx < len(attempt_plan):
                    if os.environ.get("KILL_CHROME_BEFORE_UC_RETRY", "1").strip().lower() in {"1", "true", "yes"}:
                        print("[INFO] Menutup proses chrome/chromedriver lama sebelum retry...")
                        kill_linux_chrome_processes()

        # Last resort: native Selenium Chrome dengan profile yang sama.
        print("[WARN] Semua percobaan UC gagal, fallback ke Selenium native.")
        native_opts = webdriver.ChromeOptions()
        native_opts.add_argument("--no-first-run")
        native_opts.add_argument("--no-default-browser-check")
        native_opts.add_argument("--disable-popup-blocking")
        native_opts.add_argument("--disable-dev-shm-usage")
        native_opts.add_argument("--no-sandbox")
        native_opts.add_argument("--disable-gpu")
        if chrome_bin:
            native_opts.binary_location = chrome_bin
        if runtime_user_data:
            native_opts.add_argument(f"--user-data-dir={runtime_user_data}")
        if runtime_profile_dir:
            native_opts.add_argument(f"--profile-directory={runtime_profile_dir}")
        try:
            return webdriver.Chrome(options=native_opts)
        except Exception:
            if last_exc is not None:
                raise last_exc
            raise

    # Windows: opsional pakai UC + profile persisten (default untuk GUI Citius).
    if os.name == "nt" and env_truthy("CHROME_WINDOWS_UC", "0"):
        if uc is None:
            raise RuntimeError("undetected-chromedriver belum terpasang. Install: pip install undetected-chromedriver")

        local_app_data = os.environ.get("LOCALAPPDATA", "")
        default_user_data = (
            os.path.join(local_app_data, "CitiusBossAuto", "acrea_profile") if local_app_data else ""
        )
        user_data_dir = (os.environ.get("CHROME_USER_DATA_DIR") or default_user_data).strip()
        profile_dir = (os.environ.get("CHROME_PROFILE_DIR") or "Default").strip()
        if user_data_dir:
            try:
                os.makedirs(user_data_dir, exist_ok=True)
            except Exception:
                pass
            print("[INFO] Windows UC user-data-dir:", user_data_dir)
        if profile_dir:
            print("[INFO] Windows UC profile-directory:", profile_dir)

        retry_enabled = env_truthy("CHROME_WINDOWS_UC_RETRY", "1")
        fallback_native = env_truthy("CHROME_WINDOWS_UC_FALLBACK_NATIVE", "1")
        no_subprocess_first = env_truthy("CHROME_WINDOWS_UC_NO_SUBPROCESS_FIRST", "1")
        print("[INFO] Windows UC mode aktif.")

        def build_windows_uc_options():
            opts = uc.ChromeOptions()
            opts.add_argument("--no-first-run")
            opts.add_argument("--no-default-browser-check")
            opts.add_argument("--disable-popup-blocking")
            opts.add_argument("--password-store=basic")
            opts.add_argument("--remote-allow-origins=*")
            if chrome_bin:
                opts.binary_location = chrome_bin
            if user_data_dir:
                opts.add_argument(f"--user-data-dir={user_data_dir}")
            if profile_dir:
                opts.add_argument(f"--profile-directory={profile_dir}")
            return opts

        tried = set()
        attempts = []

        def push_attempt(label, use_subprocess, version_main):
            key = (bool(use_subprocess), int(version_main or 0))
            if key in tried:
                return
            tried.add(key)
            attempts.append((label, bool(use_subprocess), int(version_main or 0)))

        first_use_subprocess = not no_subprocess_first
        first_label = (
            "Windows UC attempt-1 use_subprocess=True"
            if first_use_subprocess
            else "Windows UC attempt-1 use_subprocess=False"
        )
        push_attempt(first_label, first_use_subprocess, chrome_major)
        if retry_enabled:
            second_use_subprocess = not first_use_subprocess
            second_label = (
                "Windows UC attempt-2 use_subprocess=True"
                if second_use_subprocess
                else "Windows UC attempt-2 use_subprocess=False"
            )
            push_attempt(second_label, second_use_subprocess, chrome_major)
            push_attempt("Windows UC attempt-3 tanpa version_main", True, 0)
            push_attempt("Windows UC attempt-4 tanpa version_main + use_subprocess=False", False, 0)

        idx = 0
        last_exc = None
        while idx < len(attempts):
            label, use_subprocess, version_main = attempts[idx]
            idx += 1
            kwargs = {
                "options": build_windows_uc_options(),
                "use_subprocess": use_subprocess,
            }
            if chrome_bin:
                kwargs["browser_executable_path"] = chrome_bin
            if version_main > 0:
                kwargs["version_main"] = version_main
            try:
                print(f"[INFO] {label}")
                return uc.Chrome(**kwargs)
            except Exception as exc:
                last_exc = exc
                print(f"[WARN] {label} gagal: {exc}")
                browser_major = extract_browser_major_from_error(exc)
                if retry_enabled and browser_major > 0 and browser_major != version_main:
                    push_attempt(
                        f"Windows UC retry browser major={browser_major} use_subprocess=True",
                        True,
                        browser_major,
                    )
                    push_attempt(
                        f"Windows UC retry browser major={browser_major} use_subprocess=False",
                        False,
                        browser_major,
                    )

        if not fallback_native:
            if last_exc is not None:
                raise last_exc
            raise RuntimeError("Windows UC gagal membuat sesi browser.")
        print("[WARN] Semua percobaan Windows UC gagal, fallback ke Selenium native.")

    # Windows native Selenium + fallback attach.
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disable-popup-blocking")

    if chrome_bin:
        chrome_options.binary_location = chrome_bin

    user_data_dir = ""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    default_user_data = (
        os.path.join(local_app_data, "Google", "Chrome", "User Data") if local_app_data else ""
    )
    user_data_dir = (os.environ.get("CHROME_USER_DATA_DIR") or default_user_data).strip()
    if user_data_dir and os.path.isdir(user_data_dir):
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        print("[INFO] Chrome user-data-dir:", user_data_dir)

    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as exc:
        msg = str(exc).lower()
        if "user data directory is already in use" in msg or "profile appears to be in use" in msg:
            raise RuntimeError(
                "Chrome profile sedang dipakai proses lain. Tutup semua Chrome lalu jalankan ulang."
            ) from exc
        if "devtoolsactiveport file doesn't exist" in msg:
            print("[WARN] Native ChromeDriver gagal (DevToolsActivePort). Coba fallback attach mode.")
            if os.environ.get("KILL_CHROME_BEFORE_ATTACH", "1").strip().lower() in {"1", "true", "yes"}:
                print("[INFO] Menutup proses Chrome/ChromeDriver lama sebelum attach...")
                kill_windows_chrome_processes()
            return make_driver_windows_attach(chrome_bin, user_data_dir=user_data_dir)
        raise
    print("[INFO] Selenium native Chrome mode aktif.")
    return driver


def wait_for_windows_profile_selection(driver_d):
    if os.name != "nt":
        return True
    if os.environ.get("DISABLE_PROFILE_PICKER_WAIT", "").strip().lower() in {"1", "true", "yes"}:
        return True

    timeout = 180
    try:
        timeout = int(os.environ.get("PROFILE_PICKER_TIMEOUT", "180"))
    except Exception:
        timeout = 180
    if timeout <= 0:
        return True

    print(f"[INFO] Pilih profil Chrome dulu (timeout {timeout} detik)...")
    deadline = time.time() + timeout
    selected_handle = None
    force_picker = os.environ.get("FORCE_PROFILE_PICKER", "1").strip().lower() in {"1", "true", "yes"}
    force_picker_done = False

    while time.time() < deadline:
        if force_picker and not force_picker_done:
            try:
                driver_d.get("chrome://profile-picker/")
            except Exception as exc:
                print("[INFO] gagal force buka profile picker:", exc)
            force_picker_done = True

        try:
            handles = list(driver_d.window_handles)
        except Exception:
            break

        for handle in handles:
            try:
                driver_d.switch_to.window(handle)
                current_url = (driver_d.current_url or "").lower()
            except Exception:
                continue
            if not current_url.startswith("chrome://profile-picker"):
                selected_handle = handle
                break

        if selected_handle:
            break
        sleep(1)

    if not selected_handle:
        print("[WARN] Timeout pilih profil, lanjut otomatis.")
        return True

    # Jangan menutup window apa pun di tahap ini. Menutup handle yang salah bisa
    # memutus sesi WebDriver (InvalidSessionId) setelah profile picker.
    try:
        driver_d.switch_to.window(selected_handle)
        _ = driver_d.current_url
    except Exception as exc:
        print("[WARN] Sesi WebDriver tidak valid setelah pilih profil:", exc)
        return False

    print("[INFO] Profil dipilih, lanjut proses.")
    return True


def has_active_gmail_session(driver_d):
    inbox_url = "https://mail.google.com/mail/u/0/#inbox"

    def _is_logged_url():
        try:
            current = (driver_d.current_url or "").lower()
        except Exception:
            return False
        return ("mail.google.com" in current) and ("accounts.google.com" not in current)

    if _is_logged_url():
        return True

    try:
        driver_d.get(inbox_url)
    except Exception:
        return False

    deadline = time.time() + 15
    while time.time() < deadline:
        if _is_logged_url():
            return True
        sleep(1)
    return False


def is_driver_alive(driver_d):
    try:
        _ = driver_d.current_url
        driver_d.execute_script("return document.readyState")
        return True
    except Exception:
        return False


def is_session_lost_error(exc):
    text = (str(exc) or "").lower()
    markers = (
        "invalid session id",
        "no such window",
        "target window already closed",
        "disconnected",
        "session deleted",
        "chrome not reachable",
    )
    return any(m in text for m in markers)


def ensure_gmail_inbox_ready(driver_d, data_xpath, timeout=35):
    inbox_url = "https://mail.google.com/mail/u/0/#inbox"
    deadline = time.time() + max(8, int(timeout))
    last_err = None
    while time.time() < deadline:
        try:
            if not has_active_gmail_session(driver_d):
                driver_d.get(inbox_url)
                sleep(1.5)

            inbox_btn_xpath = data_xpath.get("inbox_button")
            top_list_xpath = data_xpath.get("top_mail_list")

            if inbox_btn_xpath:
                element_presence(By.XPATH, inbox_btn_xpath, 20, driver_d)
            if top_list_xpath:
                element_presence(By.XPATH, top_list_xpath, 20, driver_d)
            return True
        except Exception as exc:
            last_err = exc
            try:
                driver_d.get(inbox_url)
            except Exception:
                pass
            sleep(2)
    print("[WARN] Inbox Gmail belum siap:", last_err)
    return False


def run():
    # proxy kamu gak dipakai, jadi diabaikan
    driver_d = make_driver()
    if (
        os.name == "nt"
        and not use_existing_chrome_attach_mode()
        and not env_truthy("CHROME_WINDOWS_UC", "0")
    ):
        session_ok = wait_for_windows_profile_selection(driver_d)
        if not session_ok:
            print("[INFO] Re-init driver setelah profile picker.")
            try:
                driver_d.quit()
            except Exception:
                pass
            driver_d = make_driver()

    if has_active_gmail_session(driver_d):
        print("[INFO] Sesi Gmail aktif, lewati login form.")
    else:
        wait_manual_gmail_login(driver_d)

    while True:
        try:
            if not is_driver_alive(driver_d):
                print("[WARN] Session browser terputus, inisialisasi ulang driver...")
                try:
                    driver_d.quit()
                except Exception:
                    pass
                driver_d = make_driver()

            data_xpath = get_data_xpath()
            if not ensure_gmail_inbox_ready(driver_d, data_xpath, timeout=35):
                print("[WARN] Inbox belum siap, minta login manual ulang.")
                wait_manual_gmail_login(driver_d)
                continue

            # scroll to top
            try:
                driver_d.execute_script(
                    'document.getElementById("'
                    + driver_d.find_element(By.XPATH, data_xpath["top_mail_list"]).get_attribute("id")
                    + '").scrollTop=0'
                )
            except Exception as e:
                print(e)
                print("ERROR_CODE : top_mail_list 001 \n contact your IT Staff")
                sleep(5)

            for x in range(20):
                print("X = " + str(x))
                try:
                    subject_email = driver_d.find_element(
                        By.XPATH,
                        data_xpath["subject_mail_list"].replace("replace_with_detail_row", str(x + 1)),
                    )
                    print("subject_email ", subject_email.text)
                except Exception as e:
                    print(e)
                    print("ERROR_CODE : subject_mail_list 001 \n contact your IT Staff")
                    sleep(2)
                    continue

                try:
                    sender_el = driver_d.find_element(
                        By.XPATH,
                        data_xpath["sender_mail_list"].replace("replace_with_detail_row", str(x + 1)),
                    )
                    sender_email = sender_el.get_attribute("email")

                    # ✅ FIX LOGIC PRIORITY (biar TIKET gak lolos tanpa whitelist)
                    if check_whitelist_sender_email(sender_email) and (
                        ("New Incident" in subject_email.text) or ("TIKET" in subject_email.text)
                    ):
                        print("class sender ", sender_el.get_attribute("class"))

                        if sender_el.get_attribute("class") == "zF":
                            # click email
                            while True:
                                try:
                                    sender_el.click()
                                    break
                                except Exception as e:
                                    try:
                                        driver_d.execute_script(
                                            'document.getElementById("'
                                            + driver_d.find_element(
                                                By.XPATH,
                                                data_xpath["row_mail_list"].replace("replace_with_detail_row", str(x + 1)),
                                            ).get_attribute("id")
                                            + '").scrollIntoView()'
                                        )
                                    except Exception:
                                        pass
                                    print("try click again\n", e)

                            element_presence(By.XPATH, data_xpath["body_email"], 30, driver_d)
                            body_email_text = driver_d.find_element(By.XPATH, data_xpath["body_email"]).text

                            if ("TIKET :" in body_email_text) and ("ATM ID :" in body_email_text):
                                if "STATUS :" not in body_email_text:
                                    incident_id = body_email_text.split("TIKET : ")[1].strip().split("\n")[0]
                                    atm_id = body_email_text.split("ATM ID : ")[1].strip().split("\n")[0]
                                    problem = body_email_text.split("PROBLEM : ")[1].strip().split("\n")[0]

                                    while True:
                                        status, message, http_status, response_text, error_detail = shot_api(
                                            incident_id, atm_id, problem, data_xpath["token"]
                                        )
                                        if status in (0, 1):
                                            print("API:", status, message)
                                            break
                                        print(
                                            "API error, retry...",
                                            "status=", status,
                                            "message=", message,
                                            "http_status=", http_status,
                                            "response_text=", response_text,
                                            "error_detail=", error_detail,
                                        )
                                        sleep(10)

                            driver_d.find_element(By.XPATH, data_xpath["inbox_button"]).click()
                            sleep(2)
                            print("OK")

                except Exception as e:
                    print(e)

            driver_d.find_element(By.XPATH, data_xpath["inbox_button"]).click()
            sleep(2)

        except Exception as e:
            print("error ni")
            print(e)
            if is_session_lost_error(e):
                print("[WARN] Sesi browser hilang, re-init driver...")
                try:
                    driver_d.quit()
                except Exception:
                    pass
                driver_d = make_driver()
                if has_active_gmail_session(driver_d):
                    print("[INFO] Sesi Gmail aktif setelah re-init.")
                else:
                    wait_manual_gmail_login(driver_d)
            sleep(2)


if __name__ == "__main__":
    run()
