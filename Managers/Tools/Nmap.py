import os
import pathlib
import time

from Managers.CacheManager import CacheManager


class Nmap:
    def __init__(self, domain):
        self.__tool_name = self.__class__.__name__
        self.__domain = domain

    def check_ports(self, subdomains):

        cache_manager = CacheManager(self.__tool_name, self.__domain)
        report_lines = cache_manager.get_saved_result()
        if not report_lines:
            start = time.time()
            nmap_directory = f"Results/{self.__tool_name}"
            if not os.path.exists(nmap_directory):
                os.makedirs(nmap_directory)
            txt_filepath = f"{nmap_directory}/{self.__domain}.txt"
            txt_file = open(txt_filepath, 'a')
            for subdomain in subdomains:
                txt_file.write("%s\n" % str(subdomain))
            txt_file.close()

            subdomains_filepath = os.path.join(pathlib.Path().resolve(), txt_filepath)
            command = f'nmap -sT -T4 -iL {subdomains_filepath} --top-ports 10000'
            stream = os.popen(command)
            bash_outputs = stream.readlines()
            report_lines = []

            os.remove(txt_filepath)

            for line in bash_outputs:
                if line.startswith('Nmap scan report') or ' open ' in line:
                    report_lines.append(line.replace('\n', ''))
            end = time.time()
            cache_manager.save_result(report_lines)

            print(f'Nmap finished in {(end - start)/60} minutes')
