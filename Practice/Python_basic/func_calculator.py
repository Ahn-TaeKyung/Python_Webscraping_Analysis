def calculator(a, b, op):
    if op == '+':
        return a + b
    elif op == '-':
        return a - b
    elif op == '*':
        return a * b
    elif op == '/':
        return a / b
    else:
        return 'op error'

a = int(input('첫 번째 수:'))
b = int(input('두 번째 수:'))
op = input('연산자:')
print(calculator(a, b, op))