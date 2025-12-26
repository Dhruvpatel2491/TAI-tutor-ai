# Write a loop that reads a character ch from the keyboard until that character is either 'q' or 'Q'. 
 
'''
pseudo-code:

read a character ch
if ch is not 'q' and ch is not 'Q' 
    read a character ch
if ch is not 'q' and ch is  not'Q' 
    read a character ch
-------

read a character ch 
while ch != 'q' and ch != 'Q'
    read a character ch

user enters: 
ch = 'a' condition is true
ch = 'b' condition is true
ch = 'q' condition is false

or 

'a'
'Q'
'

while ch is not 'q' or ch is not 'Q'

condition = true if ch != 'q' 
condition = true if ch != Q'
condition = false if ch == 'q'
condition = false if ch == 'Q'
 
e1: ch != 'q'    true if ch ! = 'q'
e2: ch ! = 'Q'   true if ch != 'Q'

e1 op e2 

e1 and e2 
T  and T  = T
everything else is False
F and F = F
F and T  = F
T and F = F

e1 or e2
T or any = T
any or T = T
F or F = F

'''

ch = input("Enter a character (q or Q to quit)")

while not (ch == 'q' or ch == 'Q'): # ch != 'q' and ch != 'Q':
    print("Not yet q or Q")
    ch = input("Enter a character (q or Q to quit)")

print("You entered", ch, "Thank you for playing")