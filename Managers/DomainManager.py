import os


def get_start_urls(file_path):
    if os.path.exists(file_path):
        return set(line.strip() for line in open(file_path))


class DomainManager:
    pass
