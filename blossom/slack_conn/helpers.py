import threading

# https://stackoverflow.com/a/59043636
def fire_and_forget(f, *args, **kwargs):
    def wrapped(*args, **kwargs):
        threading.Thread(target=f, args=(args), kwargs=kwargs).start()

    return wrapped
