import tree_sitter_c_sharp
from tree_sitter import Language, Parser, Query

CSHARP_LANGUAGE = Language(tree_sitter_c_sharp.language())
parser = Parser()
parser.language = CSHARP_LANGUAGE

source = b"""
class A {
    void Test() {
        var a = Task.WhenAll(t1, t2);
        b.ToList();
        Take(5);
        foo.Bar<int>();
    }
}
"""

tree = parser.parse(source)

query = Query(CSHARP_LANGUAGE, """
(invocation_expression
    function: [
        (member_access_expression name: (identifier) @name)
        (identifier) @name
        (generic_name (identifier) @name)
        (member_access_expression name: (generic_name (identifier) @name))
    ]
) @dependencies
""")

for match in query.matches(tree.root_node):
    # What does each capture give?
    for node, capture_name in match[1]:
        print(f"Capture: {capture_name}, text: {node.text.decode('utf-8')}, type: {node.type}")
