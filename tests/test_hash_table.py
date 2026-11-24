import unittest

from src.hash_table import HashTable


class HashTableTest(unittest.TestCase):
    def test_empty_lookup_and_comparison_count(self):
        table = HashTable()

        self.assertIsNone(table.get("missing"))
        self.assertEqual(table.get_with_count("missing"), (None, 0))

    def test_insert_lookup_and_replace(self):
        table = HashTable()

        table.put("key", "first")
        self.assertEqual(table.get("key"), "first")

        table.put("key", "updated")
        self.assertEqual(table.get("key"), "updated")

    def test_collisions_are_searched_and_counted(self):
        table = HashTable()
        for key in ("a", "i", "q"):
            table.put(key, key.upper())

        self.assertEqual(table.get_with_count("a"), ("A", 1))
        self.assertEqual(table.get_with_count("i"), ("I", 2))
        self.assertEqual(table.get_with_count("q"), ("Q", 3))
        self.assertEqual(table.get_with_count("y"), (None, 3))

    def test_removing_each_collision_preserves_other_entries(self):
        for removed_key in ("a", "i", "q"):
            with self.subTest(removed_key=removed_key):
                table = HashTable()
                for key in ("a", "i", "q"):
                    table.put(key, key.upper())

                self.assertTrue(table.remove(removed_key))
                self.assertIsNone(table.get(removed_key))
                for key in ("a", "i", "q"):
                    if key != removed_key:
                        self.assertEqual(table.get(key), key.upper())

    def test_remove_reports_whether_key_existed(self):
        table = HashTable()
        table.put("key", "value")

        self.assertTrue(table.remove("key"))
        self.assertFalse(table.remove("key"))

    def test_replacing_existing_key_does_not_increase_item_count(self):
        table = HashTable()
        for key in ("a", "b", "c", "d", "e", "f"):
            table.put(key, key)

        table.put("a", "updated")

        self.assertEqual(table.capacity, 8)
        self.assertEqual(table.get("a"), "updated")

    def test_default_capacity_grows_after_load_exceeds_threshold(self):
        table = HashTable()
        for key in ("a", "b", "c", "d", "e", "f"):
            table.put(key, key)
        self.assertEqual(table.capacity, 8)

        table.put("g", "g")

        self.assertEqual(table.capacity, 16)
        for key in ("a", "b", "c", "d", "e", "f", "g"):
            self.assertEqual(table.get(key), key)

    def test_custom_max_load_controls_growth(self):
        table = HashTable(capacity=4, max_load=0.5)
        table.put("a", 1)
        table.put("b", 2)
        self.assertEqual(table.capacity, 4)

        table.put("c", 3)

        self.assertEqual(table.capacity, 8)
        self.assertEqual(table.get("a"), 1)
        self.assertEqual(table.get("b"), 2)
        self.assertEqual(table.get("c"), 3)

    def test_none_max_load_disables_growth(self):
        table = HashTable(capacity=8, max_load=None)

        for number in range(40):
            table.put(f"key-{number}", number)

        self.assertEqual(table.capacity, 8)
        for number in range(40):
            self.assertEqual(table.get(f"key-{number}"), number)

    def test_removing_items_does_not_shrink_capacity(self):
        table = HashTable()
        for key in ("a", "b", "c", "d", "e", "f", "g"):
            table.put(key, key)
        self.assertEqual(table.capacity, 16)

        for key in ("a", "b", "c", "d", "e", "f", "g"):
            table.remove(key)

        self.assertEqual(table.capacity, 16)


if __name__ == "__main__":
    unittest.main()
