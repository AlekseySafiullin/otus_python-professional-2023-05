from . import field


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
REQUEST_METHOD_ONLINE_SCORE = 'online_score'
REQUEST_METHOD_CLIENTS_INTERESTS = 'clients_interests'


class RequestMeta(type):
    def __new__(cls, name, bases, attrs):
        __field_map = {
            name: value
            for name, value in attrs.items()
            if isinstance(value, field.Field)
        }
        __orig_init = attrs.get('__init__')

        def init(self, **kwargs):
            for key in set(__field_map) | set(kwargs):
                if key not in __field_map:
                    raise Exception(f'Unexpected argument: {key}')

                if key not in kwargs and __field_map[key].required:
                    raise Exception(f'Skipped required argument: {key}')

                if key in kwargs:
                    setattr(self, key, kwargs[key])

            if __orig_init:
                __orig_init(self, **kwargs)

        attrs['__init__'] = init
        attrs['_field_map'] = __field_map

        obj = super().__new__(cls, name, bases, attrs)

        return obj


class RequestBase(metaclass=RequestMeta):
    def __init__(self, *args, **kwargs):
        pass

    def is_valid(self):
        return all(
            getattr(self.__class__, name).is_valid(self)
            for name in self.__class__._field_map
            if hasattr(self, name)
        )


class ClientsInterestsRequest(RequestBase):
    client_ids = field.ClientIDsField(required=True)
    date = field.DateField(required=False, nullable=True)


class OnlineScoreRequest(RequestBase):
    first_name = field.CharField(required=False, nullable=True)
    last_name = field.CharField(required=False, nullable=True)
    email = field.EmailField(required=False, nullable=True)
    phone = field.PhoneField(required=False, nullable=True)
    birthday = field.BirthDayField(required=False, nullable=True)
    gender = field.GenderField(required=False, nullable=True)


REQUEST_METHOD_MAP = {
    REQUEST_METHOD_CLIENTS_INTERESTS: ClientsInterestsRequest,
    REQUEST_METHOD_ONLINE_SCORE: OnlineScoreRequest
}


class MethodRequest(RequestBase):
    account = field.CharField(required=False, nullable=True)
    login = field.CharField(required=True, nullable=True)
    token = field.CharField(required=True, nullable=True)
    arguments = field.ArgumentsField(required=True, nullable=True)
    method = field.CharField(required=True, nullable=False)

    def __init__(self, **kwargs):
        self._method = REQUEST_METHOD_MAP[self.method](**self.arguments)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN
