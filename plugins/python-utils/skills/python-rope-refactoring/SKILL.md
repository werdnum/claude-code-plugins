---
name: python-rope-refactoring
description: This skill should be used when performing Python refactoring operations using the rope library. It provides comprehensive guidance on using rope programmatically for safe, automated refactorings including rename, extract method/variable, move, inline, restructure, and more.
---

# Python Rope Refactoring

This skill provides comprehensive guidance on using the rope library for advanced Python refactoring operations.

## About Rope

Rope is the world's most advanced open source Python refactoring library. It provides:

- **Powerful and safe refactorings**: Rename, extract, inline, move, restructure, and more
- **Static Object Analysis (SOA)**: Sophisticated type inference for accurate refactorings
- **Cross-project refactorings**: Refactor across multiple related projects
- **IDE helpers**: Auto-completion, find occurrences, definition location
- **VCS integration**: Git, Mercurial, SVN support

Rope is pure Python with no dependencies, making it ideal for programmatic refactoring.

## When to Use This Skill

Use this skill when:
- Performing systematic refactorings across a Python codebase
- Renaming variables, functions, classes, or modules safely
- Extracting methods or variables from complex functions
- Moving code between modules or packages
- Inlining functions or variables
- Restructuring code patterns programmatically
- Need automated, safe refactoring that updates all references

## Installation

Install rope using pip:

```bash
pip install rope
```

## Core Concepts

### Project

A rope `Project` represents a Python codebase in a directory. All refactorings operate within a project context:

```python
from rope.base.project import Project

# Create a project for the current directory
project = Project('.')

# Or specify a path
project = Project('/path/to/myproject')

# Always close when done
project.close()
```

**Key points about projects:**
- A project is a directory that can contain any files
- Rope searches for Python modules/packages inside the project
- Refactorings only change files inside the project
- External modules are analyzed but never modified
- Rope creates a `.ropeproject` folder for configuration and caching (can be disabled with `ropefolder=None`)

### Resources

Files and folders in rope are accessed through `Resource` objects (`File` and `Folder`):

```python
from rope.base import libutils

# Get a resource for an existing file
resource = libutils.path_to_resource(project, '/path/to/file.py')

# Create a resource for a file that doesn't exist yet
new_file = libutils.path_to_resource(project, '/path/to/new_file.py', type='file')
```

### Changes

Refactorings return `Change` objects that describe the modifications:

```python
# Get changes from a refactoring
changes = refactoring.get_changes('new_name')

# Preview changes
print(changes.get_description())

# Apply changes
project.do(changes)

# Undo if needed
project.history.undo()
```

## Refactoring Operations

### Rename

Rename variables, functions, classes, modules - rope updates all references:

```python
from rope.refactor.rename import Rename

# Get the resource
resource = libutils.path_to_resource(project, 'mymodule.py')

# Create renamer at offset (character position in file)
renamer = Rename(project, resource, offset)

# Get changes with new name
changes = renamer.get_changes('new_name')

# Option: rename in docs/comments too
changes = renamer.get_changes('new_name', docs=True)

# Apply
project.do(changes)
```

**Calculating offsets**: Offsets are character positions in the file (0-indexed). DOS line-endings and multi-byte characters count as one character. To find the offset of a name, read the file and use `source.find('name')` or calculate from line/column positions.

### Extract Method

Extract selected code into a new method:

```python
from rope.refactor.extract import ExtractMethod

resource = libutils.path_to_resource(project, 'mymodule.py')

# start and end are character offsets of the region to extract
extractor = ExtractMethod(project, resource, start, end)

# Extract to a method named 'extracted_method'
changes = extractor.get_changes('extracted_method')
project.do(changes)
```

**Options:**
- `global_`: Extract as a global function instead of method
- `similar`: Extract similar code blocks too

### Extract Variable

Extract an expression into a variable:

```python
from rope.refactor.extract import ExtractVariable

resource = libutils.path_to_resource(project, 'mymodule.py')
extractor = ExtractVariable(project, resource, start, end)

changes = extractor.get_changes('extracted_var')
project.do(changes)
```

**Options:**
- `similar`: Extract similar expressions too
- `global_`: Extract as a global variable

### Inline

Inline a method, variable, or parameter (replace uses with the actual value):

```python
from rope.refactor.inline import (
    InlineMethod,
    InlineVariable,
    InlineParameter
)

resource = libutils.path_to_resource(project, 'mymodule.py')

# Inline method
inliner = InlineMethod(project, resource, offset)
changes = inliner.get_changes()
project.do(changes)

# Inline variable
inliner = InlineVariable(project, resource, offset)
changes = inliner.get_changes()
project.do(changes)
```

**Options:**
- `only_current`: Only inline the current occurrence
- `remove`: Remove the definition after inlining

### Move

Move classes, functions, modules, or methods:

```python
from rope.refactor.move import create_move

resource = libutils.path_to_resource(project, 'mymodule.py')

# create_move auto-detects what to move based on offset
mover = create_move(project, resource, offset)

# Move to destination resource (module or package)
dest_resource = libutils.path_to_resource(project, 'newmodule.py')
changes = mover.get_changes(dest_resource)
project.do(changes)
```

### Change Signature

Modify function/method signatures (add, remove, reorder parameters):

```python
from rope.refactor.change_signature import ChangeSignature

resource = libutils.path_to_resource(project, 'mymodule.py')
changer = ChangeSignature(project, resource, offset)

# Get current signature info
signature = changer.get_signature()

# Modify signature - add parameter, remove parameter, reorder, etc.
# See rope documentation for ArgumentReordering and ArgumentAdder
changes = changer.get_changes(new_signature)
project.do(changes)
```

### Restructure

Pattern-based code transformation - the most powerful refactoring:

```python
from rope.refactor.restructure import Restructure

# Pattern: what to match (uses ${} for wildcards)
pattern = '${pow_func}(${param1}, ${param2})'

# Goal: what to replace it with
goal = '${param1} ** ${param2}'

# Args: constraints on wildcards
args = {'pow_func': 'name=mymodule.pow'}

restructuring = Restructure(project, pattern, goal, args)
changes = restructuring.get_changes()
project.do(changes)
```

**Pattern syntax:**
- `${name}` - wildcard matching any expression
- Constraints: `name=module.func`, `type=mymodule.MyClass`, etc.

**Common use cases:**
- Convert function calls to operators
- Modernize old API calls
- Apply design pattern transformations

### Other Refactorings

```python
# Introduce factory
from rope.refactor.introduce_factory import IntroduceFactory

# Encapsulate field (add getter/setter)
from rope.refactor.encapsulate_field import EncapsulateField

# Method to method object
from rope.refactor.method_object import MethodObject

# Local variable to field
from rope.refactor.localtofield import LocalToField

# Module to package
from rope.refactor.topackage import ModuleToPackage

# Organize imports
from rope.refactor.importutils import ImportOrganizer
```

## Best Practices

### 1. Always Validate Before Refactoring

When files change outside rope, validate to clear caches:

```python
# Validate the entire project
project.validate(project.root)

# Or validate a specific resource
project.validate(resource)
```

Call this before each refactoring operation when using rope in an IDE or when files may have changed externally.

### 2. Use Static Object Analysis for Better Results

Run SOA to improve rope's type inference:

```python
from rope.base import libutils

# Analyze a single module
libutils.analyze_module(project, resource)

# Analyze all modules (can be slow on large projects)
libutils.analyze_modules(project)
```

Run this periodically, especially before large refactorings. SOA analyzes function calls and assignments to infer types.

### 3. Preview Before Applying

Always preview changes before applying:

```python
changes = refactoring.get_changes('new_name')

# Get description
print(changes.get_description())

# Or inspect the Change object directly for detailed info
for change_set in changes.changes:
    print(change_set.get_description())

# Apply only if satisfied
project.do(changes)
```

### 4. Handle Task Progress

For long-running refactorings, use TaskHandle to monitor progress and allow cancellation:

```python
from rope.base.taskhandle import TaskHandle

handle = TaskHandle("Rename refactoring")

def update_progress():
    jobset = handle.current_jobset()
    if jobset:
        percent = jobset.get_percent_done()
        print(f"Progress: {percent}%")

handle.add_observer(update_progress)

# Pass as keyword argument
changes = renamer.get_changes('new_name', task_handle=handle)
```

### 5. Close Projects

Always close projects to flush caches and save state:

```python
try:
    project = Project('.')
    # ... perform refactorings ...
finally:
    project.close()
```

### 6. Use Context Managers

Create a context manager for automatic cleanup:

```python
from contextlib import contextmanager

@contextmanager
def rope_project(path):
    project = Project(path)
    try:
        yield project
    finally:
        project.close()

# Usage
with rope_project('.') as project:
    # ... perform refactorings ...
```

## Common Workflows

### Workflow: Safe Rename Across Project

```python
from rope.base.project import Project
from rope.base import libutils
from rope.refactor.rename import Rename

with rope_project('.') as project:
    # Validate first
    project.validate(project.root)

    # Find the target
    resource = libutils.path_to_resource(project, 'mymodule.py')

    # Read file to find offset
    source = resource.read()
    offset = source.find('old_name')

    # Create renamer
    renamer = Rename(project, resource, offset)

    # Preview
    changes = renamer.get_changes('new_name', docs=True)
    print(changes.get_description())

    # Confirm and apply
    response = input("Apply changes? (y/n): ")
    if response.lower() == 'y':
        project.do(changes)
        print("Refactoring complete!")
```

### Workflow: Extract Method for Code Cleanup

```python
from rope.refactor.extract import ExtractMethod

with rope_project('.') as project:
    resource = libutils.path_to_resource(project, 'messy_module.py')

    # Calculate offsets for the code block to extract
    source = resource.read()
    # Find start/end positions...
    start = source.find('# START EXTRACTION')
    end = source.find('# END EXTRACTION')

    extractor = ExtractMethod(project, resource, start, end)
    changes = extractor.get_changes('extracted_logic', similar=True)

    project.do(changes)
```

### Workflow: Batch Restructure

```python
from rope.refactor.restructure import Restructure

# Convert all old-style format strings to f-strings
pattern = '"${text}" % ${args}'
goal = 'f"${text}"'  # Note: simplified, real implementation is more complex

with rope_project('.') as project:
    restructuring = Restructure(project, pattern, goal, {})
    changes = restructuring.get_changes()

    if changes:
        print(changes.get_description())
        project.do(changes)
```

## Using Helper Scripts

This skill includes helper scripts for common rope operations:

### scripts/rope_rename.py

Interactive rename script:

```bash
python scripts/rope_rename.py /path/to/project file.py old_name new_name
```

### scripts/rope_extract.py

Extract method/variable interactively:

```bash
python scripts/rope_extract.py /path/to/project file.py start_line end_line extracted_name
```

See the scripts directory for more utilities.

## Troubleshooting

### Import Errors

If rope can't find imports:
- Ensure the project root is correct
- Check `.ropeproject/config.py` for `python_path` settings
- Validate project before refactoring

### Incorrect Refactorings

If rope makes wrong changes:
- Run SOA to improve type inference
- Check that offsets are calculated correctly (DOS line endings!)
- Use preview to inspect changes before applying
- Consider limiting scope with `resources` parameter

### Performance Issues

For large projects:
- Use `resources` parameter to limit refactoring scope
- Run SOA periodically, not on every refactoring
- Consider using `.ropeproject` caching
- Use TaskHandle to monitor and cancel long operations

## References

For detailed information, refer to:
- Rope documentation: https://rope.readthedocs.io/
- Library usage: https://rope.readthedocs.io/en/latest/library.html
- Rope repository: https://github.com/python-rope/rope

See `references/rope_library_docs.md` for the complete rope library documentation (included in this skill for offline reference).
