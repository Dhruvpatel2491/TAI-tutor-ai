list_names = ["Mary", "John", "Alex"] # () a set, {} a dictionary
list_time_day = ['morning', 'afternoon', 'evening']

time_day = list_time_day[0] # index 0 means the first item in the list
for name in list_names: # name takes each value in list_names
    print('Good', time_day, name)
print()

time_day = list_time_day[1] # index 0 means the first item in the list
for name in list_names: # name takes each value in list_names
    print('Good', time_day, name)
print()

time_day = list_time_day[2] # index 0 means the first item in the list
for name in list_names: # name takes each value in list_names
    print('Good', time_day, name)
print()

for time_day in list_time_day:
    print(time_day)
    for name in list_names:
        print('Good', time_day, name) # body
    
