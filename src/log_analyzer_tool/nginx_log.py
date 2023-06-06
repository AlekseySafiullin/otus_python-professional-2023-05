import re
import logging
import gzip

from pathlib import Path
from datetime import datetime
from collections import namedtuple
from functools import partial


LogRow = namedtuple(
    'LogRow',
    'remote_addr, remote_user, time_local, request,'
    'status, body_bytes_sent, http_referer, http_user_agent,'
    'http_x_forwarded_for, http_X_REQUEST_ID, http_X_RB_USER, request_time'
)


class NginxLog:
    NGINX_LOG_FILE_NAME_PTRN = 'nginx-access-ui.log-*'
    LOG_ROW_PTRN = re.compile(
        r'^(?P<remote_addr>.+)  (?P<remote_user>\S+) (?P<time_local>\[.+\])'
        r' (?P<request>\".+\") (?P<status>\d+) (?P<body_bytes_sent>\d+)'
        r' (?P<http_referer>\".+\") (?P<http_user_agent>\".+\")'
        r' (?P<http_x_forwarded_for>\".+\") (?P<http_X_REQUEST_ID>\".+\")'
        r' (?P<http_X_RB_USER>\".+\") (?P<request_time>\d+\.?\d*)'
    )

    def __init__(self, fs_path):
        self.fs_path = Path(fs_path)
        self.logger = logging.getLogger(
            f'{self.__module__}.{self.__class__.__name__}'
        )
        self.raw_date, self.date = self._parse_date()
        self.total_line_count = None
        self.parsed_line_count = None

    def __iter__(self):
        self.total_line_count = 0
        self.parsed_line_count = 0

        return self._read(self.fs_path)

    def _parse_date(self):
        date_ptrn_queue = ['%Y%m%d']

        if self.fs_path.suffix == '.gz':
            raw_date = self.fs_path.stem.rpartition('-')[2]
        else:
            raw_date = self.fs_path.name.rpartition('-')[2]

        for date_ptrn in date_ptrn_queue:
            try:
                return raw_date, datetime.strptime(raw_date, date_ptrn)
            except ValueError:
                self.logger.warning(f'Incorrect datetime format: {raw_date}')
                continue

        return raw_date, None

    def _read(self, path):
        path = Path(path)

        if path.suffix == '.gz':
            _open = partial(gzip.open, filename=path, mode='rt', encoding='utf-8')
        else:
            _open = partial(path.open, mode='r')

        with _open() as fp:
            for line in fp:
                line = line.strip()

                if not line:
                    continue

                self.total_line_count += 1

                row = self._parse_line(line)
                if row is None:
                    self.logger.warning(f'Failed parse line: {line}')
                    continue

                self.parsed_line_count += 1
                yield row

    def _parse_line(self, line):
        match = self.LOG_ROW_PTRN.match(line)

        if match is not None:
            return LogRow(**match.groupdict())
