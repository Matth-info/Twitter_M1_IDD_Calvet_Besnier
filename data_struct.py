import hashlib
import math 

def nextprime(n):
    p=n+1
    for i in range(2,p):
        if(p%i==0):
            p=p+1
    else:
        print(p,end=" ")

class HashTable:
	def __init__(self, nb_element):
		self.size = nextprime(math.floor(1.3 * nb_element))
		self.slots = [None] * self.size
		self.data = [None] * self.size
		
	def put(self, key, data):
		hashvalue = self.hashfunction(key, len(self.slots))

		if self.slots[hashvalue] == None:
			self.slots[hashvalue] = key
			self.data[hashvalue] = data
		else:
			if self.slots[hashvalue] == key:
				self.data[hashvalue] = data  # replace
			else:
				nextslot = self.rehash(hashvalue, len(self.slots))
				while self.slots[nextslot] != None and self.slots[nextslot] != key:
					nextslot = self.rehash(nextslot, len(self.slots))

				if self.slots[nextslot] == None:
					self.slots[nextslot] = key
					self.data[nextslot] = data
				else:
					self.data[nextslot] = data  # replace

	def hashfunction(self, key, size):
	     return key % size

	def rehash(self, oldhash, size):
		return (oldhash + 1) % size	
	    
	def get(self, key):
		startslot = self.hashfunction(key, len(self.slots))

		data = None
		stop = False
		found = False
		position = startslot
		while self.slots[position] != None and  not found and not stop:
			if self.slots[position] == key:
				found = True
				data = self.data[position]
			else:
				position = self.rehash(position, len(self.slots))
				if position == startslot:
					stop = True
		return data

	def __getitem__(self, key):
		return self.get(key)

	def __setitem__(self, key, data):
		self.put(key, data)	    

def hashFunction(x): # this function will hash k times the key 
    h = hashlib.sha256(str(x).encode('utf-8'))  # we'll use sha256 just for this example
    return int(h.hexdigest(), base=16)

class BloomFilter(object):
   
    def __init__(self, m, k, hashFun):
        self.m = m # size of the bit vector 
        self.vector = [0] * m
        self.k = k # number of hashfunctions computed to store an element 
        self.data = dict() 
        self.falsePositive = 0 # number of value store inside
        self.hashFun = hashFun
    
    def insert(self, key, value):
        current = key
        for i in range(self.k):
            current = self.hashFun(current) % self.m
            print(current)
            self.vector[current] = 1
        
        self.falsePositive += 1        
        self.data[key] = value 
        # last part store the value in to a data set
        # having access easily to the element store in the Bloom filter 
    
    def contains(self, key):
        current = key
        for i in range(self.k):
            current = (self.hashFun(current) % self.m)

            if (self.vector[current] != 1):
                return float(1) # never see this key
        
        return (1 - math.exp(-self.k*self.falsePositive/self.m))**self.k # How computing the false positive probability 
        
        # if each position in the bit vector are 1, we only can 
        # return a probability of the key being in the bloom filter.