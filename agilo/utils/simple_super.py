#!/usr/bin/env python
# encoding: utf-8

"""
License: Public Domain
Authors: Martin Häcker <spamfaenger _at_ gmx _dot_ de>, 
         Felix Schwarz <felix _at_ schwarz-online _dot_ org>

Version 1.0.1

This is a simple piece of code born out of our frustration with the 
repetitiveness of calling overriden methods in python.
having to write

    super(TheCurrentClassThatImIn, self).the_method_that_im_currently_in(all, the, arguments, again)

every time you want to do that is just not DRY and makes refactoring
that much more tedious.

Wouldn't it be much coolder if you could just write self.super() instead? 
Yeah we thought so too.

In the superclass of the class where you want to use this
you need to make the superproxy available like this:

class SuperClass(object):
    super = SuperProxy()

Afterwards you can just use it in three forms in any method:
  - Auto-pick-up all available arguments and call the super method of the current method
    
    self.super()

  - Call super method of current method but with explicit arguments
    
    self.super(some_arguments)

  - Get a proxy for the superclass and call a specific method with specific arguments
    
    self.super.whatever_method(whatever, arguments)
    
    (self.super is the same as super(CurrentClass, self) but more DRY)

Known Bugs:
  - Works only for object subclasses (new style classes)

TODO:
  - Research how this all works in py3k
  - Package it all up nicely so it's super easy to use
  - Find a way so you can do something like from simple_super import 
    use_in_object to get every object enhanced by its niceness.
  - consider adding support for nested tupple unpacking?.
    Not sure if this is actually used, but I found a note about this in the docs 
    of the inspect module

Changelog
1.0.1 
  - do not add arguments if subclass uses self.super() and super class does 
    not get any arguments besides self.

1.0
  - initial release
"""

__all__ = ['SuperProxy']

import inspect
import sys
import traceback

# REFACT: move all the methods into SuperProxy

def find_class(instance, code):
    method_name = code.co_name
    for klass in reversed(inspect.getmro(instance.__class__)):
        if hasattr(klass, method_name):
            func = getattr(klass, method_name)
            # Objects special methods like __init__ are c-stuff that is only 
            # available to python as <slot_wrapper> which don't have im_func 
            # members, so I can't get the code object to find the actual implementation.
            # However this is not neccessary, as I only want to find methods
            # defined in python (the caller) so I  can just skip all <slot_wrappers>
            if hasattr(func, 'im_func'):
                other_code = func.im_func.func_code
                if id(code) == id(other_code):
                    return klass

def find_arguments_for_called_method():
    arg_names, varg_name, kwarg_name, arg_values = inspect.getargvalues(sys._getframe(3))
    # don't need self
    arg_names = arg_names[1:]
    
    vargs = []
    for name in arg_names:
        vargs.append(arg_values[name])
    
    if varg_name:
        vargs.extend(arg_values[varg_name])
    
    kwargs = {}
    if kwarg_name:
        kwargs = arg_values[kwarg_name]
    
    return vargs, kwargs

def arguments_for_super_method(super_method):
    if not hasattr(super_method, 'im_func'):
        # special treatment of object's __init__
        return ([], {})
    (args, varargs, varkw, defaults) = inspect.getargspec(super_method)
    if len(args) == 1 and varargs is None: # just self
        return ([], {})
    return find_arguments_for_called_method()


def call_super_implementation(self, *vargs, **kwargs):
    code = sys._getframe(1).f_code
    method = getattr(super(find_class(self, code), self), code.co_name)
    # always prefer explicit arguments
    if vargs or kwargs:
        return method(*vargs, **kwargs)
    else:
        vargs, kwargs = arguments_for_super_method(method)
        return method(*vargs, **kwargs)

def find_caller_self():
    arg_names, varg_name, kwarg_name, arg_values = inspect.getargvalues(sys._getframe(2))
    return arg_values[arg_names[0]]


class SuperProxy(object):
    "This has as few methods as possible, to serve as an ideal proxy."
    
    def __call__(self, *vargs, **kwargs):
        code = sys._getframe(1).f_code
        caller_self = find_caller_self()
        method = getattr(super(find_class(caller_self, code), caller_self), code.co_name)
        # always prefer explicit arguments
        if vargs or kwargs:
            return method(*vargs, **kwargs)
        else:
            vargs, kwargs = arguments_for_super_method(method)
            return method(*vargs, **kwargs)
    
    def __getattr__(self, method_name):
        code = sys._getframe(1).f_code
        caller_self = find_caller_self()
        return getattr(super(find_class(caller_self, code), caller_self), method_name)
    


class Super(object):
    super = SuperProxy()
    def __init__(self):
        self.did_call_super = False
    
    def method(self, *vargs, **kwargs):
        self.did_call_super = True
        return self
    
    def verify(self):
        assert self.did_call_super
    


import unittest
class SuperTests(unittest.TestCase):
    
    def test_no_arguments(self):
        class Upper(Super):
            def method(self):
                return self.super()
        class Lower(Upper):
            def method(self):
                return self.super()
        
        Lower().method().verify()
    
    def test_positional_argument(self):
        class Upper(Super):
            def method(self, arg, *vargs):
                assert 'fnord' == arg
                assert (23, 42) == vargs
                return self.super()
        class Lower(Upper):
            def method(self, arg, *vargs):
                self.super(arg, *vargs)
                return self.super()
        
        Lower().method('fnord', 23, 42).verify()
    
    def test_test_keyword_argument(self):
        class Upper(Super):
            def method(self, arg1, arg2, **kwargs):
                assert 'fnord' == arg1
                assert 23 == arg2
                assert {'foo': 'bar'}
                return self.super()
        class Lower(Upper):
            def method(self, arg1, arg2, **kwargs):
                self.super(arg1=arg1, arg2=arg2, **kwargs)
                return self.super()
        
        Lower().method(arg1='fnord', arg2=23, foo='bar').verify()
    
    def test_positional_variable_and_keyword_arguments(self):
        class Upper(Super):
            def method(self, arg, *vargs, **kwargs):
                assert 'fnord' == arg
                assert (23, 42) == vargs
                assert {'foo':'bar'} == kwargs
                return self.super()
        class Lower(Upper):
            def method(self, arg, *vargs, **kwargs):
                self.super(arg, *vargs, **kwargs)
                return self.super()
        
        Lower().method('fnord', 23, 42, foo='bar').verify()
    
    def test_default_arguments(self):
        class Upper(Super):
            def method(self, arg):
                assert 'fnord' == arg
                return self.super()
        class Lower(Upper):
            def method(self, arg='fnord'):
                self.super(arg)
                return self.super()
        
        Lower().method().verify()
    
    def test_can_change_arguments_to_super(self):
        class Upper(Super):
            def method(self, arg):
                assert 'fnord' == arg
                return self.super()
        class Lower(Upper):
            def method(self, arg):
                return self.super('fnord')
        
        Lower().method('foobar').verify()
    
    def test_super_has_fewer_arguments(self):
        class Upper(Super):
            def method(self, arg):
                assert 23 == arg
                return self.super()
        class Lower(Upper):
            def method(self, arg1, arg2):
                return self.super(arg1)
        
        Lower().method(23, 42).verify()
    
    def test_can_call_arbitrary_method_on_super(self):
        class Upper(Super):
            def foo(self):
                return self.super.method()
        class Lower(Upper):
            def bar(self):
                return self.super.foo()
        
        Lower().bar().verify()
    
    def test_can_use_super_in_init(self):
        # Objects special method like __init__ are special and can't be accessed like
        # normal methods. This test verifies that these methods can still be called.
        class Upper(object):
            super = SuperProxy()
            def __init__(self):
                self.super()
                self.did_call_super = True
        class Lower(Upper):
            def __init__(self):
                return self.super()
        
        self.assertTrue(Lower().did_call_super)
    
    def test_do_not_pass_arguments_by_default_if_lower_doesnt_have_any(self):
        # In order to have a nice API using self.super(), we need to be smart
        # so we can can detect the case where no arguments should be passed
        # as opposed to the case where all original arguments should be passed.
        class Upper(Super):
            def foo(self):
                return self.super.method()
        class Lower(Upper):
            def foo(self, default=None, *args, **kwargs):
                return self.super()
        
        Lower().foo().verify()




if __name__ == '__main__':
    unittest.main()

