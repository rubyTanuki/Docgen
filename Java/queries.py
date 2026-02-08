CLASS_QUERY = """
    (
        (class_declaration
            (modifiers)* @modifiers
            name: (identifier) @identifier
            body: (class_body
                (method_declaration)* @methods
                (field_declaration)* @fields
            ) @body
        )
    )
"""

PACKAGE_QUERY = """
(package_declaration
    (_) @package
)
(import_declaration
    (_) @imports
)
"""

METHOD_QUERY = """
    (
        (method_declaration
            (modifiers)* @modifiers
            type: [
                (void_type) @type
                (type_identifier) @type
            ] 
            name: (identifier) @identifier
            (formal_parameters
                (formal_parameter)* @parameters
            )
            body: (block) @body
        )
        
    )
"""

DEPENDENCY_QUERY = """
    (
        (method_invocation
            name: (identifier) @dependencies
        )
    )
"""

FIELD_QUERY = """
    (
        (field_declaration
            (modifiers)* @modifiers
            type: (_) @type
            (variable_declarator
                name: (identifier) @identifier
            )
        )
        
    )
"""