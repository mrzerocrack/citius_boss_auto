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


#DATE TIME GMT DAN LOCAL
# print("\nGMT: "+time.strftime("%a, %d %b %Y %I:%M:%S %p %Z", time.gmtime()))
# print("Local: "+strftime("%a, %d %b %Y %I:%M:%S %p %Z\n"))

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
	chrome_options = Options()
	chrome_options.add_argument("--incognito")
	#chrome_options.add_argument('--no-sandbox')
	#chrome_options.add_argument('--headless')
	#chrome_options.add_argument('--proxy-server='+input_proxy.split("-")[0])
	driver_d = Chrome(options=chrome_options)
	has_cookie = 0
	driver_d.get("https://app.slmugmandiri.co.id/sistrack_new/")
	login(driver_d)
	get_tiket = get_data_api('https://boss.citius.co.id/public/api/get_pending_ticket')
	for data_ticket in get_tiket:

		try:
			if data_ticket["status"] == "t":
				driver_d.get("https://app.slmugmandiri.co.id/sistrack_new/Home")
		
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