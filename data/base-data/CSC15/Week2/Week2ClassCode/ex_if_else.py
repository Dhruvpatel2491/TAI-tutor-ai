
ch = input("Enter a character ")

if ch >= 'A' and ch <= 'Z':  # ch is an upper letter case letter
    print('Upper case')
elif ch >= 'a' and ch <= 'z': # ch is a lower case letter
    print('Lower case')
elif ch >= '0' and ch <= '9': # ch is a digit
    print('Digit')
else: # ch is a special digit
    print('Special')
    
print(ch, 'has the code = ', ord(ch), 'and type ', type(ch))