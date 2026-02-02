# metaclass_test.py

class metaclass(type):
    def __new__(cls, name, bases, dct):
        print("metaclass.__new__ called on", cls.__name__, name, bases, sorted(dct.keys()))
        print(f"{dct['var']=}")
        return super().__new__(cls, name, bases, dct)

class top(metaclass=metaclass):
    var = "top"
    def __init__(self):
        print("top.__init__")

class bottom(top):
    var = "bottom"
    def __init__(self):
        super().__init__()
        print("bottom.__init__")

