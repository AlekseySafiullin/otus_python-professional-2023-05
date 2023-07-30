import hashlib
import datetime
import logging

from collections import namedtuple

from ..scoring import get_score, get_interests

from .request import OnlineScoreRequest, ClientsInterestsRequest


SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


ResponseError = namedtuple('ResponseError', 'code, error')
ResponseMethod = namedtuple('ResponseMethod', 'code, response')
ResponseOnlineScore = namedtuple('ResponseOnlineScore', 'score')
class ResponseClientsInterests(dict):
    def _asdict(self):
        return self


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).hexdigest()
    else:
        digest = hashlib.sha512(request.account + request.login + SALT).hexdigest()
    if digest == request.token:
        return True
    return False


class Response:
    def __init__(self):
        self.logger = logging.getLogger(
            f'{self.__module__}.{self.__class__.__name__}'
        )

    def __call__(self, request):
        response = self._process_request(request)

    def _process_request(self, request):
        is_valid, message = request.is_valid()

        if not is_valid:
            self.logger.error(message)
            return ResponseError(
                code=INVALID_REQUEST,
                error=ERRORS[INVALID_REQUEST]
            )

        auth_is_success = check_auth(request)

        if not auth_is_success:
            return ResponseError(
                code=FORBIDDEN,
                error=ERRORS[INVALID_REQUEST]
            )

        if request.method == OnlineScoreRequest.request_name:
            return self._process_online_score_method(request)

        if request.method == ClientsInterestsRequest.request_name:
            return self._process_clients_interests_method(request)

        self.logger.error(f'Unknown method: {request.method}')
        return ResponseError(
            code=NOT_FOUND,
            error=ERRORS[NOT_FOUND]
        )

    def _process_online_score_method(self, request):
        self.logger.info('Process online score method')
        method = OnlineScoreRequest(
            **(request.arguments if request.arguments else {})
        )
        is_valid, message = method.is_valid()
        if not is_valid:
            return ResponseError(
                code=INVALID_REQUEST,
                error=message
            )

        if request.is_admin:
            return ResponseOnlineScore(
                score=int(ADMIN_SALT)
            )

        return ResponseOnlineScore(
            score=get_score(
                store=None,
                phone=method.phone,
                email=method.email,
                birthday=method.birthday,
                gender=method.gender,
                first_name=method.first_name,
                last_name=method.last_name
            )
        )

    def _process_clients_interests_method(self, request):
        self.logger.info('Process clients interests method')
        method = OnlineScoreRequest(
            **(request.arguments if request.arguments else {})
        )
        is_valid, message = method.is_valid()
        if not is_valid:
            return ResponseError(
                code=INVALID_REQUEST,
                error=message
            )

        return ResponseClientsInterests({
            client_id: get_interests(
                store=None,
                cid=client_id
            )
            for client_id in method.client_ids
        })
