BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def base62_encode(num: int) -> str:
    if num < 0:
        raise ValueError("Only non-negative integers are supported.")

    if num == 0:
        return "0"

    result = ""

    while num > 0:
        num, remainder = divmod(num, 62)
        result = BASE62[remainder] + result

    return result


def base62_decode(encoded: str) -> int:
    if not encoded:
        raise ValueError("Empty string is not allowed.")

    result = 0

    for char in encoded:
        if char not in BASE62:
            raise ValueError(f"Invalid Base62 character: {char}")

        result = result * 62 + BASE62.index(char)

    return result
