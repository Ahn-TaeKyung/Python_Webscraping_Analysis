email = input('이메일 주소:')
if '@' in email and '.' in email:
    print('유효함')
else:
    print('유효하지 않음')