# no_results_test.py

class No_results(Exception):
    pass

def gen(do_yield):
    if do_yield:
        yield 1
    else:
        raise No_results

print("True:")
print(list(gen(True)))

print("False:")
print(list(gen(False)))
