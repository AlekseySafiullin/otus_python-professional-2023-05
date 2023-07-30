import json

from datetime import datetime, date
from weakref import WeakKeyDictionary


class FieldMeta(type):
    def __new__(cls, name, bases, attrs):
        is_valid_fn_queue = [attrs['is_valid']] if 'is_valid' in attrs else []
        for base in bases:
            is_valid_fn = getattr(base, 'is_valid', None)
            if is_valid_fn is not None:
                is_valid_fn_queue.append(is_valid_fn)

        def is_valid(self, instance):
            value = self.storage[instance]

            if value is None:
                return (
                    self.nullable,
                    '' if self.nullable else 'Value cannot be None'
                )

            for is_valid_fn in is_valid_fn_queue[::-1]:
                is_valid, message = is_valid_fn(self, instance)
                if not is_valid:
                    return is_valid, message

            return True, ''

        attrs['is_valid'] = is_valid

        obj = super().__new__(cls, name, bases, attrs)

        return obj


class Field(metaclass=FieldMeta):
    def __init__(self, required=False, nullable=False):
        self.name = None
        self.required = required
        self.nullable = nullable
        self.storage = WeakKeyDictionary()

    def __get__(self, instance, owner):
        if instance is None:
            return self

        if instance not in self.storage:
            raise AttributeError

        return self.storage[instance]

    def __set__(self, instance, value):
        self.storage[instance] = value

    @classmethod
    def _value_is_valid(cls, value):
        return None, None


class ListField(Field):
    item_type = None

    def is_valid(self, instance):
        value_list = self.storage[instance]

        if not hasattr(value_list, '__iter__'):
            return (
                False,
                f'{self.__class__.__name__} have to support __iter__ protocol'
            )

        for value in value_list:
            is_valid, message = self.item_type._value_is_valid(value)
            if not is_valid:
                return is_valid, message

        return True, ''


class CharField(Field):
    def is_valid(self, instance):
        return self._value_is_valid(self.storage[instance])

    @classmethod
    def _value_is_valid(cls, value):
        return (
            isinstance(value, str),
            f'For {cls.__name__} value must be str'
        )


class ArgumentsField(Field):
    def is_valid(self, instance):
        value = self.storage[instance]
        message = f'For {self.__class__.__name__} value must be correct JSON'

        try:
            json.dumps(value)
        except:
            return False, message

        return True, message


class EmailField(CharField):
    def is_valid(self, instance):
        value = self.storage[instance]
        message = f'For {self.__class__.__name__} value have to contain @'

        if '@' in value:
            return True, message

        return False, message


class PhoneField(Field):
    def is_valid(self, instance):
        value = str(self.storage[instance])
        message = (
            f'For {self.__class__.__name__} value have to starts with number 7 '
            f'and and contain 11 digits'
        )

        if value.startswith('7') and len(value) == 11:
            return True, message

        return False, message


class DateField(Field):
    FORMAT = '%d.%m.%Y'

    def to_date(self, value):
        if isinstance(value, (datetime, date)):
            return value

        return datetime.strptime(value, self.FORMAT).date()

    def is_valid(self, instance):
        message = (
            f'For {self.__class__.__name__} value have to conform to '
            f'format: {self.FORMAT}'
        )

        try:
            self.to_date(self.storage[instance])
        except ValueError:
            return False, message

        return True, message


class BirthDayField(DateField):
    def is_valid(self, instance):
        value = self.to_date(self.storage[instance])
        now = date.today()
        message = (
            f'For {self.__class__.__name__} value have to be actual and less '
            f'then 70 years'
        )

        if value > now or now.year - value.year > 70:
            return False, message

        return True, message


class IntField(Field):
    def is_valid(self, instance):
        return self._value_is_valid(self.storage[instance])

    @classmethod
    def _value_is_valid(cls, value):
        return (
            isinstance(value, int),
            f'For {cls.__name__} value must be int'
        )


class GenderField(IntField):
    CORRECT_VALUES = [0, 1, 2]

    def is_valid(self, instance):
        value = self.storage[instance]
        message = (
            f'For {self.__class__.__name__} have to match one of the values '
            f'{self.CORRECT_VALUES}'
        )

        return value in self.CORRECT_VALUES, message


class ClientIDsField(ListField):
    item_type = IntField
