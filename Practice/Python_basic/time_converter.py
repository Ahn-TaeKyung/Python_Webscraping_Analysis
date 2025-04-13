time = 12345
h = time // 3600
temp = time % 3600
m = temp // 60
s = temp % 60
print(f'{time}초는 {h}시간 {m}분 {s}초 입니다.')