import os
from dotenv import load_dotenv

from Common.RequestHandler import RequestHandler
from Managers.CsvManager import CsvManager
from Managers.DomainFlowManager import DomainFlowManager
from Managers.DomainTrackerManager import DomainTackerManager
from Managers.FastUrlFlowManager import FastUrlFlowManager
from Managers.MultipleUrlFlowManager import MultipleUrlFlowManager
from Managers.SingleUrlFlowManager import SingleUrlFlowManager
from Models.HeadRequestDTO import HeadRequestDTO

headers = {
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
}

load_dotenv('config.env')

if __name__ == '__main__':
    check_mode = os.environ.get('check_mode')
    print(f'Running - {check_mode} mode')

    if check_mode == 'SC':
        csv_man = CsvManager(headers)
        csv_man.run()

    elif check_mode == 'D':
        domain = os.environ.get('domain')
        domain_man = DomainFlowManager(headers)
        domain_man.check_domain(domain)

    elif check_mode == 'DL':
        file_path = 'Targets/domains.txt'
        if os.path.exists(file_path):
            domains = list(set(line.strip() for line in open(file_path)))
            domain_man = DomainFlowManager(headers)
            counter = len(domains)
            for domain in domains:
                print(f'Checking {domain} domain. Counter: {counter}')
                domain_man.check_domain(domain)
                counter -= 1
        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{file_path} is missing')

    elif check_mode == 'TD':
        domain_man = DomainTackerManager(headers)
        domain_man.track_domains()


    elif check_mode == 'U':
        single_url_man = SingleUrlFlowManager(headers)
        single_url = os.environ.get('single_url')
        request_handler = RequestHandler(cookies="", headers=headers)
        response = request_handler.send_head_request(single_url)
        single_url_man.run(HeadRequestDTO(response))

    elif check_mode == 'UL':
        check_mode = os.environ.get('check_mode')
        multiple_url_man = MultipleUrlFlowManager(headers)
        multiple_url_man.run()

    elif check_mode == 'FU':
        fast_man = FastUrlFlowManager(headers)
        fast_man.run()


