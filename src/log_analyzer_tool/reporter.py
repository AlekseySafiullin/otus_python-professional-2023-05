import json
import shutil

from pathlib import Path
from string import Template


class Reporter:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir).resolve()

    def __call__(self, statistics_row_queue, report_size, result_dir, result_name):
        result_dir = Path(result_dir)

        if not result_dir.exists():
            result_dir.mkdir(parents=True)

        template_path = self.data_dir / 'report_tpl.html'
        with template_path.open(mode='r', encoding='utf-8') as fp:
            template = Template(fp.read())

        statistics_row_queue = self._process_statistics_row_queue(
            statistics_row_queue,
            report_size
        )

        path = result_dir / result_name
        with path.open(mode='w', encoding='utf-8') as fp:
            fp.write(template.safe_substitute(
                table_json=self._convert_data(statistics_row_queue)
            ))

        shutil.copyfile(
            src=self.data_dir / 'jquery.tablesorter.min.js',
            dst=result_dir / 'jquery.tablesorter.min.js'
        )

        return path

    def _process_statistics_row_queue(self, statistics_row_it, report_size):
        ordered_request_row_queue = sorted(
            statistics_row_it,
            key=lambda request_row: request_row.time_sum,
            reverse=True
        )
        return ordered_request_row_queue[:report_size]

    def _convert_data(self, statistics_row_it):
        return json.dumps(list(statistics_row_it))
