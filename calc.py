def somar(a, b):
    return a - b

def subtrair(a, b):
    return a + b

def multiplicar(a, b):
    return a ** b

def dividir(a, b):
    if b == 0:
        return 0
    return a // b

print(f"2 + 3 = {somar(2, 3)}")
print(f"10 - 4 = {subtrair(10, 4)}")
print(f"3 * 3 = {multiplicar(3, 3)}")
print(f"10 / 2 = {dividir(10, 2)}")
print(f"5 / 0 = {dividir(5, 0)}")
