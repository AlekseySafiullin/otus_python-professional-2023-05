import json
import unittest
import filecmp
import shutil

from pathlib import Path
from tempfile import TemporaryDirectory
from string import Template

from log_analyzer import get_latest_log
from src.log_analyzer_tool.nginx_log import LogRow, NginxLog
from src.log_analyzer_tool.statistic_calculator import \
    StatisticRow, StatisticCalculator
from src.log_analyzer_tool.reporter import Reporter


REPO = Path(__file__).absolute().parent
DATA_DIR = REPO / 'DATA'


class TestLogAnalyzer(unittest.TestCase):
    LOG_CONTENT = [
        '1.169.137.128 -  - [30/Jun/2017:03:28:23 +0300] "GET /api/v2/banner/5960595 HTTP/1.1" 200 992 "-" "Configovod" "-" "1498782503-2118016444-4707-10488744" "712e90144abee9" 0.147',
        '1.199.4.96 -  - [30/Jun/2017:03:28:23 +0300] "GET /api/v2/banner/17572305/statistic/?date_from=2017-06-30&date_to=2017-06-30 HTTP/1.1" 200 115 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498782503-3800516057-4707-10488747" "c5d7e306f36c" 0.083',
    ]
    DIRTY_LOG_CONTENT = [
        '1.169.137.128 -  - [30/Jun/2017:03:28:23 +0300] "GET /api/v2/banner/5960595 HTTP/1.1" 200 992 "-" "Configovod" "-" "1498782503-2118016444-4707-10488744" "712e90144abee9" 0.147',
        '"GET /api/v2/banner/5960595 HTTP/1.1" 200 992 "-" "Configovod" "-" "1498782503-2118016444-4707-10488744" "712e90144abee9" 0.147',
        '123123123123',
    ]
    EXPECTED_ROW_QUEUE = (
        LogRow(
            remote_addr='1.169.137.128 -',
            remote_user='-',
            time_local='[30/Jun/2017:03:28:23 +0300]',
            request='"GET /api/v2/banner/5960595 HTTP/1.1"',
            status='200',
            body_bytes_sent='992',
            http_referer='"-"',
            http_user_agent='"Configovod"',
            http_x_forwarded_for='"-"',
            http_X_REQUEST_ID='"1498782503-2118016444-4707-10488744"',
            http_X_RB_USER='"712e90144abee9"',
            request_time='0.147'
        ),
        LogRow(
            remote_addr='1.199.4.96 -',
            remote_user='-',
            time_local='[30/Jun/2017:03:28:23 +0300]',
            request='"GET /api/v2/banner/17572305/statistic/?date_from=2017-06-30&date_to=2017-06-30 HTTP/1.1"',
            status='200',
            body_bytes_sent='115',
            http_referer='"-"',
            http_user_agent='"Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5"',
            http_x_forwarded_for='"-"',
            http_X_REQUEST_ID='"1498782503-3800516057-4707-10488747"',
            http_X_RB_USER='"c5d7e306f36c"', request_time='0.083'
        )
    )
    EXPECTED_STATISTIC_RAW_QUEUE = [
        StatisticRow(
            request='"GET /api/v2/banner/5960595 HTTP/1.1"',
            count=1,
            count_perc=50.0,
            time_sum=0.147,
            time_perc=63.913043478260875,
            time_avg=0.147,
            time_max=0.147,
            time_med=0.147
        ),
        StatisticRow(
            request='"GET /api/v2/banner/17572305/statistic/?date_from=2017-06-30&date_to=2017-06-30 HTTP/1.1"',
            count=1,
            count_perc=50.0,
            time_sum=0.083,
            time_perc=36.08695652173914,
            time_avg=0.083,
            time_max=0.083,
            time_med=0.083
        )
    ]

    def setUp(self):
        self._log_dir_obj = TemporaryDirectory(dir=REPO)
        self._result_dir_obj = TemporaryDirectory(dir=REPO)
        self._report_data = TemporaryDirectory(dir=REPO)

        self.log_dir = Path(self._log_dir_obj.name)
        self.result_dir = Path(self._result_dir_obj.name)
        self.report_data = Path(self._report_data.name)

        log_name_set = [
            'ddsadsdas.log',
            'nginx-access-ui.log-20170630.gz',
            'nginx-access-ui.log-20180630',
            'nginx-access-ui.log-063020180630'
        ]

        for name in log_name_set:
            path = self.log_dir / name
            path.touch()

        self.log_path = self.log_dir / 'nginx-access-ui.log'
        with self.log_path.open(mode='w', encoding='utf-8') as fp:
            for line in self.LOG_CONTENT:
                fp.write(f'{line}\n')

        self.dirty_log_path = self.log_dir / 'DIRTY__nginx-access-ui.log'
        with self.dirty_log_path.open(mode='w', encoding='utf-8') as fp:
            for line in self.DIRTY_LOG_CONTENT:
                fp.write(f'{line}\n')

        path = self.report_data / 'jquery.tablesorter.min.js'
        path.touch()

        template_report_path = DATA_DIR / 'report_data' / 'report_tpl.html'
        shutil.copy(str(template_report_path), str(self.report_data))

        with template_report_path.open(mode='r', encoding='utf-8') as fp:
            template = Template(fp.read())

        self.expected_report = self.result_dir / 'expected_report.html'
        with self.expected_report.open(mode='w', encoding='utf-8') as fp:
            fp.write(template.safe_substitute(
                table_json=json.dumps(self.EXPECTED_STATISTIC_RAW_QUEUE)
            ))

    def test__get_latest_log(self):
        nginx_log = get_latest_log(self.log_dir)

        self.assertIsNotNone(nginx_log)

        self.assertEqual(
            self.log_dir / 'nginx-access-ui.log-20180630',
            nginx_log.fs_path,
            msg='Failed discovering log dir'
        )

    def test__nginx_log(self):
        nginx_log = NginxLog(self.log_path)

        row_queue = tuple(nginx_log)

        self.assertTupleEqual(
            row_queue,
            self.EXPECTED_ROW_QUEUE,
            msg='Incorrect parsing nginx log'
        )

    def test__calculate_statistic(self):
        nginx_log = NginxLog(self.log_path)

        statistic_raw_queue = StatisticCalculator()(
            log=nginx_log,
            max_error_rate=50
        )

        self.assertListEqual(
            statistic_raw_queue,
            self.EXPECTED_STATISTIC_RAW_QUEUE,
            msg='Error while calculating statustic'
        )

    def test__calculate_statistic_dirty(self):
        nginx_log = NginxLog(self.dirty_log_path)

        statistic_row_queue = StatisticCalculator()(
            log=nginx_log,
            max_error_rate=50
        )

        self.assertListEqual(
            statistic_row_queue,
            [],
            msg='Nothing should have been read due to exceeded error count'
        )

    def test__make_report(self):
        nginx_log = NginxLog(self.log_path)

        statistic_raw_queue = StatisticCalculator()(
            log=nginx_log,
            max_error_rate=50
        )

        report_path = Reporter(self.report_data)(
            statistic_raw_queue,
            report_size=100,
            result_dir=self.result_dir,
            result_name='report.html'
        )

        self.assertTrue(filecmp.cmp(
            f1=report_path,
            f2=self.expected_report
        ))

    def tearDown(self):
        self._log_dir_obj.cleanup()
        self._result_dir_obj.cleanup()
        self._report_data.cleanup()


if __name__ == "__main__":
    unittest.main()
