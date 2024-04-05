import os
import time

from dotenv import load_dotenv

from Common.ThreadBucket import ThreadBucket
from Dal.MysqlRepository import MysqlRepository
from Managers.BbManager import BbManager
from Managers.CsvManager import CsvManager
from Managers.DomainManager import DomainManager
from Managers.TrackerManager import TrackerManager
from Managers.FastUrlManager import FastUrlManager
from Managers.UrlListManager import UrlListManager
from Managers.SingleUrlManager import SingleUrlManager

headers = {
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
}

load_dotenv('config.env')



if __name__ == '__main__':

    check_mode = os.environ.get('check_mode')
    print(f'Running - {check_mode} mode')

    mysql_repo = MysqlRepository()
    mysql_repo.init_tables()

    if check_mode == 'SC':
        csv_man = CsvManager(headers)
        csv_man.run()

    elif check_mode == 'D':
        domain = os.environ.get('domain')
        domain_man = DomainManager(headers)
        domain_man.check_domain(domain)

    elif check_mode == 'DL':
        domain_man = DomainManager(headers)
        domain_man.check_multiple_domains()

    elif check_mode == 'TR':
        domain_man = TrackerManager(headers)
        domain_man.track_domains()

    elif check_mode == 'U':
        single_url_man = SingleUrlManager(headers)
        single_url_man.run()

    elif check_mode == 'UL':
        multiple_url_man = UrlListManager(headers)
        multiple_url_man.run()

    elif check_mode == 'FU':
        fast_man = FastUrlManager(headers)
        fast_man.run()

    elif check_mode == 'BB':
        fast_man = BbManager()
        fast_man.run()
