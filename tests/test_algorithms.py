import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from algorithms import MinHeap, count_routes, top_k_routes


def brute_force(rows, k):
    counts = {}
    for row in rows:
        counts[row] = counts.get(row, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [(count, key) for key, count in ordered[:k]]


class HeapTests(unittest.TestCase):
    def test_pops_in_ascending_order(self):
        heap = MinHeap()
        for value in [5, 1, 9, 3, 7, 2, 8]:
            heap.push((value, (value, value)))
        popped = []
        while heap.size() > 0:
            popped.append(heap.pop()[0])
        self.assertEqual(popped, [1, 2, 3, 5, 7, 8, 9])

    def test_peek_returns_smallest(self):
        heap = MinHeap()
        heap.push((4, (1, 1)))
        heap.push((2, (2, 2)))
        self.assertEqual(heap.peek()[0], 2)


class RouteTests(unittest.TestCase):
    def test_count_routes(self):
        rows = [(1, 2), (1, 2), (3, 4)]
        self.assertEqual(count_routes(rows), {(1, 2): 2, (3, 4): 1})

    def test_top_k_small_example(self):
        rows = [(1, 2), (1, 2), (1, 2), (3, 4), (3, 4), (5, 6)]
        self.assertEqual(top_k_routes(rows, 2), [(3, (1, 2)), (2, (3, 4))])

    def test_k_larger_than_distinct_routes(self):
        rows = [(1, 2), (3, 4)]
        self.assertEqual(len(top_k_routes(rows, 10)), 2)

    def test_empty_input(self):
        self.assertEqual(top_k_routes([], 5), [])

    def test_matches_brute_force_on_random_data(self):
        random.seed(11)
        for k in [1, 3, 10, 25]:
            rows = [(random.randint(1, 15), random.randint(1, 15)) for _ in range(3000)]
            self.assertEqual(top_k_routes(rows, k), brute_force(rows, k))

    def test_ties_are_ordered_by_route(self):
        rows = [(5, 5), (2, 2), (9, 9), (2, 2), (5, 5), (9, 9)]
        self.assertEqual(top_k_routes(rows, 3), brute_force(rows, 3))


if __name__ == "__main__":
    unittest.main()
