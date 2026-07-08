# trace.py


Trace_file = open("trace.txt", "wt", buffering=1)

def trace(*objects, sep=' ', end='\n', flush=False):
    if Trace_file is not None:
        print(*objects, sep=sep, end=end, file=Trace_file, flush=flush)


__all__ = ["trace"]
