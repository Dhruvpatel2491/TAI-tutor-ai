# this program finds the minimum integer value for which the sum from
# 1 to that value is greater than limit

# 1. read the value of limit
limit = int(input('Enter an int value > 1'))

# 2 & 3 init sum and num
sum = 0
num = 0

# 4. repeat

while sum <= limit:
    num = num + 1
    sum += num

# print the values of sum and num
print("The smallest value is", num)
print("The sum from 1 to ", num, " is ", sum)

