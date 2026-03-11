import pytest
from toaster.core.registry import MemberRegistry
from toaster.languages.java.models import JavaClass, JavaMethod, JavaField

def test_dataclass_instantiation():
    reg = MemberRegistry()
    jc = JavaClass(
        ucid="com.test.MyClass",
        signature="public class MyClass",
        body="public class MyClass {}",
        start_line=1,
        registry=reg
    )
    assert jc.ucid == "com.test.MyClass"
    assert "MyClass" in jc.signature
    assert jc.end_line == 1  # 1 + body.count('\n') where count is 0

def test_id_generation():
    jm = JavaMethod(
        identifier="foo",
        scoped_identifier="MyClass.foo",
        return_type="void",
        umid="com.test.MyClass#foo()",
        signature="public void foo()",
        body="{}",
        dependency_names=[],
        start_line=5,
        parameters=[],
    )
    assert jm.id.startswith("M-")
    assert jm.arity == 0

def test_link_dependencies_local():
    reg = MemberRegistry()
    caller = JavaMethod(
        identifier="caller",
        scoped_identifier="MyClass.caller",
        return_type="void",
        umid="com.test.MyClass#caller()",
        signature="void caller()",
        body="callee();",
        dependency_names=[("callee()", "callee")],
        start_line=1,
        parameters=[],
        registry=reg
    )
    callee = JavaMethod(
        identifier="callee",
        scoped_identifier="MyClass.callee",
        return_type="void",
        umid="com.test.MyClass#callee()",
        signature="void callee()",
        body="{}",
        dependency_names=[],
        start_line=5,
        parameters=[],
        registry=reg
    )
    reg.add_method(caller)
    reg.add_method(callee)
    
    caller.resolve_dependencies([])
    
    assert len(caller.dependencies) == 1
    assert len(callee.inbound_dependencies) == 1
