# import threading
# import queue
#
# # A function to run in threads
# def task(n, result_queue):
import inject
import requests
from dotenv import load_dotenv

from Common.DI import DI
from Common.RequestHandler import RequestHandler
from Tools.Nmap import Nmap

load_dotenv('config.env')

inject.configure(DI.configure)

nmap = inject.instance(Nmap)
aaa = nmap.check_ports('qwant.com', [])

a = 1


