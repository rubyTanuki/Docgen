import pytest
from toaster.core.registry import MemberRegistry
from toaster.languages.java.builder import JavaBuilder

def test_cross_file_linking():
    reg = MemberRegistry()
    builder = JavaBuilder(reg)
    
    # File A has a method
    file_a_src = b"""
    package com.test;
    public class FileA {
        public void foo() {}
    }
    """
    
    # File B calls that method
    file_b_src = b"""
    package com.test;
    public class FileB {
        public void caller() {
            foo();
        }
    }
    """
    
    file_a = builder.parse_source("FileA.java", file_a_src)
    file_b = builder.parse_source("FileB.java", file_b_src)
    
    # Resolving dependencies globally
    file_a.resolve_dependencies()
    file_b.resolve_dependencies()
    
    foo_method = file_a.classes[0].methods["com.test.FileA#foo()"]
    caller_method = file_b.classes[0].methods["com.test.FileB#caller()"]
    
    assert len(caller_method.dependencies) > 0
    assert "M-" in caller_method.dependencies[0]
    
    assert len(foo_method.inbound_dependencies) > 0
    assert "M-" in foo_method.inbound_dependencies[0]

