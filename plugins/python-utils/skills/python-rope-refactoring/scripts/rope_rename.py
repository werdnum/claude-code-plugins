#!/usr/bin/env python3
"""
Interactive rope rename script.

Usage:
    python rope_rename.py <project_path> <file_path> <old_name> <new_name> [--docs]

Example:
    python rope_rename.py . mymodule.py old_function new_function --docs
"""

import sys
import os
import argparse
from pathlib import Path
from rope.base.project import Project
from rope.base import libutils
from rope.refactor.rename import Rename


def main():
    parser = argparse.ArgumentParser(description='Rename a Python symbol using rope')
    parser.add_argument('project_path', help='Path to the project root')
    parser.add_argument('file_path', help='Path to the file containing the symbol (relative to project)')
    parser.add_argument('old_name', help='Current name of the symbol')
    parser.add_argument('new_name', help='New name for the symbol')
    parser.add_argument('--docs', action='store_true', help='Also rename in docstrings and comments')
    parser.add_argument('--preview-only', action='store_true', help='Only preview changes, do not apply')

    args = parser.parse_args()

    project = None
    try:
        # Create project
        project = Project(args.project_path)

        # Validate project
        print("Validating project...")
        project.validate(project.root)

        # Get resource (use absolute path or project.root for relative paths)
        if os.path.isabs(args.file_path):
            resource = libutils.path_to_resource(project, args.file_path)
        else:
            resource = project.root.get_child(args.file_path)

        if not resource.exists():
            print(f"Error: File '{args.file_path}' does not exist")
            return 1

        # Read file and find offset
        source = resource.read()
        offset = source.find(args.old_name)

        if offset == -1:
            print(f"Error: Could not find '{args.old_name}' in {args.file_path}")
            print("Note: Searching for exact string match. Ensure the name is correct.")
            return 1

        print(f"Found '{args.old_name}' at offset {offset}")

        # Create renamer
        print(f"Creating rename refactoring: {args.old_name} -> {args.new_name}")
        renamer = Rename(project, resource, offset)

        # Get changes
        changes = renamer.get_changes(args.new_name, docs=args.docs)

        # Preview
        print("\n" + "=" * 70)
        print("PREVIEW OF CHANGES:")
        print("=" * 70)
        print(changes.get_description())
        print("=" * 70)

        if args.preview_only:
            print("\nPreview-only mode: no changes applied")
            return 0

        # Confirm
        response = input("\nApply these changes? (y/n): ")
        if response.lower() != 'y':
            print("Refactoring cancelled")
            return 0

        # Apply
        print("Applying changes...")
        project.do(changes)
        print("✓ Refactoring complete!")

        # Show changed files
        changed_resources = changes.get_changed_resources()
        if changed_resources:
            print(f"\nChanged {len(changed_resources)} file(s):")
            for res in changed_resources:
                print(f"  - {res.path}")

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
