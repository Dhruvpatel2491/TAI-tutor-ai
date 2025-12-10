# example of error in representing 0.1 in floating point
# floating point values sometimes are represented innacurately on the computer (small errors)
# you should not compare two floating point values with ==. 
# compute the absolute value of their difference and compare it with a very small number (not 0)

v1 = 0.1
#user_input = float(input("Enter 1.0: "))

print("v1 = ", v1, "5-4.9=", 5-4.9)  #  "user_input=", user_input)

another_01 = 5 - 4.9

if abs(v1 - another_01) < 0.1e-6:
    print("Equal")
else:
    print("Not equal")