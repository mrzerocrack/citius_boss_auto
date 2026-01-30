import zipfile
import os
import sys
import datetime
import re
from time import sleep, strftime
import random
import secrets
import string
import requests
import json
import psutil
import urllib.request
import pickle
from PIL import Image

import undetected_chromedriver as uc  # ✅ pakai ini, bukan "from undetected_chromedriver import Chrome"

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# =========================
# CONFIG
# =========================
CHROME_MAJOR_VERSION = 144  # ✅ KUNCI UC ke chromedriver 144

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

    # ✅ KUNCI chromedriver major version = 144
    driver = uc.Chrome(
        options=chrome_options,
        version_main=CHROME_MAJOR_VERSION
    )
    return driver


def run():
    # proxy kamu gak dipakai, jadi diabaikan
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
