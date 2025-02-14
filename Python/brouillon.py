def test():
    for i in range(3):
        yield i

a = test()

for i in a:
    print(i)