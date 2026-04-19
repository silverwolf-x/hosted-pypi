"""Example compiled package B with a native C extension."""

__version__ = "2.1.1"


def hello():
    return f"Hello from package b v{__version__}"


def hello_native():
    """Call the native C extension."""
    from b import _native

    return _native.hello()
