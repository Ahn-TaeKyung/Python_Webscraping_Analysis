john = {'name':'John', 'age':30}
sub = {'math':90, 'science':85, 'history':78}
fruit = {'apple':3, 'banana':5}
print(f'나이: {john["age"]}')
print('과목들:', list(sub.keys()))
fruit['apple'] += 2
print(fruit)