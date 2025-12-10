# cee-lo dice game
from random import randint

# 4 players
# each of them rolls a dice
# the player with highest dice number beomes the banker

# function definition 
def check_roll_pair(dice): # dice is the input value = int between 1 and 6
    if dice == 1:
        print("Banker losses: Two of a kind and 1")
        roll_state = "loss"
    elif dice == 6:
        print("Banker wins: Two of a kind and 6")
        roll_state = "win"
    else: # d3 = 2, or 3, or 4, or 5
        print("Banker rolled state")
        roll_state = "state"
    return roll_state  # (return value) value is sent back to the program that called this function
                       # indicates the end of the function 

def check_all_different(t1,t2,t3):
    # Instant win: 4-5-6;
    # Instant loss: 1-2-3
    # Dead roll: any other combination (re-roll)
    
    # find low, middle, high dice values among t1, t2, t3
    if t1 < t2:
        if t1 < t3:
            low = t1
            if t2 < t3:
                middle = t2
                high = t3
            else:
                middle = t2
                high = t3
        else: # t1 > t3 and t1 < t2
            low = t3
            middle = t1
            high = t2
    elif t2 < t3: # t1 > t2
        low = t2
        if t1 > t3:
            high = t1
            middle = t3
        else:
            high = t3
            middle = t1
    
    else: # t1 > t2 and t2 > t3
        low = t3
        middle = t2
        high = t1
    
    print(low, middle, high)
    roll_state = "different"
    return roll_state

start = print("Press any key to start the game")

# roll a die 4 times, and find the largest value

p1 = randint(1,6)
p2 = randint(1,6)
p3 = randint(1,6)
p4 = randint(1,6)

print("p1 rolled", p1)
print("p2 rolled", p2)
print("p3 rolled", p3)
print("p4 rolled", p4)

max_throw = p1
index_max_player = 1
if max_throw < p2:
   max_throw = p2
   index_max_player = 2

if max_throw < p3:
    max_throw = p3
    index_max_player = 3

if max_throw < p4:
    max_throw = p4
    index_max_player = 4

print("Player", index_max_player, "is the banker with the largest throw of", max_throw)

cont = input("Press any key to continue the game")

# the banker throws three more dices
d1 = randint(1,6)
d2 = randint(1,6)
d3 = randint(1,6)

print(f"The banker rolled: {d1}, {d2}, {d3}")

'''
Rules for banker roll:
Instant win: 4-5-6; 3-of-a-kind; Pair + 6
Instant loss: 1-2-3; Pair + 1
Set point: Pair + 2; Pair + 3; Pair + 4; Pair + 5
Dead roll: any other combination (re-roll)
'''

roll_state = 'dead' # roll_state take one of these values "win", or "loss" or "set"

if d1 == d2 and d2 == d3:
    print("Banker wins: Three of a kind")
    roll_state = "win"
elif d1 == d2: # Check if there is a pair 
    # call function check_roll_pair
    roll_state = check_roll_pair(d3)
elif d1 == d3:
    roll_state = check_roll_pair(d2)
elif d2 == d3:
    roll_state = check_roll_pair(d1)
else: # all dice are different
    roll_state = check_all_different(d1,d2,d3)
    print("All different")
