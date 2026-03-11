import pytest
from toaster.core.registry import MemberRegistry
from toaster.languages.csharp.models import CSharpClass, CSharpMethod, CSharpField

def test_dataclass_instantiation():
    reg = MemberRegistry()
    jc = CSharpClass(
        ucid="TestNamespace.MyClass",
        signature="public class MyClass",
        body="public class MyClass {}",
        start_line=1,
        registry=reg
    )
    assert jc.ucid == "TestNamespace.MyClass"
    assert "MyClass" in jc.signature
    assert jc.end_line == 1  # 1 + body.count('\n') where count is 0

def test_id_generation():
    jm = CSharpMethod(
        identifier="Foo",
        scoped_identifier="MyClass.Foo",
        return_type="void",
        umid="TestNamespace.MyClass#Foo()",
        signature="public void Foo()",
        body="{ }",
        dependency_names=[],
        start_line=5,
        parameters=[],
    )
    assert jm.id.startswith("M-")
    assert jm.arity == 0

def test_link_dependencies_local():
    reg = MemberRegistry()
    caller = CSharpMethod(
        identifier="Caller",
        scoped_identifier="MyClass.Caller",
        return_type="void",
        umid="TestNamespace.MyClass#Caller()",
        signature="public void Caller()",
        body="Callee();",
        dependency_names=[("Callee()", "Callee")],
        start_line=1,
        parameters=[],
        registry=reg
    )
    callee = CSharpMethod(
        identifier="Callee",
        scoped_identifier="MyClass.Callee",
        return_type="void",
        umid="TestNamespace.MyClass#Callee()",
        signature="public void Callee()",
        body="{ }",
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
