#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging

import argparse

from pathlib import Path

from src.log_analyzer_tool.nginx_log import NginxLog
from src.log_analyzer_tool.statistic_calculator import StatisticCalculator
from src.log_analyzer_tool.reporter import Reporter


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';


REPO = Path(__file__).absolute().parent
DATA_DIR = REPO / 'DATA'
RESULT_DIR = REPO / 'results'


parser = argparse.ArgumentParser(description='Nginx log statistic utility')
parser.add_argument(
    '--config',
    help='path to config file',
    type=Path,
    default=DATA_DIR / 'config.json'
)
parser.add_argument(
    '--max_error_rate',
    help='Maximum allowable error rate',
    type=float
)
#TODO Удалить уровень DEBUG
parser.add_argument(
    '--log_level',
    choices=list(map(
        logging.getLevelName, [logging.INFO, logging.ERROR, logging.DEBUG]
    )),
    help='Log level'
)
args = parser.parse_args()


config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


LOGGER_FORMAT = '%(asctime)s %(levelname)-8s %(message)s'


logging.basicConfig(format=LOGGER_FORMAT, level=args.log_level)


logger = logging.getLogger(__name__)


def get_latest_log(log_dir):
    log_dir = Path(log_dir).resolve()

    nginx_log_queue = []
    for fs_path in log_dir.glob(NginxLog.NGINX_LOG_FILE_NAME_PTRN):
        nginx_log = NginxLog(fs_path)

        if nginx_log.date is None:
            continue

        nginx_log_queue.append(nginx_log)

    ordered_nginx_log_queue = sorted(
        nginx_log_queue,
        key=lambda nginx_log: nginx_log.date,
    )

    if ordered_nginx_log_queue:
        return ordered_nginx_log_queue[-1]

    return None


def main():
    try:
        with args.config.resolve().open(mode='r', encoding='utf-8') as fp:
            outer_config = json.load(fp)
    except:
        logger.exception('Config parsing failed.')
        return

    target_config = {
        key: outer_config.get(key, value)
        for key, value in config.items()
    }
    logger.debug(f'Target config: {target_config}')

    log = get_latest_log(target_config['LOG_DIR'])
    if log is None:
        logger.warning('Nginx log file not found')
        return

    logger.info(f'Log: {log.fs_path}')

    report_path = RESULT_DIR / f'report-{log.date.strftime("%Y.%m.%d")}.html'
    if report_path.exists():
        logger.warning('Report already exists!')
        return

    logger.info('Stat collecting statistics')

    statistic_calculator = StatisticCalculator()
    statistics_row_queue = statistic_calculator(
        log,
        max_error_rate=args.max_error_rate
    )

    if statistics_row_queue:
        logger.info('Generating report')
        Reporter(DATA_DIR / 'report_data')(
            statistics_row_queue,
            target_config['REPORT_SIZE'],
            result_dir=report_path.parent,
            result_name=report_path.name
        )
        logger.info(f'Report saved to: {report_path}')


if __name__ == "__main__":
    try:
        main()
    except:
        logger.exception('Unexpected error!')
