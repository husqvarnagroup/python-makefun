import sys

try:  # python 3.3+
    from inspect import signature, Signature, Parameter
except ImportError:
    from funcsigs import signature, Signature, Parameter


from makefun import create_function

python_version = sys.version_info.major


def test_from_string():
    """ First example from the documentation: tests that we can generate a function from a string """

    # define the signature
    func_signature = "foo(b, a=0)"

    # define the handler that should be called
    def my_handler(*args, **kwargs):
        """This docstring will be used in the generated function by default"""
        print("my_handler called !")
        return args, kwargs

    # create the dynamic function
    dynamic_fun = create_function(func_signature, my_handler)

    # first check the source code
    ref_src = "def foo(b, a=0):\n    return _call_handler_(b=b, a=a)\n"
    print(dynamic_fun.__source__)
    assert dynamic_fun.__source__ == ref_src

    # then the behaviour
    args, kwargs = dynamic_fun(2)
    assert args == ()
    assert kwargs == {'a': 0, 'b': 2}

    # second case
    if python_version >= 3:
        func_signature = "foo(b, *, a=0, **kwargs)"
        dynamic_fun = create_function(func_signature, my_handler)

        ref_src = "def foo(b, *, a=0, **kwargs):\n    return _call_handler_(b=b, a=a, **kwargs)\n"
        print(dynamic_fun.__source__)
        assert dynamic_fun.__source__ == ref_src


def test_from_sig():
    """ Tests that we can create a function from a Signature object """

    # define the signature from an existing function
    def foo(b, a=0):
        pass
    func_signature = signature(foo)
    func_name = foo.__name__

    # define the handler that should be called
    def my_handler(*args, **kwargs):
        """This docstring will be used in the generated function by default"""
        print("my_handler called !")
        return args, kwargs

    # create the dynamic function
    dynamic_fun = create_function(func_signature, my_handler, func_name=func_name)

    # call it and check
    args, kwargs = dynamic_fun(2)
    assert args == ()
    assert kwargs == {'a': 0, 'b': 2}

    ref_src = "def foo(b, a=0):\n    return _call_handler_(b=b, a=a)\n"
    print(dynamic_fun.__source__)
    assert dynamic_fun.__source__ == ref_src


def test_injection():
    """ Tests that the function can be injected as first argument when inject_as_first_arg=True """
    def generic_handler(f, *args, **kwargs):
        print("This is generic handler called by %s" % f.__name__)
        # here you could use f.__name__ in a if statement to determine what to do
        if f.__name__ == "func1":
            print("called from func1 !")
        return args, kwargs

    # generate 2 functions
    func1 = create_function("func1(a, b)", generic_handler, inject_as_first_arg=True)
    func2 = create_function("func2(a, d)", generic_handler, inject_as_first_arg=True)

    func1(1, 2)
    func2(1, 2)
