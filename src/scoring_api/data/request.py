from functools import lru_cache

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
        __field_map = {}
        for name, value in attrs.items():
            if not isinstance(value, field.Field):
                continue
            value.name = name
            __field_map[name] = value

        __orig_init = attrs.get('__init__')

        def init(self, **kwargs):
            for key in set(__field_map) | set(kwargs):
                if key not in __field_map:
                    raise Exception(f'Unexpected argument: {key}')

                # if key not in kwargs and __field_map[key].required:
                #     raise Exception(f'Skipped required argument: {key}')

                if key in kwargs:
                    setattr(self, key, kwargs[key])

            if __orig_init:
                __orig_init(self, **kwargs)

        attrs['__init__'] = init
        attrs['_field_map'] = __field_map

        obj = super().__new__(cls, name, bases, attrs)

        return obj


class RequestBase(metaclass=RequestMeta):
    request_name = None

    def __init__(self, *args, **kwargs):
        pass

    def is_valid(self):
        for name, field in self.__class__._field_map.items():
            if not hasattr(self, name):
                if field.required:
                    return False, f'Missing required field: {name}'
                continue

            is_valid, message = field.is_valid(self)

            if not is_valid:
                return is_valid, message

        return True, None

    @property
    def ctx(self):
        return dict()


class ClientsInterestsRequest(RequestBase):
    request_name = 'clients_interests'

    client_ids = field.ClientIDsField(required=True, not_empty=True)
    date = field.DateField(required=False, nullable=True)

    @property
    def ctx(self):
        return dict(nclients=len(self.client_ids))


class OnlineScoreRequest(RequestBase):
    request_name = 'online_score'

    first_name = field.CharField(required=False, nullable=True)
    last_name = field.CharField(required=False, nullable=True)
    email = field.EmailField(required=False, nullable=True)
    phone = field.PhoneField(required=False, nullable=True)
    birthday = field.BirthDayField(required=False, nullable=True)
    gender = field.GenderField(required=False, nullable=True)

    def is_valid(self):
        is_valid, message = super().is_valid()
        if not is_valid:
            return is_valid, message

        required_field_name_set_queue = [
            (self.__class__.phone.name, self.__class__.email.name),
            (self.__class__.first_name.name, self.__class__.last_name.name),
            (self.__class__.gender.name, self.__class__.birthday.name),
        ]
        required_field_pair_map = {
            ' and '.join(name_set): all(
                getattr(self, name, None) is not None
                for name in name_set
            )
            for name_set in required_field_name_set_queue
        }
        is_valid = any(required_field_pair_map.values())
        if not is_valid:
            return (
                is_valid,
                f'Required field combinations missing: '
                f'{" OR ".join(required_field_pair_map)}'
            )

        return True, None

    @property
    def ctx(self):
        return dict(
            has=list(
                name
                for name in self.__class__._field_map
                if getattr(self, name, None) is not None
            )
        )


class MethodRequest(RequestBase):
    account = field.CharField(required=False, nullable=True)
    login = field.CharField(required=True, nullable=True)
    token = field.CharField(required=True, nullable=True)
    arguments = field.ArgumentsField(required=True, nullable=True)
    method = field.CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN
