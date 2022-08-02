import base64
import os
import subprocess
import requests

from flask import Flask
from dotenv import load_dotenv

from Managers.CacheManager import CacheManager
from Managers.CookieManager import CookieManager
from Managers.Dirb import Dirb
from Managers.Sublister import Sublister
from Managers.ThreadManager import ThreadManager

headers = {
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
}
# 'X-Forwarded-For': "1'OR(if(1=1,sleep(5),0))OR'2",
# 'X-API-KEY': 'xapikeypoc\'',
app = Flask(__name__)
load_dotenv('config.env')

# @app.route("/")
# def index():
#     return '/run'


# @app.route("/clear")
# def clear():
#     CacheManager.clear_all()


# @app.route("/clear")
# def clear():
#     return CacheManager.clear_all()


# @app.route("/run")
# def main():
if __name__ == '__main__':

    check_mode = os.environ.get('check_mode')
    max_depth = os.environ.get('max_depth')
    batch_size = os.environ.get('batch_size')
    ngrok_url = os.environ.get('ngrok_url')
    download_path = os.environ.get('download_path')
    thread_man = ThreadManager(batch_size, download_path, max_depth, headers, ngrok_url)

    if check_mode == 'D':
        domain = os.environ.get('domain')
        man = Sublister(domain, headers, download_path)
        subdomain_urls = man.get_subdomains()
        dirb = Dirb(thread_man)
        dirb.check_subdomain_urls(subdomain_urls)
    elif check_mode == 'U':
        start_url = os.environ.get('start_url')
        raw_cookies = os.environ.get('raw_cookies')
        print(f'start_url - {start_url}')
        print(f'raw_cookies - {raw_cookies}')
        thread_man.run_single(start_url, raw_cookies)

    elif check_mode == 'T':
        print(f'is_single_check - {check_mode}')
        thread_man.run_target_urls()

# if __name__ == '__main__':
# my_env = os.environ.copy()
# my_env["PATH"] = "/usr/sbin:/sbin:" + my_env["PATH"]
# a = subprocess.Popen(['bash', '1.sh'])
# print(a)
# from subprocess import check_output
# a = check_output(['bash', '/mnt/c/F/1.sh'], shell=True)
# print(a)
# app.run(host="0.0.0.0")
