from Common.Logger import Logger
from Common.ProcessHandler import ProcessHandler
from Common.RequestChecker import RequestChecker
from Common.RequestHandler import RequestHandler
from Common.S500Handler import S500Handler
from Common.ThreadManager import ThreadManager
from Dal.MysqlRepository import MysqlRepository
from Helpers.CookieHelper import CookieHelper
from Helpers.LfiManager import LfiManager
from Helpers.ManualTesting import ManualTesting
from Helpers.Slack import Slack
from Helpers.Spider import Spider
from Helpers.SqliManager import SqliManager
from Helpers.SubdomainChecker import SubdomainChecker
from Helpers.XssManager import XssManager
from Helpers.UrlChecker import UrlChecker
from Managers.BbManager import BbManager
from Managers.CsvManager import CsvManager
from Managers.DomainManager import DomainManager
from Managers.FastUrlManager import FastUrlManager
from Managers.SingleUrlManager import SingleUrlManager
from Managers.UrlListManager import UrlListManager
from Tools.Amass import Amass
from Tools.EyeWitness import EyeWitness
from Tools.Gobuster import Gobuster
from Tools.Httracker import Httracker
from Tools.Knock import Knock
from Tools.Nmap import Nmap
from Tools.Nuclei import Nuclei
from Tools.Waybackurls import Waybackurls
from Tools.Waymore import Waymore


class DI:
    @staticmethod
    def configure(binder):
        binder.bind_to_provider(Logger, Logger)
        binder.bind_to_provider(CookieHelper, CookieHelper)
        binder.bind_to_provider(RequestHandler, RequestHandler)
        binder.bind_to_provider(ProcessHandler, ProcessHandler)
        binder.bind_to_provider(RequestChecker, RequestChecker)
        binder.bind_to_provider(S500Handler, S500Handler)
        binder.bind_to_provider(DomainManager, DomainManager)
        binder.bind_to_provider(SingleUrlManager, SingleUrlManager)
        binder.bind_to_provider(UrlListManager, UrlListManager)
        binder.bind_to_provider(FastUrlManager, FastUrlManager)
        binder.bind_to_provider(BbManager, BbManager)
        binder.bind_to_provider(ThreadManager, ThreadManager)
        binder.bind_to_provider(Spider, Spider)
        binder.bind_to_provider(Waybackurls, Waybackurls)
        binder.bind_to_provider(Nmap, Nmap)
        binder.bind_to_provider(EyeWitness, EyeWitness)
        binder.bind_to_provider(Waymore, Waymore)
        binder.bind_to_provider(CsvManager, CsvManager)
        binder.bind_to_provider(LfiManager, LfiManager)
        binder.bind_to_provider(Gobuster, Gobuster)
        binder.bind_to_provider(Nuclei, Nuclei)
        binder.bind_to_provider(XssManager, XssManager)
        binder.bind_to_provider(SqliManager, SqliManager)
        binder.bind_to_provider(SubdomainChecker, SubdomainChecker)
        binder.bind_to_provider(ManualTesting, ManualTesting)
        binder.bind_to_provider(Amass, Amass)
        binder.bind_to_provider(Knock, Knock)
        binder.bind_to_provider(Slack, Slack)
        binder.bind_to_provider(Httracker, Httracker)
        binder.bind_to_provider(MysqlRepository, MysqlRepository)
        binder.bind_to_provider(UrlChecker, UrlChecker)
