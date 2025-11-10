#!/usr/bin/env python3
"""
Interactive rope extract method/variable script.

Usage:
    python rope_extract.py <project_path> <file_path> <start_offset> <end_offset> <name> [--type method|variable] [--similar]

Example:
    python rope_extract.py . mymodule.py 100 250 extracted_method --type method --similar
"""

import sys
import os
import argparse
from rope.base.project import Project
from rope.base import libutils
from rope.refactor.extract import ExtractMethod, ExtractVariable


def main():
    parser = argparse.ArgumentParser(description='Extract method or variable using rope')
    parser.add_argument('project_path', help='Path to the project root')
    parser.add_argument('file_path', help='Path to the file (relative to project)')
    parser.add_argument('start', type=int, help='Start offset of code to extract')
    parser.add_argument('end', type=int, help='End offset of code to extract')
    parser.add_argument('name', help='Name for the extracted method/variable')
    parser.add_argument('--type', choices=['method', 'variable'], default='method',
                        help='Type of extraction (default: method)')
    parser.add_argument('--similar', action='store_true',
                        help='Extract similar code blocks too')
    parser.add_argument('--global', dest='global_', action='store_true',
                        help='Extract as global function/variable instead of method/local')
    parser.add_argument('--preview-only', action='store_true',
                        help='Only preview changes, do not apply')

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

        # Show what will be extracted
        source = resource.read()
        if args.start >= len(source) or args.end > len(source) or args.start >= args.end:
            print(f"Error: Invalid offsets. File length: {len(source)}, start: {args.start}, end: {args.end}")
            return 1

        extracted_code = source[args.start:args.end]
        print(f"\nCode to extract ({args.end - args.start} characters):")
        print("-" * 70)
        print(extracted_code)
        print("-" * 70)

        # Create extractor
        if args.type == 'method':
            print(f"\nExtracting method: {args.name}")
            extractor = ExtractMethod(project, resource, args.start, args.end)
            changes = extractor.get_changes(args.name, similar=args.similar, global_=args.global_)
        else:
            print(f"\nExtracting variable: {args.name}")
            extractor = ExtractVariable(project, resource, args.start, args.end)
            changes = extractor.get_changes(args.name, similar=args.similar, global_=args.global_)

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
