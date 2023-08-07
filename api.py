#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import uuid
import hashlib
import datetime
import logging

from collections import namedtuple
from optparse import OptionParser
from http.server import BaseHTTPRequestHandler, HTTPServer

from src.scoring_api.scoring import get_score, get_interests

from src.scoring_api.data.request import (MethodRequest, OnlineScoreRequest,
    ClientsInterestsRequest)


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


def sha512(data):
    return hashlib.sha512(data.encode('utf-8')).hexdigest()


def check_auth(request):
    if request.is_admin:
        digest = sha512(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT)
    else:
        digest = sha512(request.account + request.login + SALT)
    if digest == request.token:
        return True
    return False


class RequestHandler:
    def __init__(self, store, ctx):
        self.store = store
        self.ctx = ctx
        self.logger = logging.getLogger(
            f'{self.__module__}.{self.__class__.__name__}'
        )

    def __call__(self, request):
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
                error=ERRORS[FORBIDDEN]
            )

        if request.method == OnlineScoreRequest.request_name:
            response = self._process_online_score_method(request)
        elif request.method == ClientsInterestsRequest.request_name:
            response = self._process_clients_interests_method(request)
        else:
            self.logger.error(f'Unknown method: {request.method}')
            return ResponseError(
                code=NOT_FOUND,
                error=ERRORS[NOT_FOUND]
            )

        if isinstance(response, ResponseError):
            return response

        return ResponseMethod(
            code=OK,
            response=response
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

        self.ctx.update(method.ctx)

        if request.is_admin:
            score = int(ADMIN_SALT)
        else:
            score = get_score(
                store=self.store,
                phone=getattr(method, 'phone', None),
                email=getattr(method, 'email', None),
                birthday=getattr(method, 'birthday', None),
                gender=getattr(method, 'gender', None),
                first_name=getattr(method, 'first_name', None),
                last_name=getattr(method, 'last_name', None)
            )

        return dict(score=score)

    def _process_clients_interests_method(self, request):
        self.logger.info('Process clients interests method')
        method = ClientsInterestsRequest(
            **(request.arguments if request.arguments else {})
        )
        is_valid, message = method.is_valid()
        if not is_valid:
            return ResponseError(
                code=INVALID_REQUEST,
                error=message
            )

        self.ctx.update(method.ctx)

        return {
            client_id: get_interests(
                store=self.store,
                cid=client_id
            )
            for client_id in method.client_ids
        }


def method_handler(request, ctx, store):
    raw_response = RequestHandler(store=store, ctx=ctx)(
        MethodRequest(**request.get('body', {}))
    )

    response = raw_response._asdict()
    response, code = (
        response.get('response') or response.get('error'),
        response['code']
    )

    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path](
                        {"body": request, "headers": self.headers},
                        context,
                        self.store
                    )
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r))
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(
        filename=opts.log,
        level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S'
    )
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
