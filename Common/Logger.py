import os
import traceback
from datetime import datetime
from Models.LogLevel import LogLevel


class Logger:

    def __init__(self):
        self._verbose_level = int(os.environ.get("verbose_level"))

    def log_debug(self, msg):
        self.__log(msg, LogLevel.Debug)

    def log_info(self, msg):
        self.__log(msg, LogLevel.Info)

    def log_warn(self, msg):
        self.__log(msg, LogLevel.Warn)

    def log_error(self, msg):
        self.__log(msg, LogLevel.Error)

    def __log(self, msg: str, log_level: LogLevel):

        if log_level == LogLevel.Error:
            print(f'{msg}; LEVEL: {LogLevel.Error}')

        elif self._verbose_level >= 1 and log_level == LogLevel.Warn:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: {msg}')

        elif self._verbose_level >= 2 and log_level == LogLevel.Info:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: {msg}')

        elif self._verbose_level >= 3 and log_level == LogLevel.Debug:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: {msg}')
            traceback.print_stack()
