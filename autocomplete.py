from pprint import pprint
from functools import reduce
from queue import PriorityQueue
import sys

class Trie(object):

    def __init__(self):
        self._children = {}
        self._bool = False

    def insert(self, word):
        '''
        Parameters:
            Input: word
            Output: None
        Purpose:
            Insert word into the trie and set the flag to true
        '''
        for char in word:
            if char not in self._children:
                self.add(char)
            self = self._children[char]
        self._bool = True

    def contains(self, word):
        '''
        Parameters:
            Input: word
            Output: None
        Purpose:
            Check if the word in the children and then return the boolean flag
        '''
        for char in word:
            if char not in self._children:
                return False
            self = self._children[char]
        return self._bool

    def add(self, char):
        '''
        Parameters:
            Input: prefix
            Output: list of all the suffixes
        Purpose:
        '''
        self._children[char] = Trie()

    def all_suffixes(self, prefix):
        '''
        Parameters:
            Input: prefix
            Output: list of all the suffixes
        Purpose:
            Check for the boolean flag first and then using functional programming return the list of children
            that have the suffix to the prefix
        '''
        results = set()
        if self._bool:
            results.add(prefix)
        if not self._children:
            return results
        output = []
        return reduce(lambda a, b: a | b, [self.all_suffixes(prefix + char) for (char, self) in self._children.items()]) | results

    def edit_distance(self, string1, string2):
        '''
        Parameters:
            Input: 2 strings
            Output: edit distance value
        Purpose:
            Implemenetation of the Levenshtein's edit distance formula
        '''
        string1 = " " + string1
        string2 = " " + string2
        edit_distance_array = [ [ 0 for x in range(0,len(string2))] for y in range(0,len(string1))]
        for i in range(1,len(string1)):
            edit_distance_array[i][0] = i
        for j in range(1,len(string2)):
            edit_distance_array[0][j] = j
        for i in range(1,len(string1)):
            for j in range(1,len(string2)):
                addition = 0
                if string1[i] != string2[j]:
                    addition = 1
                edit_distance_array[i][j] = min(edit_distance_array[i-1][j]+1, edit_distance_array[i][j-1]+1, edit_distance_array[i-1][j-1]+addition)
        return edit_distance_array[-1][-1]

    def autocomplete(self, prefix, song_dic):
        '''
        Parameters:
            Input: prefix
            Output: ordered list of suggestions based off edit_distance from prefix for word
        Purpose:
            Get all the suffixes from all_suffixes then order the words with a priority queue by edit distance.
            From there, return a list by popping from the queue
        '''
        for char in prefix:
            if char not in self._children:
                return set()
            self = self._children[char]
        suggestions = list(self.all_suffixes(prefix))
        pq = PriorityQueue()
        for song in suggestions:
            pq.put((self.edit_distance(prefix, song), song))
        suggestions_ordered = []
        for i in range(pq.qsize()):
            suggestions_ordered.append(song_dic[pq.get()[1]])
        return suggestions_ordered

if __name__ == '__main__':
    prefix = sys.argv[1]
    song_dic = {}
    t = Trie()
    with open('data/song_names.txt', 'r') as f:
        for line in f:
            arr = line.split(',')
            t.insert(arr[1].lower())
            if arr[1] not in song_dic:
                song_dic[arr[1].lower()] = [arr]
            else:
                song_dic[arr[1].lower()].extend([arr])
    pprint(t.autocomplete(prefix.lower(), song_dic))
