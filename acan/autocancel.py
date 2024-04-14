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
	with open('list_tiket.txt', 'r') as f:
		for line in f:
			data_ticket = get_data_api('http://boss.citius.co.id/public/api/get_cancel_ticket_api/'+line.strip())

			try:
				if data_ticket["status"] == "t":
					driver_d.get("https://app.slmugmandiri.co.id/sistrack_new/Home")
					name_foto = data_ticket["ticket_ebs"] + data_ticket["foto"].replace("/","-")
					if data_ticket["status_foto"] == "t":
						download("http://boss.citius.co.id/"+data_ticket["foto"], name_foto)
						path_foto = os.getcwd()+"\\"+name_foto
			
					element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[1]/div[2]/div/label/input", 30, driver_d)
					driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[1]/div[2]/div/label/input").send_keys(data_ticket["ticket_ebs"]+"\n")

					while True:
						sleep(1)
						try:
							driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr[2]/td[1]")
							print("ADA")
						except Exception as e:
							break

					if driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr[1]/td[3]/h3/span").text != "CLOSED":
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

						# driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[13]/td[2]/input").send_keys(data_ticket["date"])
						# driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[13]/td[2]/input").send_keys(Keys.RIGHT)
						# driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[13]/td[2]/input").send_keys(data_ticket["date"])
						driver_d.execute_script("arguments[0].value='"+data_ticket["dt"]+"';", driver_d.find_element(By.XPATH, '/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[13]/td[2]/input'))

						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[2]/table/tbody/tr[6]/td/input").send_keys("NON JC REPORT")
						# driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[2]/table/tbody/tr[8]/td/textarea").click()
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[2]/table/tbody/tr[8]/td/textarea").send_keys(data_ticket["note"])
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[3]/button").click()
						element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[1]/div/div", 30, driver_d)
						sleep(2)
						driver_d.refresh()
						element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[1]/td[2]", 30, driver_d)

						if data_ticket["status_foto"] == "t":
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
						shot_url("http://boss.citius.co.id/closeEbsTicketAuto/"+str(data_ticket["ticket_id"]))
				else:
					open("ticket_error.txt","a").writelines(line)
			except Exception as e:
				print(e)
				open("ticket_error.txt","a").writelines(line+"-EXCEPTION\n"+str(e)+"\n\n")

			open("last_ticket_proccessed.txt","w").writelines(line)
			
# def check_whitelist_sender_email(email):
# 	url = 'http://boss.citius.co.id/api/check-whitelist-email'
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
			print(url)
			open(name, "wb").write(response.content)
			break
		except Exception as e:
			print(e)
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