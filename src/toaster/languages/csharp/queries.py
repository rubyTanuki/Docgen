DEPENDENCY_QUERY = """
(invocation_expression
    function: [
        (member_access_expression name: (identifier) @name)
        (identifier) @name
        (generic_name (identifier) @name)
        (member_access_expression name: (generic_name (identifier) @name))
    ]
) @dependencies
"""
