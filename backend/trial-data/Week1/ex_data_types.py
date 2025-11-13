var_int = 1
var_float = 1.0
var_char = '1'
print(var_int, "is of type ", type(var_int))
print(var_float, "is of type ", type(var_float))
print(var_char, "is of type ", type(var_char))

#var_float = var_int
print(var_int, "is of type ", type(var_int))
print(var_float, "is of type ", type(var_float))

var_bool = True
print(var_bool, "is of type ", type(var_bool))

var_result = var_int + var_float
print(var_result, "is of type ", type(var_result))

var_convert = int(var_char) # convert a data type to another data type
print(var_convert, "is of type ", type(var_convert))

# remainder (modulo) operator (%) = works only between integer data types
var_remainder = 5 % 3
print(var_remainder)
var_div_int = 5 // 3  # integer division = division between two integers => result is an
                                        # integer
print(var_div_int)

var_div_float = 4 /3 
print(var_div_float)
# var_char = '1'
var_char = str(int(var_char) + 1)
print(var_char, type(var_char))
#var_char += 3 # var_char = var_char + 3
#print(var_char)
