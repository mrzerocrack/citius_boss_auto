import zipfile
from selenium import webdriver
from undetected_chromedriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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
import win32api
import win32gui
import subprocess
from urllib.parse import urlparse


#DATE TIME GMT DAN LOCAL
# print("\nGMT: "+time.strftime("%a, %d %b %Y %I:%M:%S %p %Z", time.gmtime()))
# print("Local: "+strftime("%a, %d %b %Y %I:%M:%S %p %Z\n"))

def element_presence(by,by_val,time, driver):
	element_present = EC.presence_of_element_located((by, by_val))
	try:
		WebDriverWait(driver, time).until(element_present)
	except Exception as e:
		print (e)
	else:
		pass

def run():
	global is_login
	# tab = sys.argv[1]
	chrome_options = Options()
	chrome_options.add_argument("--incognito")
	#chrome_options.add_argument('--no-sandbox')
	#chrome_options.add_argument('--headless')
	#chrome_options.add_argument('--proxy-server='+input_proxy.split("-")[0])
	global driver_d
	driver_d = Chrome(options=chrome_options)
	has_cookie = 0
	driver_d.get("https://sistrack.ugarta.co.id/sistrack_new/")
	login(driver_d)
	show_notif_captcha()
	with open('list_tiket.txt', 'r') as f:
		for line in f:
			data_ticket = get_data_api('https://1gen.citius.co.id/api/shintei/autotools/get_report_item_value_closed_ticket/'+line.strip())
			print("MASUK PROSES")

			try:
				foto_file_name = None
				if data_ticket["status"] == 1:
					driver_d.get("https://sistrack.ugarta.co.id/sistrack_new/")
					if data_ticket["status_foto"] == 1:
						print("MASUK DOWNLOAD")
						foto_file_name = download(data_ticket["foto"])
						print("MASUK AFTER DOWNLO")
						path_foto = os.getcwd()+"\\"+foto_file_name

					element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[1]/div[2]/div/label/input", 30, driver_d)
					driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[1]/div[2]/div/label/input").send_keys(data_ticket["ticket_ebs"]+"\n")

					while True:
						sleep(1)
						try:
							driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr[2]/td[1]")
							driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr[1]/td[3]/h3/span")
							print("ADA")
						except Exception as e:
							break

					element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr[1]/td[3]/h3/span", 30, driver_d)
					if driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr[1]/td[3]/h3/span").text != "CLOSED":
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr/td[1]/a").click()
						element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[1]/td[2]", 30, driver_d)
						sleep(2)
						try:
							btn_suspen = driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[3]/div/div/a")
							if "Open Suspend" in btn_suspen.text:
								driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[3]/div/div/a").click()
								element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[1]/div/div", 30, driver_d)
						except Exception as e:
							pass
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[1]/td[2]/input").send_keys(data_ticket["grounding"])

						#INPUT RMM
						#CLICK SELECT RMM
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[2]/td[2]/select").click()
						#CLICK OPTION ACTIVE
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[2]/td[2]/select/option[4]").click()

						#INPUT VOLTAGE
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[3]/td[2]/input").send_keys(data_ticket["voltage"])

						#INPUT UPS
						#CLICK SELECT UPS
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[4]/td[2]/select").click()
						#PILIH STATUS
						if(data_ticket["ups"] == "Ready"):
							driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[4]/td[2]/select/option[4]").click()
						elif(data_ticket["ups"] == "Not Ready"):
							driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[4]/td[2]/select/option[5]").click()
						else:
							driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[4]/td[2]/select/option[3]").click()

						#CLICK AC
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[5]/td[2]/input").send_keys(data_ticket["temp"])

						#CLICK EXHAUST FAN
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[6]/td[2]/select").click()
						#CLICK SELECT EXHAUST ADA
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[6]/td[2]/select/option[3]").click()

						#SET PLAT ASKIM READY
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[7]/td[2]/input").send_keys("ready")

						#CLICK SELECT CAMERA INTERNAL
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[8]/td[2]/select").click()
						#CLICK CAMERA INTERNAL ADA BRFUNGSI
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[8]/td[2]/select/option[5]").click()

						# driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[12]/td[2]/input").send_keys(data_ticket["start_wo_date"])
						# driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[12]/td[2]/input").send_keys(Keys.RIGHT)
						# driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[12]/td[2]/input").send_keys(data_ticket["start_wo_time"])
						driver_d.execute_script("arguments[0].value='"+data_ticket["dt_start_wo"]+"';", driver_d.find_element(By.XPATH, '/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[12]/td[2]/input'))

						# driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[13]/td[2]/input").send_keys(data_ticket["finish_wo_date"])
						# driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[13]/td[2]/input").send_keys(Keys.RIGHT)
						# driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[13]/td[2]/input").send_keys(data_ticket["finish_wo_time"])
						driver_d.execute_script("arguments[0].value='"+data_ticket["dt_finish_wo"]+"';", driver_d.find_element(By.XPATH, '/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[13]/td[2]/input'))

						# driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[2]/table/tbody/tr[6]/td/input").click()
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[2]/table/tbody/tr[6]/td/input").send_keys(data_ticket["fe_report"])
						# driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[2]/table/tbody/tr[8]/td/textarea").click()
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[2]/table/tbody/tr[8]/td/textarea").send_keys(data_ticket["note"])
	  
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[3]/button").click()
						element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[1]/div/div", 30, driver_d)
						sleep(2)
						driver_d.refresh()
						element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[1]/td[2]", 30, driver_d)

						if data_ticket["status_foto"] == 1:
							driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[3]/div[2]/a[4]").click()
							sleep(3)
							driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[6]/div/div/form/div[1]/div/input").send_keys(path_foto)
	   
							driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[6]/div/div/form/div[2]/button[2]").click()
							element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[1]/div/div", 30, driver_d)
							sleep(2)
							driver_d.refresh()
							element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[1]/td[2]", 30, driver_d)

						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[1]/div[2]/table/tbody/tr[4]/td[2]/div/div[1]/select").click()
	  
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[1]/div[2]/table/tbody/tr[4]/td[2]/div/div[1]/select/option[6]").click()
	  
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[1]/div[2]/table/tbody/tr[4]/td[2]/div/div[2]/button").click()
						element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[1]/div/div", 30, driver_d)
						sleep(2)
						shot_url("https://1gen.citius.co.id/api/shintei/autotools/delete_closed_from_list/"+str(data_ticket["ticket_id"]))
					else:
						shot_url("https://1gen.citius.co.id/api/shintei/autotools/delete_closed_from_list/"+str(data_ticket["ticket_id"]))
				else:
					open("ticket_error.txt","a").writelines(line)
			except Exception as e:
				open("ticket_error.txt","a").writelines(line+"-EXCEPTION\n"+str(e)+"\n\n")

			open("last_ticket_proccessed.txt","w").writelines(line)
   
	win32api.MessageBox(0, "AUTO Selesai", "INFO", 0x00001000)
	exit_app()
			
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

def download(url):
	while True:
		try:
			resp = requests.get(url, verify=False, timeout=10)
			# 1. Coba dari header Content-Disposition
			cd = resp.headers.get('content-disposition')
			if cd:
				matches = re.findall(r'filename="?([^"]+)"?', cd)
				filename = matches[0] if matches else None
			else:
				filename = None

			# 2. Jika masih None, ambil dari URL path
			if not filename:
				path = urlparse(url).path
				filename = os.path.basename(path)

			# 3. Jika masih kosong (URL tanpa nama), buat default berdasarkan waktu + ekstensi
			if not filename:
				# ambil ekstensi dari Content-Type misal 'image/jpeg'
				ct = resp.headers.get('content-type', '')
				ext = ct.split('/')[-1] if '/' in ct else 'jpg'
				filename = f"image_{int(time())}.{ext}"

			# simpan file
			with open(filename, "wb") as f:
				f.write(resp.content)

			print(f"✅ Tersimpan sebagai: {filename}")
			return filename

		except Exception as e:
			print("🔄 Ulang…", e)
			sleep(5)

def shot_url(url):
	while True:
		try:
			myobj = {}
			print(url)
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
	win32api.MessageBox(0, "Login manual, klo dah sukses login klik OK dibawah", "INFO", 0x00001000)

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