import turtle
from random import randint
wn = turtle.Screen()
wn.bgcolor("light blue")
wn.title("Turtle")
t1 = turtle.Turtle()

# move randomly until touching a position with x divisible by 10 and y divisible by 3

# draws a square
t1.setx(0)
t1.sety(0)
t1.color('red')
t1.fillcolor('yellow')
t1.begin_fill()

for i in range(4): # i = 0,1,2,3
    t1.setheading(90*i)
    t1.forward(100)
t1.end_fill()

# wait 1 sec

#t1.clear()

# draw a triangle
t1.setx(-100)
t1.sety(0)
t1.color('green')
t1.fillcolor('red')
t1.begin_fill()
size = 100

# order of headings
# 0 horizontal line
# 120 down
# 240 up

for i in range(3): # i in [0,1,2]
    t1.setheading(-120*i)
    t1.fd(size)
t1.end_fill()

'''
while int(t1.xcor()) % 5 != 0 or int(t1.ycor()) % 3 != 0:
    # chose a random direction and steps
    steps = randint(0,100)
    angle = randint(0,360)
    
    t1.right(angle)
    t1.forward(steps)
    
    t1.dot(10, "red")
    
    wn.delay(100)
    print(t1.xcor(), int(t1.xcor()), t1.ycor(), int(t1.ycor()))


#key = input("Press any key")
'''
t1.screen.mainloop()
turtle.done()