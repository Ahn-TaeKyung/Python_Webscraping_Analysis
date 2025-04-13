def find_primes(start, end):
    prime = []
    for i in range(start, end + 1):
        if i > 1:
            for j in range(2, int(i // 2) + 1):
                if i % j == 0:
                    break
            else:
                prime.append(i)
    return prime

start = int(input('시작값:'))
end = int(input('끝값:'))
print(find_primes(start, end))