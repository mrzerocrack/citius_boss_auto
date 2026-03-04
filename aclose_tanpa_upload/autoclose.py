import zipfile
from selenium import webdriver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
import sys
import datetime
import re
from time import *
import os
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import Proxy, ProxyType
import random
import secrets
import string
import requests
import json
import pandas as pd
import psutil
import openpyxl
import json,urllib.request
import pickle
from PIL import Image
import subprocess
import shutil
import tkinter as tk
from tkinter import messagebox

try:
	import win32api  # type: ignore
except Exception:
	win32api = None


#DATE TIME GMT DAN LOCAL
# print("\nGMT: "+time.strftime("%a, %d %b %Y %I:%M:%S %p %Z", time.gmtime()))
# print("Local: "+strftime("%a, %d %b %Y %I:%M:%S %p %Z\n"))
def resolve_chrome_binary():
	candidates = []
	if os.name == "nt":
		local_app_data = os.environ.get("LOCALAPPDATA", "")
		program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
		program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
		candidates.extend(
			[
				shutil.which("chrome"),
				shutil.which("chrome.exe"),
				os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe") if local_app_data else "",
				os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
				os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
			]
		)
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


def default_windows_uc_user_data_dir():
	if os.name != "nt":
		return ""
	override = (os.environ.get("CHROME_USER_DATA_DIR") or "").strip()
	if override:
		return override
	local_app_data = os.environ.get("LOCALAPPDATA", "")
	if not local_app_data:
		return ""
	module_tag = f"{os.path.basename(os.path.dirname(__file__))}_{os.path.splitext(os.path.basename(__file__))[0]}"
	return os.path.join(local_app_data, "CitiusBossAuto", "uc_profiles", module_tag)


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
		# Windows: baca versi dari metadata file executable agar tidak memicu spawn Chrome.
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
	except Exception:
		return 0
	return _extract_chrome_major(f"{proc.stdout}\n{proc.stderr}")


def build_uc_driver(chrome_options):
	driver_kwargs = {"options": chrome_options}
	chrome_bin = resolve_chrome_binary()
	if chrome_bin:
		chrome_options.binary_location = chrome_bin
		driver_kwargs["browser_executable_path"] = chrome_bin
	if os.name == "nt":
		user_data_dir = default_windows_uc_user_data_dir()
		profile_dir = (os.environ.get("CHROME_PROFILE_DIR") or "Default").strip()
		if user_data_dir:
			try:
				os.makedirs(user_data_dir, exist_ok=True)
			except Exception:
				pass
			chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
			print("WINDOWS UC user-data-dir:", user_data_dir)
		if profile_dir:
			chrome_options.add_argument(f"--profile-directory={profile_dir}")
			print("WINDOWS UC profile-directory:", profile_dir)
		chrome_options.add_argument("--no-first-run")
		chrome_options.add_argument("--no-default-browser-check")
	chrome_major = detect_chrome_major(chrome_bin)
	if chrome_major > 0:
		driver_kwargs["version_main"] = chrome_major
		print("AUTO-DETECT CHROME MAJOR:", chrome_major, "binary:", chrome_bin)
	else:
		print("AUTO-DETECT CHROME MAJOR gagal, lanjut default UC")
	try:
		return uc.Chrome(**driver_kwargs)
	except Exception as exc:
		if os.name == "nt":
			raise
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
stop = False
def shot_api(incident_id, atm_id, problem):
	print('shot_api ',incident_id,atm_id,problem)
	url = 'https://boss.citius.co.id/api/create-ticket'
	myobj = {'incident_id':incident_id, 'atm_id':atm_id, 'problem':problem}
	x = requests.post(url, data = myobj)
	x.close()
	return x.text

def element_presence(by,by_val,time, driver):
	element_present = EC.presence_of_element_located((by, by_val))
	try:
		WebDriverWait(driver, time).until(element_present)
	except Exception as e:
		print (e)
	else:
		pass

def run():

	dataframe = openpyxl.load_workbook('doc.xlsx')
	dataframe1 = dataframe.active
	conti_last_proc = False
	last_proc = ""
	try:
		last_proc = open("last_line_proccessed.txt","r").readline()
		conti_last_proc = True
	except Exception as e:
		pass

	# for row in range(0, dataframe1.max_row):
	# 	print(dataframe1[row])
	# 	for col in dataframe1.iter_cols(1, dataframe1.max_column):
	# 		print(col[row].value)
	# 	input("enter")
	# tab = sys.argv[1]
	chrome_options = uc.ChromeOptions()
	chrome_options.add_argument("--incognito")
	chrome_options.add_argument('--headless')
	#chrome_options.add_argument('--no-sandbox')
	#chrome_options.add_argument('--proxy-server='+input_proxy.split("-")[0])
	driver_d = build_uc_driver(chrome_options)
	driver_d.maximize_window()
	has_cookie = 0
	driver_d.get("https://app.slmugmandiri.co.id/sistrack_new/")
	login(driver_d)
	show_notif_captcha()
	line_no = 0
	for data in dataframe1:
		try:
			line_no += 1
			ebs = data[2].value
			reason = data[3].value
			if conti_last_proc:
				if str(line_no) == last_proc:
					conti_last_proc = False
				else:
					print("SKIPPING LINE",line_no)
					continue
			if "-" not in ebs:
				continue
			print("PROCCESSING ",ebs)
			driver_d.get("https://app.slmugmandiri.co.id/sistrack_new/Home")
	
			element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[1]/div[2]/div/label/input", 30, driver_d)
			driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[1]/div[2]/div/label/input").send_keys(ebs+"\n")

			xpath_status_text = "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr[1]/td[3]/h3"
			while True:
				sleep(1)
				try:
					driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr[2]/td[1]")
					driver_d.find_element(By.XPATH, xpath_status_text)
					print("ADA")
				except Exception as e:
					break

			element_presence(By.XPATH, xpath_status_text, 30, driver_d)

			if driver_d.find_element(By.XPATH, xpath_status_text).text != "CLOSED":
				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr/td[1]/a").click()
				element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[1]/td[2]", 30, driver_d)
				sleep(2)
				try:
					btn_suspen = driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[3]/div/div/a");
					if "Open Suspend" in btn_suspen.text:
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[3]/div/div/a").click()
						element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[1]/div/div", 30, driver_d)
				except Exception as e:
					pass

				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[1]/td[2]/input").send_keys("-")

				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[2]/td[2]/select").click()
				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[2]/td[2]/select/option[2]").click()

				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[3]/td[2]/input").send_keys("-")

				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[4]/td[2]/select").click()
				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[4]/td[2]/select/option[2]").click()

				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[5]/td[2]/input").send_keys("-")

				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[6]/td[2]/select").click()
				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[6]/td[2]/select/option[2]").click()

				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[7]/td[2]/input").send_keys("-")

				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[8]/td[2]/select").click()
				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[8]/td[2]/select/option[2]").click()
				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[2]/table/tbody/tr[6]/td/input").send_keys("-")

				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[2]/table/tbody/tr[8]/td/textarea").send_keys(reason)

				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[3]/button").click()
				element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[1]/div/div", 30, driver_d)
				sleep(2)
				driver_d.refresh()
				element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[1]/td[2]", 30, driver_d)

				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[1]/div[2]/table/tbody/tr[4]/td[2]/div/div[1]/select").click()
				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[1]/div[2]/table/tbody/tr[4]/td[2]/div/div[1]/select/option[6]").click()
				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[1]/div[2]/table/tbody/tr[4]/td[2]/div/div[2]/button").click()
				element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[1]/div/div", 30, driver_d)
			open("last_line_proccessed.txt","w").writelines(str(line_no))

			if int(line_no) == int(dataframe1.max_row):
				stop = True
				print("sini", stop)
				driver_d.quit()
				print("DONE")
				open("last_line_proccessed.txt","w").writelines("1")
				open("log_status.txt","w").writelines("DONE")
				break

		except Exception as e:
			open("ticket_error.txt","a").writelines(ebs+"-EXCEPTION\n"+str(e)+"\n\n")
			driver_d.quit()
			break

			
# def check_whitelist_sender_email(email):
# 	url = 'https://boss.citius.co.id/api/check-whitelist-email'
# 	myobj = {'email':email}
# 	while True:
# 		try:
# 			x = requests.post(url, data = myobj)
# 			x.close()
# 			if 'ok' in x.text:
# 				return True;
# 			return False;
# 		except Exception as e:
# 			print('EERORRR', e)

def check_whitelist_sender_email(email):
	whitelist_email = ['ccugmandiri@gmail.com', 'citiusdispatcher@gmail.com']
	for x in whitelist_email:
		if email == x:
			return True
	return False

def download(url, name):
	while True:
		try:
			response = requests.get(url, verify=False, timeout=10)
			print("OKEEEE")
			open(name, "wb").write(response.content)
			break
		except Exception as e:
			print("ULANGGGG")
			sleep(5)

def shot_url(url):
	while True:
		try:
			myobj = {}
			x = requests.get(url, verify=False, timeout=10)
			x.close()
			break
		except Exception as e:
			print("ULANGGGG")
			sleep(5)

def get_data_api(url):
	while True:
		try:
			x = requests.get(url, verify=False, timeout=10)
			x.close()
			return json.loads(x.text)
			break
		except Exception as e:
			print("ULANGGGG")
			sleep(5)

def post_data_api(url):
	while True:
		try:
			x = requests.post(url, data = myobj, verify=False, timeout=10)
			x.close()
			return json.loads(x.text)
			break
		except Exception as e:
			print("ULANGGGG")
			sleep(5)

def login(driver_d):
	element_presence(By.XPATH, "/html/body/div[2]/form/div[1]/input", 30, driver_d)
	try:
		driver_d.find_element(By.XPATH, "/html/body/div[2]/form/div[1]/input").send_keys("CC CTS 3")
		element_presence(By.XPATH, "/html/body/div[2]/form/div[2]/input", 30, driver_d)
		sleep(2)
		driver_d.find_element(By.XPATH, "/html/body/div[2]/form/div[2]/input").send_keys("123456")
	except Exception as e:
		print(e)

def show_notif_captcha():
	# notification = tk.Toplevel()
	# notification.title("Peringatan")
	# notification.geometry("300x100")

	# # Label untuk pesan
	# label = tk.Label(notification, text="klik OK kalau sudah login")
	# label.pack(pady=10)

	# # Tombol OK
	# ok_button = tk.Button(notification, text="OK", command=lambda: is_login_(notification))
	# ok_button.pack()
	notify_info("Login manual, klo dah sukses login klik OK dibawah", "INFO")


def notify_info(message, title="INFO"):
	if win32api is not None:
		try:
			win32api.MessageBox(0, message, title, 0x00001000)
			return
		except Exception:
			pass
	try:
		root = tk.Tk()
		root.withdraw()
		root.attributes("-topmost", True)
		messagebox.showinfo(title, message, parent=root)
		root.destroy()
	except Exception:
		print(f"[{title}] {message}")


while True:
	open("log_status.txt","w").writelines("ONPROGRESS")
	try:
		run()
		progres = open("log_status.txt","r").readline()
		if progres == "DONE":
			break
	except Exception as e:
		print(e)
		input("error")
