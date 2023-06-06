import logging
import statistics

from collections import namedtuple, defaultdict


RequestStatisticRow = namedtuple(
    'RequestStatisticRow',
    'request, count, time_queue, time_sum'
)
StatisticRow = namedtuple(
    'StatisticRow',
    'request, count, count_perc, time_sum, time_perc, time_avg, time_max,'
    ' time_med'
)


class StatisticCalculator:
    def __init__(self):
        self.logger = logging.getLogger(
            f'{self.__module__}.{self.__class__.__name__}'
        )

    def __call__(self, log, max_error_rate=50):
        result = []
        self.logger.info('Process requests data')

        (
            request_row_map,
            total_request_count,
            total_request_time_count
        ) = self._calculate_request_raw_map(log)

        if not log.total_line_count:
            self.logger.error('Empty log!')
            return result

        percent_parsing_errors = \
            ((log.total_line_count - log.parsed_line_count) * 100.0) / log.total_line_count

        if percent_parsing_errors > max_error_rate:
            self.logger.error(
                f'There are a lot of errors while parse log: '
                f'{log.parsed_line_count}/{log.total_line_count}'
                f'({percent_parsing_errors}%)'
            )
            return result

        self.logger.info(
            f'Processed {log.parsed_line_count}/{log.total_line_count} lines'
        )

        self.logger.info('Calculating statistic')

        for request_row in request_row_map.values():
            self.logger.debug(f'Process request {request_row.request}')

            result.append(StatisticRow(
                request=request_row.request,
                count=request_row.count,
                count_perc=(request_row.count * 100) / total_request_count,
                time_sum=request_row.time_sum,
                time_perc=(request_row.time_sum * 100.0) / total_request_time_count,
                time_avg=statistics.mean(request_row.time_queue),
                time_max=max(request_row.time_queue),
                time_med=statistics.median(request_row.time_queue)
            ))

        return result

    def _calculate_request_raw_map(self, log_row_it):
        request_row_map = {}
        total_request_count = 0
        total_request_time_count = 0

        for log_row in log_row_it:
            total_request_count += 1
            total_request_time_count += float(log_row.request_time)

            self.logger.debug(f'Calculate: {log_row.request}')

            request_row = request_row_map.setdefault(
                log_row.request,
                RequestStatisticRow(
                    request=log_row.request,
                    count=0,
                    time_queue=[],
                    time_sum=0
                )
            )
            request_row_map[log_row.request] = RequestStatisticRow(
                request=log_row.request,
                count=request_row.count + 1,
                time_queue=request_row.time_queue + [float(log_row.request_time)],
                time_sum=request_row.time_sum + float(log_row.request_time)
            )

        return request_row_map, total_request_count, total_request_time_count
