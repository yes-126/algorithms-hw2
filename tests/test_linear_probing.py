import unittest

from src.hash_table import LinearProbingHashTable


class LinearProbingHashTableTest(unittest.TestCase):
    def test_empty_lookup_counts_the_empty_slot(self):
        table = LinearProbingHashTable()

        self.assertIsNone(table.get("missing"))
        self.assertEqual(table.get_with_count("missing"), (None, 1))

    def test_collision_search_wraps_from_last_slot_to_zero(self):
        table = LinearProbingHashTable(capacity=8, max_load=None)
        for key in ("g", "o", "w"):
            table.put(key, key.upper())

        self.assertEqual(table._index("g"), 7)
        self.assertEqual(table.get_with_count("g"), ("G", 1))
        self.assertEqual(table.get_with_count("o"), ("O", 2))
        self.assertEqual(table.get_with_count("w"), ("W", 3))
        self.assertEqual(table.get_with_count("?"), (None, 4))

    def test_remove_leaves_tombstone_until_collision_chain_is_clear(self):
        table = LinearProbingHashTable(capacity=8, max_load=None)
        for key in ("g", "o", "w"):
            table.put(key, key.upper())

        self.assertTrue(table.remove("o"))
        self.assertEqual(table.get_with_count("w"), ("W", 3))

        table.put("?", "QUESTION")

        self.assertEqual(table.get_with_count("w"), ("W", 3))
        self.assertEqual(table.get_with_count("?"), ("QUESTION", 2))

    def test_replacing_existing_key_does_not_change_size(self):
        table = LinearProbingHashTable(capacity=4, max_load=None)
        table.put("a", "first")
        table.put("a", "updated")

        self.assertEqual(len(table), 1)
        self.assertEqual(table.get("a"), "updated")

    def test_full_table_rejects_new_key_but_allows_existing_key_update(self):
        table = LinearProbingHashTable(capacity=3, max_load=None)
        for key in ("a", "d", "g"):
            table.put(key, key.upper())

        self.assertEqual(len(table), 3)
        self.assertEqual(table.get_with_count("g"), ("G", 3))
        table.put("d", "UPDATED")
        self.assertEqual(table.get("d"), "UPDATED")
        with self.assertRaises(OverflowError):
            table.put("j", "J")

    def test_removed_slot_can_be_reused_when_table_is_full(self):
        table = LinearProbingHashTable(capacity=3, max_load=None)
        for key in ("a", "d", "g"):
            table.put(key, key.upper())

        self.assertTrue(table.remove("d"))
        table.put("j", "J")

        self.assertEqual(len(table), 3)
        self.assertEqual(table.get("a"), "A")
        self.assertEqual(table.get("g"), "G")
        self.assertEqual(table.get("j"), "J")

    def test_growth_rehashes_entries_and_preserves_capacity_after_removal(self):
        table = LinearProbingHashTable(capacity=4, max_load=0.5)
        table.put("a", 1)
        table.put("b", 2)
        self.assertEqual(table.capacity, 4)

        table.put("c", 3)

        self.assertEqual(table.capacity, 8)
        for key, value in (("a", 1), ("b", 2), ("c", 3)):
            self.assertEqual(table.get(key), value)
        table.remove("a")
        self.assertEqual(table.capacity, 8)

    def test_invalid_key_type_is_rejected(self):
        table = LinearProbingHashTable()

        with self.assertRaises(TypeError):
            table.put(1, "value")
        with self.assertRaises(TypeError):
            table.get_with_count(None)
        with self.assertRaises(TypeError):
            table.remove(False)


if __name__ == "__main__":
    unittest.main()
