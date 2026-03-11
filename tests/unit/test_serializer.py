import pytest
from toaster.core.serializer import toast, Verbosity
from toaster.languages.java.models import JavaMethod

def test_dump_method_verbosity():
    jm = JavaMethod(
        identifier="foo",
        scoped_identifier="MyClass.foo",
        return_type="void",
        umid="com.test.MyClass#foo()",
        signature="public void foo()",
        body="{\n    System.out.println();\n}",
        dependency_names=[],
        start_line=10,
        parameters=[],
    )
    jm.description = "Prints a message."
    
    minimal_out = toast.dump_method(jm, Verbosity.MINIMAL)
    assert minimal_out.strip().endswith("public void foo()")
    assert "Prints a message" not in minimal_out
    
    simple_out = toast.dump_method(jm, Verbosity.SIMPLE)
    assert "Prints a message." in simple_out
    
    full_out = toast.dump_method(jm, Verbosity.FULL)
    assert "System.out.println()" in full_out
