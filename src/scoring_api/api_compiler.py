from data.request import MethodRequest


# def is_valid(self):
#     print(
#         f'Valid: '
#         f'{(self.__class__.client_ids.is_valid(self), self.__class__.email.is_valid(self))}'
#     )


request_method_0 = MethodRequest(
    account='account-0',
    login='login-0',
    token='token-0',
    arguments={
        'client_ids': [1, 2, 3, 4, 5],
        'date': '23.07.2023'
    },
    method='clients_interests'
)

request_method_1 = MethodRequest(
    account='account-1',
    login='login-1',
    token='token-1',
    arguments={
        'first_name': 'first_name',
        'last_name': 'last_name',
        'email': 'email@gmail.com',
        'phone': '1111111',
        'birthday': '11.09.2023',
        'gender': 'Female'
    },
    method='online_score'
)

print((request_method_0.is_valid(), request_method_1.is_valid()))