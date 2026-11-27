class _Node:
    __slots__ = ("key", "value", "next")

    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.next = None


class HashTable:
    def __init__(self, capacity=8, max_load=0.75):
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError("capacity must be an integer")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if max_load is not None:
            if isinstance(max_load, bool) or not isinstance(max_load, (int, float)):
                raise TypeError("max_load must be a positive number or None")
            if max_load <= 0:
                raise ValueError("max_load must be positive")

        self.capacity = capacity
        self.max_load = max_load
        self._buckets = [None] * capacity
        self._size = 0

    def __len__(self):
        return self._size

    def iter_entries(self):
        for head in self._buckets:
            node = head
            while node is not None:
                yield node.key, node.value
                node = node.next

    @property
    def load_factor(self):
        return self._size / self.capacity

    @staticmethod
    def _index_for(key, capacity):
        value = 0
        for character in key:
            value = (value * 31 + ord(character)) % capacity
        return value

    def _index(self, key):
        return self._index_for(key, self.capacity)

    @staticmethod
    def _validate_key(key):
        if not isinstance(key, str):
            raise TypeError("key must be a string")

    def put(self, key, value):
        self._validate_key(key)
        index = self._index(key)
        node = self._buckets[index]

        if node is None:
            self._buckets[index] = _Node(key, value)
            self._size += 1
            self._grow_if_needed()
            return

        while True:
            if node.key == key:
                node.value = value
                return
            if node.next is None:
                node.next = _Node(key, value)
                self._size += 1
                self._grow_if_needed()
                return
            node = node.next

    def get(self, key):
        return self.get_with_count(key)[0]

    def get_with_count(self, key):
        self._validate_key(key)
        node = self._buckets[self._index(key)]
        comparisons = 0

        while node is not None:
            comparisons += 1
            if node.key == key:
                return node.value, comparisons
            node = node.next

        return None, comparisons

    def remove(self, key):
        self._validate_key(key)
        index = self._index(key)
        node = self._buckets[index]
        previous = None

        while node is not None:
            if node.key == key:
                if previous is None:
                    self._buckets[index] = node.next
                else:
                    previous.next = node.next
                self._size -= 1
                return True
            previous = node
            node = node.next

        return False

    def _grow_if_needed(self):
        if self.max_load is not None and self.load_factor > self.max_load:
            self._resize(self.capacity * 2)

    def _resize(self, new_capacity):
        buckets = [None] * new_capacity
        tails = [None] * new_capacity

        for head in self._buckets:
            node = head
            while node is not None:
                next_node = node.next
                node.next = None
                index = self._index_for(node.key, new_capacity)
                if buckets[index] is None:
                    buckets[index] = node
                else:
                    tails[index].next = node
                tails[index] = node
                node = next_node

        self._buckets = buckets
        self.capacity = new_capacity


_EMPTY = object()
_DELETED = object()


class LinearProbingHashTable:
    def __init__(self, capacity=8, max_load=0.75):
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError("capacity must be an integer")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if max_load is not None:
            if isinstance(max_load, bool) or not isinstance(max_load, (int, float)):
                raise TypeError("max_load must be a positive number or None")
            if max_load <= 0:
                raise ValueError("max_load must be positive")

        self.capacity = capacity
        self.max_load = max_load
        self._slots = [_EMPTY] * capacity
        self._size = 0

    def __len__(self):
        return self._size

    def iter_entries(self):
        for slot in self._slots:
            if slot is not _EMPTY and slot is not _DELETED:
                yield slot.key, slot.value

    def iter_slots(self):
        for index, slot in enumerate(self._slots):
            if slot is _EMPTY:
                yield index, None, None, False
            elif slot is _DELETED:
                yield index, None, None, True
            else:
                yield index, slot.key, slot.value, False

    @property
    def load_factor(self):
        return self._size / self.capacity

    def _index(self, key):
        return HashTable._index_for(key, self.capacity)

    def put(self, key, value):
        HashTable._validate_key(key)
        initial_index = self._index(key)
        first_deleted = None

        for offset in range(self.capacity):
            index = (initial_index + offset) % self.capacity
            slot = self._slots[index]
            if slot is _EMPTY:
                insertion_index = first_deleted if first_deleted is not None else index
                self._slots[insertion_index] = _Node(key, value)
                self._size += 1
                self._grow_if_needed()
                return
            if slot is _DELETED:
                if first_deleted is None:
                    first_deleted = index
            elif slot.key == key:
                slot.value = value
                return

        if first_deleted is not None:
            self._slots[first_deleted] = _Node(key, value)
            self._size += 1
            self._grow_if_needed()
            return

        raise OverflowError("hash table is full")

    def get(self, key):
        return self.get_with_count(key)[0]

    def get_with_count(self, key):
        HashTable._validate_key(key)
        initial_index = self._index(key)
        comparisons = 0

        for offset in range(self.capacity):
            index = (initial_index + offset) % self.capacity
            comparisons += 1
            slot = self._slots[index]
            if slot is _EMPTY:
                return None, comparisons
            if slot is not _DELETED and slot.key == key:
                return slot.value, comparisons

        return None, comparisons

    def probe_trace(self, key):
        HashTable._validate_key(key)
        initial_index = self._index(key)
        inspected_indices = []

        for offset in range(self.capacity):
            index = (initial_index + offset) % self.capacity
            inspected_indices.append(index)
            slot = self._slots[index]
            if slot is _EMPTY:
                return initial_index, tuple(inspected_indices), None
            if slot is not _DELETED and slot.key == key:
                return initial_index, tuple(inspected_indices), index

        return initial_index, tuple(inspected_indices), None

    def remove(self, key):
        HashTable._validate_key(key)
        initial_index = self._index(key)

        for offset in range(self.capacity):
            index = (initial_index + offset) % self.capacity
            slot = self._slots[index]
            if slot is _EMPTY:
                return False
            if slot is not _DELETED and slot.key == key:
                self._slots[index] = _DELETED
                self._size -= 1
                return True

        return False

    def _grow_if_needed(self):
        if self.max_load is not None and self.load_factor > self.max_load:
            self._resize(self.capacity * 2)

    def _resize(self, new_capacity):
        old_slots = self._slots
        self._slots = [_EMPTY] * new_capacity
        self.capacity = new_capacity
        self._size = 0

        for slot in old_slots:
            if slot is not _EMPTY and slot is not _DELETED:
                self._insert_without_resize(slot.key, slot.value)

    def _insert_without_resize(self, key, value):
        initial_index = self._index(key)
        for offset in range(self.capacity):
            index = (initial_index + offset) % self.capacity
            if self._slots[index] is _EMPTY:
                self._slots[index] = _Node(key, value)
                self._size += 1
                return
        raise OverflowError("hash table is full")
