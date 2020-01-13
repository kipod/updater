#!/usr/bin/env python3
import argparse
import ftplib
import os
import json
import time
import datetime
import platform
import tarfile
from urllib.parse import urlparse
import console

VERSION = '1.0'
DEFAULT_FTP_BASE_URL = 'ftp://builderust.dev.ath/tachyon/'
DEFAULT_DIST_FILE = {
    'Linux': 'tachyon-linux.tar.gz',
    'Windows': 'tachyon-windows.tar.gz',
    'Darwin': 'tachyon-macos.tar.gz'
}[platform.system()]
CONFIG_FILE = 'config.json'
CONSOLE_WIDTH, _= console.getTerminalSize()

g_args = None


def main():
    parser = argparse.ArgumentParser(description='Tachyon updater. Version {}'.format(VERSION), add_help=True)
    parser.add_argument('-u', '--ftp-base_url', help='ftp base URL', default=DEFAULT_FTP_BASE_URL)
    parser.add_argument('-f', '--file-name', help='distribution file name', default=DEFAULT_DIST_FILE)
    parser.add_argument('-c', '--conf-file', help='path to config file', default=CONFIG_FILE)
    parser.add_argument('--ftp-user', help='user name for FTP', default=None)
    parser.add_argument('--ftp-password', help='password for FTP user', default=None)

    global g_args
    g_args = parser.parse_args()
    url = urlparse(g_args.ftp_base_url)
    g_args.ftp_server = f'{url.hostname}:{url.port}' if url.port else f'{url.hostname}:21'
    g_args.ftp_dir = url.path

    with Downloader() as dl:
        try:
            dl.process_files()
        except ftplib.error_temp as e:
            print('FTP error: ', e)
            return

    with Unpacker(g_args.file_name, target_path='o') as compressed_file:
        try:
            compressed_file.extruct()
        except tarfile.TarError as e:
            print('Unpack error: ', e)
            return


class Unpacker(object):
    def __init__(self, file_path, target_path):
        self.tar_file_path = file_path
        self.target = target_path
        self.__tar = None

    def close(self):
        if self.__tar:
            self.__tar.close()

    def __enter__(self):
        self.__tar = tarfile.open(self.tar_file_path, 'r:*')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def extruct(self):
        infos = self.__tar.getmembers()
        total_size = sum([i.size for i in infos if i.isfile()])
        completed_size = 0
        prev_print_progress = 0
        start = time.time()

        def print_progress(done_size, force=False):
            nonlocal start
            if force or time.time() - start > 1.0:
                print_progress_bar(done_size, total_size, prefix='unpack:')
                start = time.time()

        for info in infos:
            if info.isdir():
                # os.makedirs(info.name, exist_ok=True)
                self.__tar.extract(info, path=self.target)
            elif info.isfile():
                self.__tar.extract(info, path=self.target)
                completed_size += info.size
                if completed_size < total_size:
                    print_progress(completed_size)
        if total_size:
            print_progress(total_size, True)


class Downloader(object):
    def __init__(self):
        self.ftp = None
        self.reopen_ftp()
        self.file = None

    def close(self):
        if self.ftp:
            self.ftp.close()
        if self.file:
            self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def reopen_ftp(self):
        if self.ftp:
            self.ftp.close()
        self.ftp = ftplib.FTP()
        host, port = g_args.ftp_server.split(':')
        self.ftp.connect(host=host, port=int(port))
        self.ftp.login(user=g_args.ftp_user, passwd=g_args.ftp_password)
        self.ftp.cwd(g_args.ftp_dir)

    def process_files(self):
        file_name = g_args.file_name
        file_size = self.ftp.size(file_name)
        completed_size = 0
        prev_print_progress = 0
        start = time.time()

        def print_progress(done_size, force=False):
            nonlocal start
            if force or time.time() - start > 1.0:
                print_progress_bar(done_size, file_size, prefix='{} :'.format(file_name))
                start = time.time()

        def parse_bin(data):
            if self.file is None:
                self.file = open(g_args.file_name, 'bw')
            self.file.write(data)
            print_progress(len(data))

        self.ftp.retrbinary('RETR {}'.format(file_name), parse_bin, blocksize=8192)
        if file_size:
            print_progress(file_size, True)

    def ftp_cmd(self, command: str):
        return self.ftp.sendcmd(command)

    def list_of_files(self):
        return [f for f, attr in self.ftp.mlsd() if attr['type'] == 'file']


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, fill='█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        fill        - Optional  : bar fill character (Str)
    """
    BAR_FORMAT = '%s |%s| %s%% %s'
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    length = CONSOLE_WIDTH - len(BAR_FORMAT % (prefix, '', percent, suffix)) - 2
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(BAR_FORMAT % (prefix, bar, percent, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total:
        print()


if __name__ == '__main__':
    main()
