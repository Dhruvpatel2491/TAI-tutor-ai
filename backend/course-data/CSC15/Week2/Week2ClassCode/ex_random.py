import math
import random
from random import randint

#random.seed(15)  # sets the seed for the random number generator algorithm
                  # same seed will always generate the same sequence of numbers
#print("Random state=", random.getstate())

print("Examples math library")
print("All functions in the math library", dir(math))
print("Example math expression", math.pow(math.pi, 5))

print("Example random")
print("Functions random library", dir(random))
print("Functions randint library", dir(randint)) # nothing interesting in here

for i in range(5): # repeat 10 times
    v_rand = randint(1,5)
    print(v_rand)

for i in range(5): # repeat 10 times
    v_rand = random.random()
    print(v_rand)
