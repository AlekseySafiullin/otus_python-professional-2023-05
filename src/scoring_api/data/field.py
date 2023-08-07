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
                    None if self.nullable else 'Value cannot be None'
                )

            for is_valid_fn in is_valid_fn_queue[::-1]:
                is_valid, message = is_valid_fn(self, instance)
                if not is_valid:
                    return is_valid, message

            return True, None

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

    def __init__(self, required=False, nullable=False, not_empty=False):
        super().__init__(required=required, nullable=nullable)
        self.not_empty = not_empty

    def is_valid(self, instance):
        value_list = self.storage[instance]

        if not isinstance(value_list, list):
            return (
                False,
                f'{self.__class__.__name__} have to be list'
            )

        if not value_list and self.not_empty:
            return (
                False,
                f'{self.__class__.__name__} must not be empty'
            )

        for value in value_list:
            is_valid, message = self.item_type._value_is_valid(value)
            if not is_valid:
                return is_valid, message

        return True, None


class CharField(Field):
    def is_valid(self, instance):
        return self._value_is_valid(self.storage[instance])

    @classmethod
    def _value_is_valid(cls, value):
        if not isinstance(value, str):
            return False, f'For {cls.__name__} value must be str'
        
        return True, None


class ArgumentsField(Field):
    def is_valid(self, instance):
        value = self.storage[instance]

        try:
            json.dumps(value)
        except:
            return (
                False,
                f'For {self.__class__.__name__} value must be correct JSON'
            )

        return True, None


class EmailField(CharField):
    def is_valid(self, instance):
        value = self.storage[instance]

        if '@' not in value:
            return (
                False,
                f'For {self.__class__.__name__} value have to contain @'
            )

        return True, None 


class PhoneField(Field):
    def is_valid(self, instance):
        value = str(self.storage[instance])

        if not value.startswith('7') or not len(value) == 11:
            return (
                False,
                (
                    f'For {self.__class__.__name__} value have to starts with number'
                    f' 7 and and contain 11 digits'
                )
            )

        return True, None


class DateField(Field):
    FORMAT = '%d.%m.%Y'

    def to_date(self, value):
        if isinstance(value, (datetime, date)):
            return value

        return datetime.strptime(value, self.FORMAT).date()

    def is_valid(self, instance):
        try:
            self.to_date(self.storage[instance])
        except ValueError:
            return (
                False,
                (
                    f'For {self.__class__.__name__} value have to conform to '
                    f'format: {self.FORMAT}'
                )
            )

        return True, None


class BirthDayField(DateField):
    def is_valid(self, instance):
        value = self.to_date(self.storage[instance])
        now = date.today()

        if value > now or now.year - value.year > 70:
            return (
                False,
                (
                    f'For {self.__class__.__name__} value have to be actual and '
                    f'less then 70 years'
                )
            )

        return True, None


class IntField(Field):
    def is_valid(self, instance):
        return self._value_is_valid(self.storage[instance])

    @classmethod
    def _value_is_valid(cls, value):
        if not isinstance(value, int):
            return False, f'For {cls.__name__} value must be int'

        return True, None


class GenderField(IntField):
    CORRECT_VALUES = [0, 1, 2]

    def is_valid(self, instance):
        value = self.storage[instance]

        if value not in self.CORRECT_VALUES:
            return (
                False,
                (
                    f'For {self.__class__.__name__} have to match one of the '
                    f'values {self.CORRECT_VALUES}'
                )
            )

        return True, None


class ClientIDsField(ListField):
    item_type = IntField
