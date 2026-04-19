#include <Python.h>

static PyObject *
native_hello(PyObject *self, PyObject *args)
{
    return PyUnicode_FromString("Hello from native C extension!");
}

static PyMethodDef NativeMethods[] = {
    {"hello", native_hello, METH_NOARGS, "Say hello from C."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef nativemodule = {
    PyModuleDef_HEAD_INIT,
    "_native",
    "Minimal C extension for package b",
    -1,
    NativeMethods
};

PyMODINIT_FUNC
PyInit__native(void)
{
    return PyModule_Create(&nativemodule);
}
