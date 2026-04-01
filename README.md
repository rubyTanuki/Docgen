<p align="center">
    <a href="https://toastedtools.com/"><img src="./logo.png" alt="Toaster Logo" width="816"></a>
</p>

<h1 align="center">
Pre-compiling Agentic AI Code Context
</h1>

<!-- usage gif goes here -->

<p align="center">
Toaster is a CLI and MCP agent context engine which greatly reduces token costs and context bloat for agentic LLM coding assistants by pre-computing an llm-described AST in the .toast format
</p>

## Features
### Pre-compiled Abstract Syntax Tree
Toaster scrapes your project on initialization, building a comprehensive Abstract Syntax Tree IR (Intermediate Representation) of the entire OOP code structure.

### Semantic Dependency Graph Resolution
Toaster resolves dependencies semantically, building a dependency graph to allow agents to traverse inbound or outbound method calls efficiently

### MCP and CLI access
Toaster has both a CLI and MCP interface, allowing llms to boot up the mcp server for larger development sessions, while allowing agents or human developers to utilize the CLI for individual actions or manual AST traversals

### Automatic Incremental Change Diffs
While the MCP server is running, Toaster identifies the subtree of the AST which was updated on file save, add, or delete, then re-scrapes and re-describes exactly the section that was updated, ensuring that the AST is up-to-date during development

### Lightweight SQLite Cache
The AST IR and Dependency Graph is cached to an on-drive SQLite .db file to vastly increase efficiency of agent AST traversal requests, as well as allow the AST to be pushed to version control for saving tokens in shared development.

# Quick Start
<!-- downnload and install TBD -->

## Initializing toaster
Before being able to use toaster, the repository must be initialized using the CLI or MCP.

To manually initialize the repository, cd to the root of the project and run:
```
% toaster init . --ignore 'default'
```
This creates the .toaster directory and initializes the default *.toastignore* to exclude environment files, node_modules, build artifacts, and other files which are not needed in the project AST

In the */.toaster* directory, you will also find the *config.toml* file to configure the other adjustable parameters (The full list of configuration parameters can be found ***Here***)

## Parsing the project
Once the project itself is initialized and configured, the AST cache has to be initialized. To do this manually, cd to the project root (where you initialized the .toaster files) and run:
```
% toaster parse .
```
This will take anywhere from a few seconds to a few minutes depending on the size of your repository, as the CLI parses the repository using tree-sitter, then passes the AST concurrently to your configured LLM provider for describing and embedding. Projects with particularly large individual classes will take longer to parse, since the description generation is blocked by class.
> The time it takes to parse during this step is one time per project, as the incremental diffing allows further parses to only update the cache invalidations

## Using the CLI
Now that the project is initialized and parsed, Toaster is ready to go!


### Project Skeleton
To test it, navigate to the project root and run:
```
% toaster skeleton . --depth 1
```
You should see Toaster print the AST skeleton of your root and its direct children directories to your console. 
> The 'depth' parameter can be adjusted to determine how many layers into the file tree should be skeletonized and printed (default is infinite, or the whole subtree of the path provided)

```
% toaster skeleton . --depth 1

/src/project/foo.py
    C-1234 | class Foo(Bar)
    //  Description of the Foo class, outlining usage and purpose
        rather than syntax

/src/project/child_dir/fizz.py
    C-1235 | class Fizz
    //  Description of the Fizz class...
    C-1236 | class Buzz(Fizz)
    //  Description of the Buzz class...

```

### Inspecting Structs

Each of the structs (files, classes, methods) can be inspected further to see more details about them:

```
% toaster inspect 'C-1234' --pretty

/src/project/foo.py
C-1234 | class Foo(Bar)
// Description of the Foo class, outlining usage and purpose
   rather than syntax
fields: 
        int num1, num2; Fizz field3; Buzz field4, field5
methods:
        M-12345 @L10-12 | def async foobar(num1: int = 0) -> int
        // Description of the foobar method...
        <  child.Fizz#outbound_dependency1(), ~M-12346|#foo(num: int), 
           ~M-12347|#bar(num:int)

        M-12346 @L22-24 | def foo(num: int) -> int
        // Description of the foo method...

        M-12347 @L27-30 | def bar(num: int) -> int
        // Description of the bar method...
```

You can also use flags to expand the detail of the output:
* `-v` / `--verbose`: Increases the verbosity of inspect commands to include more information, such as inbound dependencies (`>`) and impact scores.
* `-b` / `--body`: Attaches the body source code of the root struct being inspected to the bottom of the output.
*  `-r` / `--raw`: Disables pretty printing, or the indentation and line-wrapping configured in `.toaster/config.toml`. Pretty printing is active by default for CLI commands but inactive for MCP commands.

```
% toaster inspect 'M-12345' -v -b
/src/project/foo.py
C-1234 | Project.Foo
M-12345 @L10-20 | def async foobar(num1: int = 0) -> int
// Description of the foobar method non-truncated
<  child.Fizz#outbound_dependency1(), ~M-12346|#foo(num: int), 
   ~M-12347|#bar(num:int)
>  child.Fizz#inbound_dependency1(num1: int)
# impact score: 5

'''
self.field3.inbound_dependency1(num1)
return num1 + self.foo(num1) + self.bar(num1)
'''
```
