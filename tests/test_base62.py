import unittest

from src.base62 import decode, encode

class Base62Test(unittest.TestCase):
    def test_zero_and_known_values(self):
        self.assertEqual(encode(0), "0")
        self.assertEqual(encode(9), "9")
        self.assertEqual(encode(10), "a")
        self.assertEqual(encode(35), "z")
        self.assertEqual(encode(36), "A")
        self.assertEqual(encode(61), "Z")
        self.assertEqual(encode(62), "10")
        self.assertEqual(encode(3843), "ZZ")
        self.assertEqual(encode(3844), "100")

    def test_decode_known_values(self):
        self.assertEqual(decode("0"), 0)
        self.assertEqual(decode("a"), 10)
        self.assertEqual(decode("z"), 35)
        self.assertEqual(decode("A"), 36)
        self.assertEqual(decode("Z"), 61)
        self.assertEqual(decode("10"), 62)
        self.assertEqual(decode("ZZ"), 3843)
        self.assertEqual(decode("100"), 3844)

    def test_encode_decode_round_trip(self):
        for number in (0, 1, 61, 62, 63, 125, 3843, 10**12):
            with self.subTest(number=number):
                self.assertEqual(decode(encode(number)), number)

    def test_invalid_encode_values(self):
        with self.assertRaises(ValueError):
            encode(-1)

        for value in ("10", 1.5, True, False, None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    encode(value)

    def test_invalid_decode_values(self):
        for code in ("", "!", "a!"):
            with self.subTest(code=code):
                with self.assertRaises(ValueError):
                    decode(code)

        for code in (10, 1.5, True, None):
            with self.subTest(code=code):
                with self.assertRaises(TypeError):
                    decode(code)


if __name__ == "__main__":
    unittest.main()
