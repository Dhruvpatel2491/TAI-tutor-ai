# print number 1 to 10 using a while loop

# start statement
nr = 1
while (nr <= 10): # while condition
    # body
    print(nr, end = ' ')
    # update statement  
    nr += 1
print()

print('\n Same problem but with a for loop')
# the same problem but with a for loop
for nr in range(1,11):
    print(nr, end = ' ')
print()

# print numbers from 0 to 100 in increments of a value entered by the user

step =  int(input("Enter the step size"))

for i in range(0, 101, step):
    print(i, end = ' ')
print()

