import sys
import time

def render(size, position):
    return "[" + (" " * position) + "=" + (" " * (size - position - 1)) + "]"

def draw(size, iterations, channel=sys.stdout, waittime=0.2):
    for index in range(iterations):
        n = index % (size*2)
        position = (n if n < size else size*2 - n - 1)
        bar = render(size, position)
        channel.write(bar + '\r')
        channel.flush()
        time.sleep(waittime)

if __name__ == '__main__':
    draw(6, 100, channel=sys.stdout)
