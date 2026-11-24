import unittest

from src.base62 import decode, encode


class Base62Test(unittest.TestCase):
    def test_zero_and_known_values(self):
        self.assertEqual(encode(0), "0")
        self.assertEqual(encode(61), "Z")
        self.assertEqual(encode(62), "10")
        self.assertEqual(encode(3844), "100")

    def test_encode_decode_round_trip(self):
        for number in (0, 1, 61, 62, 63, 125, 3843, 10**12):
            with self.subTest(number=number):
                self.assertEqual(decode(encode(number)), number)

    def test_invalid_values(self):
        with self.assertRaises(ValueError):
            encode(-1)
        with self.assertRaises(TypeError):
            encode("10")
        with self.assertRaises(ValueError):
            decode("")
        with self.assertRaises(ValueError):
            decode("!")


if __name__ == "__main__":
    unittest.main()
