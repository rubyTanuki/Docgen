import pytest
import os
from toaster.core.registry import MemberRegistry
from toaster.languages.java.parser import JavaParser

def test_full_file_parse():
    test_filepath = os.path.join(
        os.path.dirname(__file__), 
        "../test_code/MRILib/A_TeleOp.java"
    )
    
    with open(test_filepath, 'rb') as f:
        code = f.read()

    parser = JavaParser(project_dir=".", registry=MemberRegistry())
    file_obj = parser.parse_file("A_TeleOp.java", code)
    
    assert file_obj is not None
    assert file_obj.ufid == "A_TeleOp.java"
    assert len(file_obj.classes) > 0
    assert len(file_obj.classes[0].methods) > 0
