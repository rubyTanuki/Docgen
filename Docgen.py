import tree_sitter_python as tspython
import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

parser = Parser()

JAVA_LANGUAGE = Language(tsjava.language())
parser.language = JAVA_LANGUAGE

java_code = b"""
class Test { 
    void run() { System.out.println("Hello"); } 
}
"""
tree = parser.parse(java_code)
