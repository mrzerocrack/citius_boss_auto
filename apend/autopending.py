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
import subprocess
import shutil


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
		print("AUTO-DETECT CHROME MAJOR:", chrome_major, "binary:", chrome_bin)
	else:
		print("AUTO-DETECT CHROME MAJOR gagal, lanjut default UC")
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

def shot_api(ticket_ebs, note):
	print('shot_api ')
	print('shot_api ',ticket_ebs,note)
	url = 'https://boss.citius.co.id/public/api/set_last_processed_pending_ticket'
	myobj = {'ticket_ebs':ticket_ebs, 'note':note}
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
	# tab = sys.argv[1]
	chrome_options = uc.ChromeOptions()
	chrome_options.add_argument("--incognito")
	#chrome_options.add_argument('--no-sandbox')
	#chrome_options.add_argument('--headless')
	#chrome_options.add_argument('--proxy-server='+input_proxy.split("-")[0])
	driver_d = build_uc_driver(chrome_options)
	has_cookie = 0
	driver_d.get("https://sistrack.ugarta.co.id/sistrack_new/")
	login(driver_d)
	while True:
		get_tiket = get_data_api('https://boss.citius.co.id/public/api/get_pending_ticket')
		for data_ticket in get_tiket:

			try:
				if data_ticket["status"] == "t":
					driver_d.get("https://sistrack.ugarta.co.id/sistrack_new/Home")
			
					element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[1]/div[2]/div/label/input", 30, driver_d)
					driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[1]/div[2]/div/label/input").send_keys(data_ticket["ticket_ebs"]+"\n")

					while True:
						sleep(1)
						try:
							driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr/td[3]/h3/span")
							print("ADA")
							break
						except Exception as e:
							# print(e)
							pass
							

					if driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr/td[3]/h3/span").text != "SUSPEND":
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr/td[1]/a").click()
						element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[3]/div/div/a", 30, driver_d)
						sleep(2)
						btn_suspen = driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[3]/div/div/a");
						if "Suspend" in btn_suspen.text:
							btn_suspen.click()
							while True:
								try:
									element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[5]/div/div/form/div[1]/div[2]/select", 30, driver_d)
									while True:
										sleep(1)
										if driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[5]/div/div/form/div[1]/div[1]/textarea").get_attribute("value") != data_ticket["message"]:
											driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[5]/div/div/form/div[1]/div[1]/textarea").send_keys(Keys.CONTROL, 'a',Keys.BACKSPACE)
											driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[5]/div/div/form/div[1]/div[1]/textarea").send_keys(data_ticket["message"])
										else:
											break
									sleep(2)
									driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[5]/div/div/form/div[1]/div[2]/select").click();
									sleep(1)
									if data_ticket['category'] == 1:
										driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[5]/div/div/form/div[1]/div[2]/select/option[2]").click()
									if data_ticket['category'] == 2:
										driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[5]/div/div/form/div[1]/div[2]/select/option[3]").click()
									if data_ticket['category'] == 3:
										driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[5]/div/div/form/div[1]/div[2]/select/option[4]").click()
									if data_ticket['category'] == 4:
										driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[5]/div/div/form/div[1]/div[2]/select/option[5]").click()
									sleep(1)
									driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[5]/div/div/form/div[2]/button[2]").click()
									break
								except Exception as e:
									# print(e)
									pass

						element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[1]/div/div", 30, driver_d)
						shot_api(data_ticket["ticket_ebs"],data_ticket["message"])
					else:
						shot_api(data_ticket["ticket_ebs"],data_ticket["message"])
				else:
					open("ticket_error.txt","a").writelines(data_ticket["ticket_ebs"]+" TICKET TIDAK WARAS\n")
			except Exception as e:
				# print(e)
				open("ticket_error.txt","a").writelines(data_ticket["ticket_ebs"]+" ERROR SAAT PROSES[2]\n")
			
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
	element_presence(By.XPATH, "/html/body/form/div/input[1]", 30, driver_d)
	sleep(3)
	try:
		driver_d.find_element(By.XPATH, "/html/body/form/div/input[1]").send_keys("CC-CTS")
		element_presence(By.XPATH, "/html/body/form/div/input[2]", 30, driver_d)
		sleep(2)
		driver_d.find_element(By.XPATH, "/html/body/form/div/input[2]").send_keys("citius123\n")
	except Exception as e:
		print(e)

run()
