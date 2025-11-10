#!/usr/bin/env python3
"""
Get information about a symbol in a Python file using rope.

Usage:
    python rope_info.py <project_path> <file_path> <symbol_name>

Example:
    python rope_info.py . mymodule.py MyClass
"""

import sys
import argparse
from rope.base.project import Project
from rope.base import libutils
from rope.contrib import codeassist


def main():
    parser = argparse.ArgumentParser(description='Get information about a Python symbol using rope')
    parser.add_argument('project_path', help='Path to the project root')
    parser.add_argument('file_path', help='Path to the file (relative to project)')
    parser.add_argument('symbol', help='Symbol name to inspect')

    args = parser.parse_args()

    project = None
    try:
        # Create project
        project = Project(args.project_path)

        # Validate project
        print("Validating project...")
        project.validate(project.root)

        # Get resource (use absolute path or project.root for relative paths)
        import os
        if os.path.isabs(args.file_path):
            resource = libutils.path_to_resource(project, args.file_path)
        else:
            resource = project.root.get_child(args.file_path)

        if not resource.exists():
            print(f"Error: File '{args.file_path}' does not exist")
            return 1

        # Read file and find offset
        source = resource.read()
        offset = source.find(args.symbol)

        if offset == -1:
            print(f"Error: Could not find '{args.symbol}' in {args.file_path}")
            return 1

        print(f"Symbol: {args.symbol}")
        print(f"Found at offset: {offset}")

        # Try to get documentation
        try:
            doc = codeassist.get_doc(project, source, offset, resource)
            if doc:
                print(f"\nDocumentation:")
                print("-" * 70)
                print(doc)
                print("-" * 70)
        except Exception as e:
            print(f"Could not retrieve documentation: {e}")

        # Try to get definition location
        try:
            location = codeassist.get_definition_location(project, source, offset, resource)
            if location:
                loc_resource, loc_offset = location
                print(f"\nDefined in: {loc_resource.path}")
                print(f"At offset: {loc_offset}")

                # Show context around definition
                if loc_resource.exists():
                    loc_source = loc_resource.read()
                    # Show 3 lines of context
                    lines = loc_source[:loc_offset + 200].split('\n')
                    start_line = max(0, len(lines) - 6)
                    print("\nDefinition context:")
                    print("-" * 70)
                    for i, line in enumerate(lines[start_line:], start=start_line + 1):
                        marker = ">>>" if i == len(lines) else "   "
                        print(f"{marker} {line}")
                    print("-" * 70)
        except Exception as e:
            print(f"Could not retrieve definition location: {e}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    finally:
        if project:
            project.close()


if __name__ == '__main__':
    sys.exit(main())
