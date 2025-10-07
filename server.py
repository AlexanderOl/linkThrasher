import os

import inject
from dotenv import load_dotenv

from Common.DI import DI
from Dal.MysqlRepository import MysqlRepository
from Managers.BbManager import BbManager
from Managers.CsvManager import CsvManager
from Managers.DomainManager import DomainManager
from Managers.FastUrlManager import FastUrlManager
from Managers.UrlListManager import UrlListManager
from Managers.SingleUrlManager import SingleUrlManager

load_dotenv('config.env')

inject.configure(DI.configure)
check_mode = os.environ.get('check_mode')
print(f'Running - {check_mode} mode')

mysql_repo = inject.instance(MysqlRepository)
mysql_repo.init_tables()

if check_mode == 'CSV':
    csv_man = inject.instance(CsvManager)
    csv_man.run()

elif check_mode == 'D':
    domain = os.environ.get('domain')
    domain_man = inject.instance(DomainManager)
    domain_man.check_domain(domain)

elif check_mode == 'DL':
    domain_man = inject.instance(DomainManager)
    domain_man.check_multiple_domains()

elif check_mode == 'U':
    single_url_man = inject.instance(SingleUrlManager)
    single_url_man.run()

elif check_mode == 'UL':
    multiple_url_man = inject.instance(UrlListManager)
    multiple_url_man.run()

elif check_mode == 'FU':
    fast_man = inject.instance(FastUrlManager)
    fast_man.run()

elif check_mode == 'BB':
    fast_man = inject.instance(BbManager)
    fast_man.run()
