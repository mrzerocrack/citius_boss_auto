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
			data_ticket = get_data_api('https://boss.citius.co.id/api/tes/'+line.strip())

			try:
				if data_ticket["status"] == "t":
					driver_d.get("https://app.slmugmandiri.co.id/sistrack_new/Home")
					download("https://boss.citius.co.id/uploads/foto/"+data_ticket["foto"], data_ticket["ticket_ebs"] + data_ticket["foto"])
					path_foto = os.getcwd()+"\\"+data_ticket["ticket_ebs"]+data_ticket["foto"]
			
					element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[1]/div[2]/div/label/input", 30, driver_d)
					driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[1]/div[2]/div/label/input").send_keys(data_ticket["ticket_ebs"]+"\n")

					while True:
						sleep(1)
						try:
							driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr[2]/td[1]")
							print("ADA")
						except Exception as e:
							break

					if driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr[1]/td[3]/h3/span").text == "CLOSED":
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div[4]/div/div/div/div/div[2]/div/table/tbody/tr/td[1]/a").click()
						element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[1]/td[2]", 30, driver_d)
						sleep(2)
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[12]/td[2]/input").send_keys(data_ticket["start_wo_date"])
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[12]/td[2]/input").send_keys(Keys.RIGHT)
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[12]/td[2]/input").send_keys(data_ticket["start_wo_time"])

						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[13]/td[2]/input").send_keys(data_ticket["finish_wo_date"])
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[13]/td[2]/input").send_keys(Keys.RIGHT)
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[1]/table/tbody/tr[13]/td[2]/input").send_keys(data_ticket["finish_wo_time"])
						driver_d.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[4]/div[2]/form/div/div[3]/button").click()
						element_presence(By.XPATH, "/html/body/div[2]/div/div/div[2]/div[1]/div/div", 30, driver_d)
						
				else:
					open("ticket_error.txt","a").writelines(line)
			except Exception as e:
				open("ticket_error.txt","a").writelines(line)

			open("last_ticket_proccessed.txt","w").writelines(line)
			
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

def get_login_email():
	url = 'https://boss.citius.co.id/api/get-login-email'
	myobj = {}
	x = requests.post(url, data = myobj)
	x.close()
	return json.loads(x.text)

def download(url, name):
	response = requests.get(url)
	open(name, "wb").write(response.content)

def shot_url(url):
	myobj = {}
	x = requests.get(url)
	x.close()

def get_data_api(url):
	myobj = {}
	x = requests.get(url)
	x.close()
	return json.loads(x.text)

def post_data_api(url):
	myobj = {}
	x = requests.post(url, data = myobj)
	x.close()
	return json.loads(x.text)

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