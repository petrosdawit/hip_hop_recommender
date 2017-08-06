from collections import defaultdict
from itertools import chain, groupby
from functools import reduce

class mapreduce:
    def parallelize(self, c, partitions):
        return _helper(c)

    def stop(self):
        pass

class _helper:
    def __init__(self, c):
        self._data = c

    def map(self, f):
        self._data = list(map(f, self._data))
        return self

    def flatMap(self, f):
        self._data = list(chain.from_iterable(map(f, self._data)))
        return self

    def filter(self, f):
        self._data = filter(f, self._data)
        return self

    def reduce(self, f):
        self._data = reduce(f, self._data)
        return self.collect()

    def sort_order(self, l, key):
        d = defaultdict(list)
        for item in l:
            d[key(item)].append(item)
        return [item for sublist in d.values() for item in sublist]

    def reduceByKey(self, f):
        self._data = map(lambda y: (y[0], reduce(f, map(lambda x: x[1], y[1]))),
            groupby(self.sort_order(self._data, lambda x: x[0]), lambda x: x[0]))
        return self

    def sortByKey(self, b):
        if b == True:
            self._data = sorted(list(self._data), key=lambda x: x[0])
        return self

    def collect(self):
        return self._data

    def count(self):
        return len(self._data)
