import os

from flask import Flask
from dotenv import load_dotenv

from Managers.DomainFlowManager import DomainFlowManager
from Managers.SingleUrlFlowManager import SingleUrlFlowManager
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
    single_url_man = SingleUrlFlowManager(headers)
    if check_mode == 'D':
        domain = os.environ.get('__domain')
        domain_man = DomainFlowManager(headers, single_url_man)
        domain_man.check_domain(domain)

    elif check_mode == 'S':
        single_url = os.environ.get('single_url')
        print(f'start_url - {single_url}')
        single_url_man.run(single_url)

    elif check_mode == 'M':
        file_path = 'Targets\\urls.txt'
        if os.path.exists(file_path):
            urls = list(set(line.strip() for line in open(file_path)))
            thread_man = ThreadManager()
            thread_man.run_all(single_url_man.run, urls)
        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{file_path} is missing')


# if __name__ == '__main__':
# my_env = os.environ.copy()
# my_env["PATH"] = "/usr/sbin:/sbin:" + my_env["PATH"]
# a = subprocess.Popen(['bash', '1.sh'])
# print(a)
# from subprocess import check_output
# a = check_output(['bash', '/mnt/c/F/1.sh'], shell=True)
# print(a)
# app.run(host="0.0.0.0")
