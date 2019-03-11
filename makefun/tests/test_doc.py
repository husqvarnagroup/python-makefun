import sys
import pytest

try:  # python 3.3+
    from inspect import signature, Signature, Parameter
except ImportError:
    from funcsigs import signature, Signature, Parameter


from makefun import create_function, add_signature_parameters, remove_signature_parameters, with_signature, wraps

python_version = sys.version_info.major


@pytest.mark.parametrize('decorator', [False, True], ids="decorator={}".format)
@pytest.mark.parametrize('type', ['str', 'Signature'], ids="type={}".format)
def test_ex_nihilo(type, decorator):
    """ First example from the documentation: tests that we can generate a function from a string """

    # (1) define the signature.
    if type == 'str':
        func_sig = "foo(b, a=0)"
        func_name = None
    else:
        parameters = [Parameter('b', kind=Parameter.POSITIONAL_OR_KEYWORD),
                      Parameter('a', kind=Parameter.POSITIONAL_OR_KEYWORD, default=0), ]
        func_sig = Signature(parameters)
        func_name = 'foo'

    # (2) define the function implementation
    def func_impl(*args, **kwargs):
        """This docstring will be used in the generated function by default"""
        print("func_impl called !")
        return args, kwargs

    # (3) create the dynamic function
    if decorator:
        gen_func = with_signature(func_sig, func_name=func_name)(func_impl)
    else:
        gen_func = create_function(func_sig, func_impl, func_name=func_name)

    # first check the source code
    ref_src = "def foo(b, a=0):\n    return _call_handler_(b=b, a=a)\n"
    print("Generated Source :\n" + gen_func.__source__)
    assert gen_func.__source__ == ref_src

    # then the behaviour
    args, kwargs = gen_func(2)
    assert args == ()
    assert kwargs == {'a': 0, 'b': 2}


@pytest.mark.skipif(sys.version_info < (3, 0), reason="keyword-only signatures require python 3+")
def test_ex_nihilo_kw_only():
    """Same than ex nihilo but keyword only"""

    def func_impl(*args, **kwargs):
        """This docstring will be used in the generated function by default"""
        print("func_impl called !")
        return args, kwargs

    func_sig = "foo(b, *, a=0, **kwargs)"
    gen_func = create_function(func_sig, func_impl)

    ref_src = "def foo(b, *, a=0, **kwargs):\n    return _call_handler_(b=b, a=a, **kwargs)\n"
    print(gen_func.__source__)
    assert gen_func.__source__ == ref_src


def test_from_sig_wrapper():
    """ Tests that we can create a function from a Signature object """

    def foo(b, a=0):
        print("foo called: b=%s, a=%s" % (b, a))
        return b, a

    # capture the name and signature of existing function `foo`
    func_name = foo.__name__
    original_func_sig = signature(foo)
    print("Original Signature: %s" % original_func_sig)

    # modify the signature to add a new parameter
    params = list(original_func_sig.parameters.values())
    params.insert(0, Parameter('z', kind=Parameter.POSITIONAL_OR_KEYWORD))
    func_sig = original_func_sig.replace(parameters=params)
    print("New Signature: %s" % func_sig)

    # define the handler that should be called
    def func_impl(z, *args, **kwargs):
        print("func_impl called ! z=%s" % z)
        # call the foo function
        output = foo(*args, **kwargs)
        # return augmented output
        return z, output

    # create the dynamic function
    gen_func = create_function(func_sig, func_impl, func_name=func_name)

    # check the source code
    ref_src = "def foo(z, b, a=0):\n    return _call_handler_(z=z, b=b, a=a)\n"
    print("Generated Source :\n" + gen_func.__source__)
    assert gen_func.__source__ == ref_src

    # then the behaviour
    assert gen_func(3, 2) == (3, (2, 0))


def test_helper_functions():
    """ Tests that the signature modification helpers work """
    def foo(b, c, a=0):
        pass

    # original signature
    original_func_sig = signature(foo)
    assert str(original_func_sig) == '(b, c, a=0)'

    # let's modify it
    func_sig = add_signature_parameters(original_func_sig,
                                        first=Parameter('z', Parameter.POSITIONAL_OR_KEYWORD),
                                        last=(Parameter('o', Parameter.POSITIONAL_OR_KEYWORD, default=True),))
    func_sig = remove_signature_parameters(func_sig, 'b', 'a')
    assert str(func_sig) == '(z, c, o=True)'


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


def test_var_length():
    """Demonstrates how variable-length arguments are passed to the handler """

    # define the handler that should be called
    def func_impl(*args, **kwargs):
        """This docstring will be used in the generated function by default"""
        print("func_impl called !")
        return args, kwargs

    func_sig = "foo(a=0, *args, **kwargs)"
    gen_func = create_function(func_sig, func_impl)
    print(gen_func.__source__)
    assert gen_func(0, 1) == ((1,), {'a': 0})


def test_positional_only():
    """Tests that as of today positional-only signatures translate to bad strings """

    params = [Parameter('a', kind=Parameter.POSITIONAL_ONLY),
              Parameter('b', kind=Parameter.POSITIONAL_OR_KEYWORD)]

    assert str(Signature(parameters=params)) in {"(<a>, b)", "(a, /, b)"}


def test_with_signature():
    """ Tests that @with_signature works as expected """
    @with_signature("foo(a)")
    def foo(**kwargs):
        return 'hello'

    with pytest.raises(TypeError):
        foo()

    assert str(signature(foo)) == "(a)"
    assert foo('dummy') == 'hello'


def test_with_signature_none():
    """"""

    def foo(a):
        return a

    new = with_signature(None, func_name='f')(foo)

    assert new('hello') == 'hello'
    assert str(signature(new)) == "(a)"

    # check that the object was not wrapped
    assert new == foo
    assert new.__name__ == 'f'


def test_wraps(capsys):
    """ """
    # we want to wrap this function f to add some prints before calls
    def foo(a, b=1):
        return a + b

    # create our wrapper: it will have the same signature than f
    @wraps(foo)
    def enhanced_foo(*args, **kwargs):
        # we can very reliably access the value for 'b'
        print('hello!')
        print('b=%s' % kwargs['b'])
        # then call f as usual
        return foo(*args, **kwargs)

    assert enhanced_foo(1, 2) == 3
    assert enhanced_foo(b=0, a=1) == 1
    assert enhanced_foo(1) == 2

    with pytest.raises(TypeError):
        # does not print anything in case of error
        enhanced_foo()

    captured = capsys.readouterr()
    with capsys.disabled():
        print(captured.out)

    assert captured.out == """hello!
b=2
hello!
b=0
hello!
b=1
"""


def test_wraps_functools(capsys):
    """ same with functools.wraps """

    from functools import wraps

    # we want to wrap this function f to add some prints before calls
    def foo(a, b=1):
        return a + b

    # create our wrapper: it will have the same signature than f
    @wraps(foo)
    def enhanced_foo(*args, **kwargs):
        # we can very reliably access the value for 'b'
        print('hello!')
        print('b=%s' % kwargs['b'])
        # then call f as usual
        return foo(*args, **kwargs)

    # assert enhanced_foo(1, 2) == 3
    assert enhanced_foo(b=0, a=1) == 1
    # assert enhanced_foo(1) == 2

    with pytest.raises(KeyError):
        # prints a message in case of error
        enhanced_foo()

    captured = capsys.readouterr()
    with capsys.disabled():
        print(captured.out)

    assert captured.out == """hello!
b=0
hello!
"""