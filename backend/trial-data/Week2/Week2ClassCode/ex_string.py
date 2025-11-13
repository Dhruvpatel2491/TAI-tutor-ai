name = 'Alexander David'

print('name=', name, 'has type=', type(name) )
print("length of name (# chars in a string)= ", len(name))
print('First character in name is at index = ',0, 'name[0]= ', name[0])
print('Last character in name is at index = ', len(name)-1, 'name[len(name)-1]=',name[len(name)-1])
print('Last character in name is at index = ', -1, 'name[-1]=',name[-1])

print('String slicing - extract a substring from a string')
print('[index_first_character:index_last_character+1:step]')

xander = name[3::]
print(name[3], name[8])
print('xne = ', xander)

print('Reverse the whole string = name[-1::-1]', name[-1::-1])

print('type of name[0]= ', type(name[0]))

# this generates a syntax error
#name[0] = 'B' # produces an error because strings cannot be changed (immutable data type in Python)
#print(name)

name = 'B' + name[1:] # fine, create a new string with 'B' as first character and name from 1 to end as remaining
print(name)