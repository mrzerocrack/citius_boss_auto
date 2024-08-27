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

manifest_json = ""
background_js = ""
bot_init = 0
with open("bot_status.txt", "w") as f:
	f.writelines("0")

def set_manifest_json(PROXY_HOST, PROXY_PORT, PROXY_PASS, PROXY_USER) :
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

def shot_api(incident_id, atm_id, problem):
	print('shot_api ',incident_id,atm_id,problem)
	url = 'http://boss.citius.co.id/api/create-ticket'
	myobj = {'incident_id':incident_id, 'atm_id':atm_id, 'problem':problem}
	while True:
		try:
			x = requests.post(url, data = myobj, timeout=10)
			print("OKEEEE")
			break
		except Exception as e:
			print("ULANGGGG")
			sleep(5)
			x = requests.post(url, data = myobj, timeout=10)
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

def get_chromedriver(use_proxy=False,host="0",port=0,pwd="a",usr="a"):
    path = os.path.dirname(os.path.abspath(__file__))
    chrome_options = webdriver.ChromeOptions()

    manifest_json = set_manifest_json(host,port,pwd,usr)
    background_js = set_background_js(host,port,pwd,usr)
    if use_proxy:
        pluginfile = 'proxy_auth_plugin.zip'

        with zipfile.ZipFile(pluginfile, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)
        chrome_options.add_extension(pluginfile)
        print("PLUG IN ADED")

    driver = webdriver.Chrome(
        os.path.join(path, 'chromedriver'),
        chrome_options=chrome_options)
    return driver

def run():
	# tab = sys.argv[1]
	input_proxy = '45.252.57.6:6451:dmproxy926:dmproxy926'
	PROXY_HOST = input_proxy.split(":")[0].strip()
	PROXY_PORT = input_proxy.split(":")[1].strip()
	PROXY_USER = input_proxy.split(":")[2].strip()
	PROXY_PASS = input_proxy.split(":")[3].strip().split("-")[0]
	chrome_options = Options()
	chrome_options.add_argument("--incognito")
	#chrome_options.add_argument('--no-sandbox')
	#chrome_options.add_argument('--headless')
	#chrome_options.add_argument('--proxy-server='+input_proxy.split("-")[0])
	driver_d = Chrome(options=chrome_options)
	has_cookie = 0
	driver_d.get("https://mail.google.com")
	data_xpath = get_data_xpath()
	login(driver_d, data_xpath)

	while True:
		data_xpath = get_data_xpath()
		try:
			try:
				driver_d.execute_script('document.getElementById("'+driver_d.find_element(By.XPATH, data_xpath['top_mail_list']).get_attribute('id')+'").scrollTop=0')
			except Exception as e:
				print(e)
				print("ERROR_CODE : top_mail_list 001 \n contact your IT Staff")
				sleep(5)

			for x in range(20):
				print('X = ' + str(x))
				try:
					subject_email = driver_d.find_element(By.XPATH, data_xpath['subject_mail_list'].replace("replace_with_detail_row", str(x+1)))
					print('subject_email ',subject_email.text)
				except Exception as e:
					print(e)
					print("ERROR_CODE : subject_mail_list 001 \n contact your IT Staff")
					sleep(5)
				try:
					if check_whitelist_sender_email(driver_d.find_element(By.XPATH, data_xpath['sender_mail_list'].replace("replace_with_detail_row", str(x+1))).get_attribute('email')) and 'New Incident' in subject_email.text or 'TIKET' in subject_email.text:
						print('class subject ', driver_d.find_element(By.XPATH, data_xpath['sender_mail_list'].replace("replace_with_detail_row", str(x+1))).get_attribute("class"))
						try:
							if driver_d.find_element(By.XPATH, data_xpath['sender_mail_list'].replace("replace_with_detail_row", str(x+1))).get_attribute("class") == 'zF':
								print("MASUK IF ZF")
								while True:
									try:
										driver_d.find_element(By.XPATH, data_xpath['sender_mail_list'].replace("replace_with_detail_row", str(x+1))).click()
										break
									except Exception as e:
										driver_d.execute_script('document.getElementById("'+driver_d.find_element(By.XPATH, data_xpath['row_mail_list'].replace("replace_with_detail_row", str(x+1))).get_attribute('id')+'").scrollIntoView()')
										print('try click again\n',e)
								try:
									element_presence(By.XPATH, data_xpath['body_email'], 30, driver_d)
								except Exception as e:
									print(e)
									print("ERROR_CODE : body_email 001 \n contact your IT Staff")
									sleep(5)

								body_email = driver_d.find_element(By.XPATH, data_xpath['body_email'])
								if 'TIKET :' in body_email.text and 'ATM ID :' in body_email.text:
									print("MASUK IF TIKET")
									if 'STATUS :' not in body_email.text:
										incident_id = str(body_email.text.split('TIKET : ')[1].strip().split('\n')[0])
										atm_id = str(body_email.text.split('ATM ID : ')[1].strip().split('\n')[0])
										problem = str(body_email.text.split('PROBLEM : ')[1].strip().split('\n')[0])
										while True:
											res_shot_api = shot_api(incident_id, atm_id, problem)
											if 'ok' in res_shot_api:
												break
											elif 'fail' in res_shot_api:
												break
											else:
												print('gagal')
								driver_d.find_element(By.XPATH, data_xpath['inbox_button']).click()
								sleep(2)
								print('OK')
						except Exception as e:
							print(e)
							print("ERROR_CODE : IF sender_mail_list with class zF 001 \n contact your IT Staff")
							sleep(5)
				except Exception as e:
					print(e)
			driver_d.find_element(By.XPATH, data_xpath['inbox_button']).click()
			sleep(2)

		except Exception as e:
			print('error ni')
			print(e)
			
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
	url = 'http://boss.citius.co.id/api/get-login-email'
	myobj = {}
	x = requests.post(url, data = myobj)
	x.close()
	return json.loads(x.text)

def get_data_xpath():
	url = 'http://iot.citius.co.id/api/mailscrapper_get_xpath'
	myobj = {}
	x = requests.post(url, data = myobj)
	x.close()
	return json.loads(x.text)

def login(driver_d, data_xpath):
	login_data = get_login_email()
	element_presence(By.XPATH, data_xpath['login_username_form'], 30, driver_d)
	try:
		element_presence(By.XPATH, data_xpath['login_username_form'], 30, driver_d)
		driver_d.find_element(By.XPATH, data_xpath['login_username_form']).send_keys(login_data['email']+"\n")
		element_presence(By.XPATH, data_xpath['login_password_form'], 30, driver_d)
		sleep(2)
		driver_d.find_element(By.XPATH, data_xpath['login_password_form']).send_keys(login_data['password']+"\n")
	except Exception as e:
		print(e)

	element_presence(By.XPATH, data_xpath['inbox_button'], 60, driver_d)

run()