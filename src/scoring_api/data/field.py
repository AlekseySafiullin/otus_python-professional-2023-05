import json

from weakref import WeakKeyDictionary


class Field:
    def __init__(self, required=False, nullable=False):
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

    def is_valid(self, instance):
        value = self.storage[instance]

        if not value and not self.nullable:
            return False

        return True


class CharField(Field):
    pass


class ArgumentsField(Field):
    def is_valid(self, instance):
        is_valid = super().is_valid(instance)

        if not is_valid:
            return is_valid

        value = self.storage[instance]

        try:
            json.dumps(value)
        except:
            return False

        return True


class EmailField(CharField):
    def is_valid(self, instance):
        is_valid = super().is_valid(instance)

        if not is_valid:
            return is_valid

        value = self.storage[instance]

        if '@' not in value:
            return False

        return True


class PhoneField(Field):
    pass


class DateField(Field):
    pass


class BirthDayField(Field):
    pass


class GenderField(Field):
    pass


class ClientIDsField(Field):
    pass
