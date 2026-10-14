def valid_inn(prefix9: str) -> str:
    prefix9 = prefix9.zfill(9)[-9:]
    weights = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    check = sum(int(prefix9[i]) * weights[i] for i in range(9)) % 11 % 10
    return prefix9 + str(check)
