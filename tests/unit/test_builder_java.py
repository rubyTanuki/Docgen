import pytest
from toaster.core.registry import MemberRegistry
from toaster.languages.java.builder import JavaBuilder

def test_parse_field():
    builder = JavaBuilder(MemberRegistry())
    source = b"class Test { private int counter = 0; }"
    file_obj = builder.parse_source("Test.java", source)
    
    assert len(file_obj.classes) == 1
    test_class = file_obj.classes[0]
    
    assert len(test_class.fields) == 1
    field_obj = list(test_class.fields.values())[0]
    
    assert field_obj.name == "counter"
    assert field_obj.field_type == "int"
    assert "private" in field_obj.signature

def test_parse_method():
    builder = JavaBuilder(MemberRegistry())
    source = b"class Test { public void doSomething(String a) {} }"
    file_obj = builder.parse_source("Test.java", source)
    
    test_class = file_obj.classes[0]
    assert len(test_class.methods) == 1
    method_obj = list(test_class.methods.values())[0]
    
    assert method_obj.identifier == "doSomething"
    assert method_obj.return_type == "void"
    assert method_obj.arity == 1
    assert method_obj.parameters == ["String a"]
    assert method_obj.file == file_obj
    assert method_obj.parent_class == test_class

def test_context_plumbing():
    builder = JavaBuilder(MemberRegistry())
    source = b"class Parent { class Child { void ping() {} } }"
    file_obj = builder.parse_source("Test.java", source)
    
    parent_class = file_obj.classes[0]
    child_class = list(parent_class.child_classes.values())[0]
    method_obj = list(child_class.methods.values())[0]
    
    assert method_obj.file == file_obj
    assert method_obj.parent_class == child_class
