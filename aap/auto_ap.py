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
import psutil
import json,urllib.request
import pickle
from PIL import Image
import tkinter as tk
from tkinter import messagebox
import threading
import subprocess

try:
	import win32api  # type: ignore
except Exception:
	win32api = None
import shutil


#DATE TIME GMT DAN LOCAL
# print("\nGMT: "+time.strftime("%a, %d %b %Y %I:%M:%S %p %Z", time.gmtime()))
# print("Local: "+strftime("%a, %d %b %Y %I:%M:%S %p %Z\n"))

def resolve_chrome_binary():
	candidates = []
	if os.name == "nt":
		candidates.extend(
			[
				shutil.which("chrome"),
				shutil.which("chrome.exe"),
				r"C:\Program Files\Google\Chrome\Application\chrome.exe",
				r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
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
	for path in candidates:
		if path and os.path.exists(path):
			return path
	return ""


def detect_chrome_major(chrome_bin):
	if not chrome_bin:
		return 0
	try:
		proc = subprocess.run([chrome_bin, "--version"], capture_output=True, text=True, check=False)
	except Exception:
		return 0
	raw = f"{proc.stdout}\n{proc.stderr}"
	m = re.search(r"(\d+)\.\d+\.\d+\.\d+", raw)
	if not m:
		return 0
	try:
		return int(m.group(1))
	except Exception:
		return 0


def build_uc_driver(chrome_options):
	driver_kwargs = {"options": chrome_options}
	chrome_bin = resolve_chrome_binary()
	if chrome_bin:
		chrome_options.binary_location = chrome_bin
		driver_kwargs["browser_executable_path"] = chrome_bin
	chrome_major = detect_chrome_major(chrome_bin)
	if chrome_major > 0:
		driver_kwargs["version_main"] = chrome_major
		print("AUTO-DETECT CHROME MAJOR:", chrome_major)
	return uc.Chrome(**driver_kwargs)

def shot_api(incident_id, atm_id, problem):
	print('shot_api ',incident_id,atm_id,problem)
	url = 'https://boss.citius.co.id/api/create-ticket'
	myobj = {'incident_id':incident_id, 'atm_id':atm_id, 'problem':problem}
	x = requests.post(url, data = myobj, verify=False)
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
	# tab = sys.argv[1]
	chrome_options = uc.ChromeOptions()
	chrome_options.add_argument("--incognito")
	#chrome_options.add_argument('--no-sandbox')
	#chrome_options.add_argument('--headless')
	#chrome_options.add_argument('--proxy-server='+input_proxy.split("-")[0])
	global driver_d
	driver_d = build_uc_driver(chrome_options)
	
	
	driver_d.get("https://sistrack.ugarta.co.id/sistrack_new/")
	login(driver_d)
	show_notif_captcha()
	while True:
		sleep(10)
		print("START JOB")
		get_tiket = get_data_api('https://1gen.citius.co.id/api/shintei/autotools/get_appointment_ticket_list')
		for tiket in get_tiket:
			try:
				cek_accept = crosscheck_ticket(tiket)
				if(cek_accept["status"] == 0):
					shot_url("https://1gen.citius.co.id/api/shintei/autotools/delete_appointment_from_list/"+str(tiket))
					continue
				driver_d.get("https://sistrack.ugarta.co.id/sistrack_new/")
		
				element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[1]/div[2]/div/label/input", 30, driver_d)
				driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[1]/div[2]/div/label/input").send_keys(tiket+"\n")

				while True:
					sleep(1)
					try:
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr[2]/td[1]")
						print("ADA")
					except Exception as e:
						break

				element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr[1]/td[3]/h3/span", 30, driver_d)
				print(str(tiket) + " | " + driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr[1]/td[3]/h3/span").text)
				if "OPEN" in driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr[1]/td[3]/h3/span").text:
					driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr/td[1]/a").click()
					element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[1]/td[2]", 30, driver_d)
					sleep(2)
					driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[1]/div[2]/table/tbody/tr[4]/td[2]/div/div[1]/select").click()
					driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[1]/div[2]/table/tbody/tr[4]/td[2]/div/div[1]/select/option[3]").click()
					driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[1]/div[2]/table/tbody/tr[4]/td[2]/div/div[2]/button").click()
					element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[1]/div/div", 30, driver_d)
					sleep(2)
				shot_url("https://1gen.citius.co.id/api/shintei/autotools/delete_appointment_from_list/"+str(tiket))
			except Exception as e:
				print(e)
			
# def check_whitelist_sender_email(email):
# 	url = 'https://boss.citius.co.id/api/check-whitelist-email'
# 	myobj = {'email':email}
# 	while True:
# 		try:
# 			x = requests.post(url, data = myobj, verify=False)
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

def crosscheck_ticket(ticket_ebs):
	while True:
		try:
			x = requests.get("https://1gen.citius.co.id/api/shintei/autotools/crosscheck_accept_ticket/"+ticket_ebs, verify=False, timeout=10)
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
		driver_d.find_element(By.XPATH, "/html/body/div[2]/form/div[1]/input").send_keys("CC-CTS")
		element_presence(By.XPATH, "/html/body/div[2]/form/div[2]/input", 30, driver_d)
		sleep(2)
		driver_d.find_element(By.XPATH, "/html/body/div[2]/form/div[2]/input").send_keys("citius123")
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

def exit_app():
	try:
		driver_d.quit()
	except Exception as e:
		pass
	window.destroy()

status_thread = threading.Thread(target=run)
status_thread.daemon = True  # Agar thread mati ketika program utama selesai
status_thread.start()

window = tk.Tk()
window.title("Auto Close")
window.geometry("50x50")
exit_button = tk.Button(window, text="exit AUTOCLOSE", command=exit_app)
exit_button.pack()
window.mainloop()
