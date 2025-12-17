# imghdr_fix.py
import sys
import types

imghdr = types.ModuleType('imghdr')

def what(file, h=None):
    return None

imghdr.what = what
imghdr.test = lambda *args, **kwargs: None
imghdr.tests = []

sys.modules['imghdr'] = imghdr
print("imghdr фикс применен")