varA = 'A'
varB = 10

if type(varA) == str or type(varB) == str: # question 1
    print('string involved')
elif varA < varB:
     print('smaller')
elif varA == varB:
     print('equal')
else:
     print('bigger')

'''
if type(varA) == str or type(varB) == str: # question 1
    print('string involved')
else:
    if varA < varB: # question 2
        print('smaller')
    else:
        if varA == varB: # question 3
            print('equal')
        else:
            print('bigger')
'''