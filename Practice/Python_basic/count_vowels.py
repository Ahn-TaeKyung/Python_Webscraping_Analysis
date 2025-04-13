str = 'Python is awesome'
vowel = 'aeiou'
cnt = 0
for char in str:
    if char in vowel:
        cnt += 1
print('모음 개수:',cnt)