def is_smaller(a, b):
    if a[0] != b[0]:
        return a[0] < b[0]
    return a[1] > b[1]


class MinHeap:
    def __init__(self):
        self.data = []

    def size(self):
        return len(self.data)

    def peek(self):
        return self.data[0]

    def push(self, item):
        self.data.append(item)
        i = len(self.data) - 1
        while i > 0:
            parent = (i - 1) // 2
            if is_smaller(self.data[i], self.data[parent]):
                self.data[i], self.data[parent] = self.data[parent], self.data[i]
                i = parent
            else:
                break

    def pop(self):
        top = self.data[0]
        last = self.data.pop()
        if self.data:
            self.data[0] = last
            i = 0
            n = len(self.data)
            while True:
                left = 2 * i + 1
                right = left + 1
                smallest = i
                if left < n and is_smaller(self.data[left], self.data[smallest]):
                    smallest = left
                if right < n and is_smaller(self.data[right], self.data[smallest]):
                    smallest = right
                if smallest == i:
                    break
                self.data[i], self.data[smallest] = self.data[smallest], self.data[i]
                i = smallest
        return top


def count_routes(rows):
    counts = {}
    for pickup, dropoff in rows:
        key = (pickup, dropoff)
        if key in counts:
            counts[key] += 1
        else:
            counts[key] = 1
    return counts


def top_k_routes(rows, k):
    counts = count_routes(rows)
    heap = MinHeap()
    for key in counts:
        item = (counts[key], key)
        if heap.size() < k:
            heap.push(item)
        elif is_smaller(heap.peek(), item):
            heap.pop()
            heap.push(item)
    ascending = []
    while heap.size() > 0:
        ascending.append(heap.pop())
    result = []
    i = len(ascending) - 1
    while i >= 0:
        result.append(ascending[i])
        i -= 1
    return result
