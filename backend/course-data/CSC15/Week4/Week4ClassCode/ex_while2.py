# Write a while loop that computes the average of a series of  
# integer values (vInt) entered by the user. 
# The loop stops when user enters 0 or a negative number

''' use case:
input: 3,4,5, -1

inside in the program: 
    sum_so_far = 0  (, 3, 7, 12)
    count_nr = 0    (, 1, 2, 3)
    while new_nr > 0
        sum_so_far += new_nr
        count_nr += 1
        read new_nr
    avg = sum_so_far/count_nr 

    if count_nr is 0 check and do not divide otherwise you get 
    a runtime error
ouput: 4
'''

sum_so_far = 0  # sum of all # entered
count_nr = 0    # count of all # entered

# read the first value of new_nr
new_nr = int(input("enter an integer or 0 or negative to stop "))

while new_nr > 0:
    sum_so_far += new_nr
    count_nr += 1

    new_nr = int(input("enter an integer or 0  or negative to stop "))

print("sum = ", sum_so_far)
print("count = ", count_nr)

if count_nr > 0:
    avg = sum_so_far/count_nr
    print("avg = ", avg)
else:
    print("Sorry, you entered no numbers")