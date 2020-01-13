import time
import console

def main():
    test_console_size()
    for i in range(100):
        print(r'-\|/'[i%4], ' ', i+1, end='\r')
        time.sleep(0.2)

def test_console_size():
    width, height = console.getTerminalSize()
    assert width
    assert height
    assert width != 80, 'default value'


if __name__ == '__main__':
    main()
