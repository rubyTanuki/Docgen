import pytest
from toaster.core.registry import MemberRegistry
from toaster.languages.csharp.builder import CSharpBuilder

def test_parse_field():
    builder = CSharpBuilder(MemberRegistry())
    source = b"class Test { private int counter = 0; }"
    file_obj = builder.parse_source("Test.cs", source)
    
    assert len(file_obj.classes) == 1
    test_class = file_obj.classes[0]
    
    assert len(test_class.fields) == 1
    field_obj = list(test_class.fields.values())[0]
    
    assert field_obj.name == "counter"
    assert field_obj.field_type == "int"
    assert "private" in field_obj.signature

def test_parse_method():
    builder = CSharpBuilder(MemberRegistry())
    source = b"class Test { public void DoSomething(string a) {} }"
    file_obj = builder.parse_source("Test.cs", source)
    
    test_class = file_obj.classes[0]
    assert len(test_class.methods) == 1
    method_obj = list(test_class.methods.values())[0]
    
    assert method_obj.identifier == "DoSomething"
    assert method_obj.return_type == "void"
    assert method_obj.arity == 1
    assert method_obj.parameters == ["string a"]
    assert method_obj.file == file_obj
    assert method_obj.parent_class == test_class

def test_context_plumbing():
    builder = CSharpBuilder(MemberRegistry())
    source = b"class Parent { class Child { void Ping() { Pong.Ding(); } } }"
    file_obj = builder.parse_source("Test.cs", source)
    
    parent_class = file_obj.classes[0]
    child_class = list(parent_class.child_classes.values())[0]
    method_obj = list(child_class.methods.values())[0]
    
    assert method_obj.file == file_obj
    assert method_obj.parent_class == child_class
    
    assert len(method_obj.dependency_names) == 1
    assert method_obj.dependency_names[0] == ("Pong.Ding()", "Ding")
