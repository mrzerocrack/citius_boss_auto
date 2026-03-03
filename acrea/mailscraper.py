import zipfile
import os
import sys
import datetime
import re
import time
import socket
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

import undetected_chromedriver as uc  # ✅ pakai ini, bukan "from undetected_chromedriver import Chrome"

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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
            if callable(finder):
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
    try:
        proc = subprocess.run([chrome_bin, "--version"], capture_output=True, text=True, check=False, timeout=8)
        major = _extract_chrome_major(f"{proc.stdout}\n{proc.stderr}")
        if major > 0:
            return major
    except Exception:
        pass

    if os.name == "nt":
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
    return 0


def find_free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return int(port)


def wait_devtools_ready(port, timeout=25):
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


def make_driver_windows_attach(chrome_bin):
    if not chrome_bin:
        raise RuntimeError("Chrome binary tidak ditemukan untuk mode attach Windows.")

    debug_port = 0
    try:
        debug_port = int(os.environ.get("CHROME_DEBUG_PORT", "0"))
    except Exception:
        debug_port = 0
    if debug_port <= 0:
        debug_port = find_free_port()

    launch_cmd = [
        chrome_bin,
        f"--remote-debugging-port={debug_port}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    subprocess.Popen(launch_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not wait_devtools_ready(debug_port, timeout=25):
        raise RuntimeError(f"DevTools port {debug_port} tidak siap.")

    options = webdriver.ChromeOptions()
    options.binary_location = chrome_bin
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    driver = webdriver.Chrome(options=options)
    print("[INFO] Windows attach mode aktif, debugger port:", debug_port)
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


def make_driver():
    # ✅ jangan pakai selenium Options(), pakai uc.ChromeOptions()
    chrome_options = uc.ChromeOptions()
    # chrome_options.add_argument("--incognito")  # optional
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disable-popup-blocking")

    chrome_bin = resolve_chrome_binary()
    chrome_major = detect_chrome_major(chrome_bin)
    if chrome_major > 0:
        print("AUTO-DETECT CHROME MAJOR:", chrome_major, "binary:", chrome_bin)
    else:
        print("AUTO-DETECT CHROME MAJOR gagal; binary:", chrome_bin or "(tidak ditemukan)")

    # Mode Windows: attach ke instance Chrome yang sama agar tidak double-spawn.
    use_attach_mode = os.name == "nt" and os.environ.get("DISABLE_WINDOWS_ATTACH_MODE", "").strip().lower() not in {
        "1",
        "true",
        "yes",
    }
    if use_attach_mode:
        return make_driver_windows_attach(chrome_bin)

    driver_kwargs = {"options": chrome_options, "use_subprocess": False}
    if chrome_bin:
        chrome_options.binary_location = chrome_bin
        driver_kwargs["browser_executable_path"] = chrome_bin
    if chrome_major > 0:
        driver_kwargs["version_main"] = chrome_major

    try:
        return uc.Chrome(**driver_kwargs)
    except Exception as exc:
        # Fallback jika UC mengambil driver major yang tidak cocok.
        msg = str(exc)
        m = re.search(r"Current browser version is (\d+)\.", msg)
        if m:
            retry_major = int(m.group(1))
            if driver_kwargs.get("version_main") != retry_major:
                print("RETRY UC DENGAN version_main:", retry_major)
                retry_options = uc.ChromeOptions()
                for arg in getattr(chrome_options, "arguments", []):
                    retry_options.add_argument(arg)
                if chrome_bin:
                    retry_options.binary_location = chrome_bin
                retry_kwargs = dict(driver_kwargs)
                retry_kwargs["options"] = retry_options
                retry_kwargs["version_main"] = retry_major
                return uc.Chrome(**retry_kwargs)
        raise


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
    force_picker = os.environ.get("FORCE_PROFILE_PICKER", "").strip().lower() in {"1", "true", "yes"}
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


def run():
    # proxy kamu gak dipakai, jadi diabaikan
    driver_d = make_driver()
    session_ok = wait_for_windows_profile_selection(driver_d)
    if not session_ok:
        print("[INFO] Re-init driver setelah profile picker.")
        try:
            driver_d.quit()
        except Exception:
            pass
        driver_d = make_driver()

    driver_d.get("https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2F&dsh=S-1238628894%3A1769658398148796&ifkv=AXbMIuCW7KLzC_Q8mlpZpr6v_D4HrrIY3tiSN98tJOblxewSwhjwofLkDRONKYNNaEXG-imVAlkN&rip=1&sacu=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin")

    data_xpath = get_data_xpath()
    login(driver_d, data_xpath)

    while True:
        data_xpath = get_data_xpath()
        try:
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
            sleep(2)


if __name__ == "__main__":
    run()
