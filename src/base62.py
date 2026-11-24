BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def encode(number):
    if isinstance(number, bool) or not isinstance(number, int):
        raise TypeError("number must be an integer")
    if number < 0:
        raise ValueError("number must be non-negative")
    if number == 0:
        return "0"

    result = []
    while number:
        number, remainder = divmod(number, 62)
        result.append(BASE62_ALPHABET[remainder])
    return "".join(reversed(result))


def decode(code):
    if not isinstance(code, str):
        raise TypeError("code must be a string")
    if not code:
        raise ValueError("code must not be empty")

    result = 0
    for character in code:
        if character not in BASE62_ALPHABET:
            raise ValueError("code contains a character outside the base62 alphabet")
        result = result * 62 + BASE62_ALPHABET.index(character)
    return result
