# cls_decorator_test.py

def decorator(cls):
    print("decorator called on", cls.__name__)
    return cls

@decorator
class top:
    def __init__(self):
        print("top.__init__")

class bottom(top):
    def __init__(self):
        super().__init__()
        print("bottom.__init__")

