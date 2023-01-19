import os
from dotenv import load_dotenv
from Managers.DomainFlowManager import DomainFlowManager
from Managers.MultipleUrlFlowManager import MultipleUrlFlowManager
from Managers.SingleUrlFlowManager import SingleUrlFlowManager
from Models.GetRequestDTO import GetRequestDTO

headers = {
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
}

load_dotenv('config.env')

if __name__ == '__main__':
    check_mode = os.environ.get('check_mode')
    if check_mode == 'D':
        domain = os.environ.get('domain')
        domain_man = DomainFlowManager(headers)
        domain_man.check_domain(domain)

    elif check_mode == 'U':
        single_url_man = SingleUrlFlowManager(headers)
        single_url = os.environ.get('single_url')
        single_url_man.run(GetRequestDTO(single_url))

    elif check_mode == 'UL':
        multiple_url_man = MultipleUrlFlowManager(headers)
        multiple_url_man.run()

    elif check_mode == 'DL':
        file_path = 'Targets/domains.txt'
        if os.path.exists(file_path):
            domains = list(set(line.strip() for line in open(file_path)))
            domain_man = DomainFlowManager(headers)
            for domain in domains:
                domain_man.check_domain(domain)
        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{file_path} is missing')

# if __name__ == '__main__':
#     proc = subprocess.Popen(["curl", "https://8c9d-91-196-101-94.eu.ngrok.io/sss"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#     # proc.wait()
#     # err_message2 = proc.stderr.read().decode()
#     kill = lambda process: process.kill()
#     my_timer = Timer(1200, kill, [proc])
#     try:
#         my_timer.start()
#         proc.wait()
#         err_message = proc.stderr.read().decode()
#
#     finally:
#         my_timer.cancel()
