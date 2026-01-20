#!/usr/bin/env python3
"""
SPS Agent Module Help System

Linux man-style documentation viewer for all Python modules in .agent/

Usage:
    python .agent/scripts/help.py                     # List all modules
    python .agent/scripts/help.py content_brain       # Full man page for module
    python .agent/scripts/help.py --search "fact"     # Search across all docs
    python .agent/scripts/help.py module --plain      # No colors
"""

import argparse
import ast
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class FunctionDoc:
    """Documentation for a single function."""
    name: str
    signature: str
    docstring: str
    is_method: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False


@dataclass
class ClassDoc:
    """Documentation for a class."""
    name: str
    docstring: str
    methods: List[FunctionDoc] = field(default_factory=list)
    bases: List[str] = field(default_factory=list)


@dataclass
class ModuleDoc:
    """Documentation for a module."""
    name: str
    qualified_name: str
    filepath: Path
    docstring: str
    brief: str
    classes: List[ClassDoc] = field(default_factory=list)
    functions: List[FunctionDoc] = field(default_factory=list)


# ============================================================================
# DOC EXTRACTOR - AST-based extraction without importing modules
# ============================================================================

class DocExtractor:
    """Extract documentation from Python files using AST parsing."""

    def extract(self, filepath: Path) -> Optional[ModuleDoc]:
        """Parse a Python file and extract all documentation."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError) as e:
            return None

        # Module-level docstring
        docstring = ast.get_docstring(tree) or ""
        brief = self._get_brief(docstring)

        # Determine qualified name from path
        name = filepath.stem
        qualified_name = self._get_qualified_name(filepath)

        module_doc = ModuleDoc(
            name=name,
            qualified_name=qualified_name,
            filepath=filepath,
            docstring=docstring,
            brief=brief
        )

        # Extract classes and functions
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_doc = self._extract_class(node)
                module_doc.classes.append(class_doc)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                if not node.name.startswith('_'):
                    func_doc = self._extract_function(node)
                    module_doc.functions.append(func_doc)

        return module_doc

    def _get_brief(self, docstring: str) -> str:
        """Extract first sentence from docstring."""
        if not docstring:
            return "(No documentation)"
        # Get first line or sentence
        lines = docstring.strip().split('\n')
        first = lines[0].strip()
        # Remove any emoji at start
        first = re.sub(r'^[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF]+\s*', '', first)
        # Truncate at first period if present
        if '.' in first:
            first = first.split('.')[0] + '.'
        return first[:80] if len(first) > 80 else first

    def _get_qualified_name(self, filepath: Path) -> str:
        """Get the import path for a module."""
        parts = filepath.parts
        # Find .agent directory and build path from there
        try:
            agent_idx = parts.index('.agent')
            relevant = parts[agent_idx + 1:-1]  # Skip .agent and filename
            module = filepath.stem
            if relevant:
                return '.'.join(relevant) + '.' + module
            return module
        except ValueError:
            return filepath.stem

    def _extract_class(self, node: ast.ClassDef) -> ClassDoc:
        """Extract documentation from a class definition."""
        docstring = ast.get_docstring(node) or ""
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(base.attr)

        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not item.name.startswith('_') or item.name in ('__init__', '__call__'):
                    func_doc = self._extract_function(item, is_method=True)
                    methods.append(func_doc)

        return ClassDoc(
            name=node.name,
            docstring=docstring,
            methods=methods,
            bases=bases
        )

    def _extract_function(self, node, is_method: bool = False) -> FunctionDoc:
        """Extract documentation from a function definition."""
        docstring = ast.get_docstring(node) or ""
        signature = self._build_signature(node)

        is_classmethod = False
        is_staticmethod = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id == 'classmethod':
                    is_classmethod = True
                elif decorator.id == 'staticmethod':
                    is_staticmethod = True

        return FunctionDoc(
            name=node.name,
            signature=signature,
            docstring=docstring,
            is_method=is_method,
            is_classmethod=is_classmethod,
            is_staticmethod=is_staticmethod
        )

    def _build_signature(self, node) -> str:
        """Build a function signature string."""
        args = []
        defaults_offset = len(node.args.args) - len(node.args.defaults)

        for i, arg in enumerate(node.args.args):
            arg_str = arg.arg
            # Add type annotation if present
            if arg.annotation:
                arg_str += ': ' + self._annotation_to_str(arg.annotation)
            # Add default value
            default_idx = i - defaults_offset
            if default_idx >= 0 and default_idx < len(node.args.defaults):
                arg_str += '=...'
            args.append(arg_str)

        # Handle *args
        if node.args.vararg:
            args.append(f'*{node.args.vararg.arg}')
        # Handle **kwargs
        if node.args.kwarg:
            args.append(f'**{node.args.kwarg.arg}')

        sig = f"{node.name}({', '.join(args)})"

        # Add return type
        if node.returns:
            sig += ' -> ' + self._annotation_to_str(node.returns)

        return sig

    def _annotation_to_str(self, annotation) -> str:
        """Convert an annotation AST node to string."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return repr(annotation.value)
        elif isinstance(annotation, ast.Subscript):
            base = self._annotation_to_str(annotation.value)
            if isinstance(annotation.slice, ast.Tuple):
                elts = ', '.join(self._annotation_to_str(e) for e in annotation.slice.elts)
                return f"{base}[{elts}]"
            return f"{base}[{self._annotation_to_str(annotation.slice)}]"
        elif isinstance(annotation, ast.Attribute):
            return annotation.attr
        return "Any"


# ============================================================================
# MODULE REGISTRY - Auto-discovery of all modules
# ============================================================================

class ModuleRegistry:
    """Discover and index all Python modules in .agent/"""

    SCAN_DIRS = ['skills', 'lib', 'shared', 'config', 'scripts']
    EXCLUDE_DIRS = {'__pycache__', 'tests', 'test', '.pytest_cache'}
    EXCLUDE_FILES = {'__init__.py', 'conftest.py'}

    def __init__(self, agent_dir: Path):
        self.agent_dir = agent_dir
        self.extractor = DocExtractor()
        self._modules: Dict[str, ModuleDoc] = {}

    def scan(self) -> Dict[str, ModuleDoc]:
        """Scan all directories and build module index."""
        for scan_dir in self.SCAN_DIRS:
            dir_path = self.agent_dir / scan_dir
            if dir_path.exists():
                self._scan_directory(dir_path)
        return self._modules

    def _scan_directory(self, directory: Path):
        """Recursively scan a directory for Python files."""
        for item in directory.iterdir():
            if item.name in self.EXCLUDE_DIRS or item.name.startswith('.'):
                continue

            if item.is_dir():
                self._scan_directory(item)
            elif item.is_file() and item.suffix == '.py':
                if item.name not in self.EXCLUDE_FILES:
                    module_doc = self.extractor.extract(item)
                    if module_doc:
                        self._modules[module_doc.name] = module_doc

    def get(self, name: str) -> Optional[ModuleDoc]:
        """Get a module by name."""
        return self._modules.get(name)

    def search(self, query: str) -> List[ModuleDoc]:
        """Search modules by text in docstrings."""
        results = []
        query_lower = query.lower()
        for module in self._modules.values():
            searchable = (
                module.docstring.lower() +
                ' '.join(c.docstring.lower() for c in module.classes) +
                ' '.join(f.docstring.lower() for f in module.functions)
            )
            if query_lower in searchable:
                results.append(module)
        return results

    def list_all(self) -> List[ModuleDoc]:
        """List all modules sorted by name."""
        return sorted(self._modules.values(), key=lambda m: m.name)


# ============================================================================
# MAN FORMATTER - Colored terminal output
# ============================================================================

class ManFormatter:
    """Format documentation in Linux man page style."""

    # ANSI color codes
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    CYAN = '\033[36m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RESET = '\033[0m'

    def __init__(self, use_color: bool = True):
        self.use_color = use_color

    def _bold(self, text: str) -> str:
        if self.use_color:
            return f"{self.BOLD}{text}{self.RESET}"
        return text

    def _section(self, text: str) -> str:
        if self.use_color:
            return f"{self.BOLD}{self.CYAN}{text}{self.RESET}"
        return text

    def _code(self, text: str) -> str:
        if self.use_color:
            return f"{self.GREEN}{text}{self.RESET}"
        return text

    def _emphasis(self, text: str) -> str:
        if self.use_color:
            return f"{self.YELLOW}{text}{self.RESET}"
        return text

    def format_module(self, module: ModuleDoc) -> str:
        """Format a full man page for a module."""
        lines = []
        name_upper = module.name.upper()
        header = f"{name_upper}(1)              SPS Agent Manual              {name_upper}(1)"
        lines.append(self._bold(header))
        lines.append('')

        # NAME section
        lines.append(self._section('NAME'))
        lines.append(f"       {module.name} - {module.brief}")
        lines.append('')

        # SYNOPSIS section
        lines.append(self._section('SYNOPSIS'))
        lines.append(f"       {self._code(f'from {module.qualified_name} import ...')}")
        lines.append('')

        # DESCRIPTION section
        lines.append(self._section('DESCRIPTION'))
        if module.docstring:
            for line in module.docstring.split('\n'):
                lines.append(f"       {line}")
        else:
            lines.append("       (No documentation)")
        lines.append('')

        # CLASSES section
        if module.classes:
            lines.append(self._section('CLASSES'))
            for cls in module.classes:
                bases_str = f"({', '.join(cls.bases)})" if cls.bases else ""
                lines.append(f"       {self._bold(cls.name)}{bases_str}")
                if cls.docstring:
                    brief = cls.docstring.split('\n')[0]
                    lines.append(f"           {brief}")
                lines.append('')

                if cls.methods:
                    lines.append(f"           {self._emphasis('Methods:')}")
                    for method in cls.methods[:10]:  # Limit to first 10 methods
                        lines.append(f"               {self._code(method.signature)}")
                        if method.docstring:
                            brief = method.docstring.split('\n')[0][:60]
                            lines.append(f"                   {brief}")
                    if len(cls.methods) > 10:
                        lines.append(f"               ... and {len(cls.methods) - 10} more methods")
                lines.append('')

        # FUNCTIONS section
        if module.functions:
            lines.append(self._section('FUNCTIONS'))
            for func in module.functions[:15]:  # Limit to first 15 functions
                lines.append(f"       {self._code(func.signature)}")
                if func.docstring:
                    brief = func.docstring.split('\n')[0][:60]
                    lines.append(f"           {brief}")
                lines.append('')

        # FILES section
        lines.append(self._section('FILES'))
        lines.append(f"       {module.filepath}")
        lines.append('')

        return '\n'.join(lines)

    def format_list(self, modules: List[ModuleDoc]) -> str:
        """Format a list of modules with brief descriptions."""
        lines = []
        lines.append(self._bold("SPS AGENT MODULES"))
        lines.append(f"{'=' * 60}")
        lines.append('')

        # Group by directory
        by_dir: Dict[str, List[ModuleDoc]] = {}
        for module in modules:
            parts = module.qualified_name.split('.')
            dir_name = parts[0] if len(parts) > 1 else 'root'
            if dir_name not in by_dir:
                by_dir[dir_name] = []
            by_dir[dir_name].append(module)

        for dir_name in sorted(by_dir.keys()):
            lines.append(self._section(dir_name.upper() + '/'))
            for module in sorted(by_dir[dir_name], key=lambda m: m.name):
                name_col = f"  {module.name:<25}"
                lines.append(f"{self._code(name_col)} {module.brief}")
            lines.append('')

        lines.append(f"Total: {len(modules)} modules")
        lines.append('')
        lines.append("Use 'python .agent/scripts/help.py <module>' for full documentation")

        return '\n'.join(lines)

    def format_search_results(self, query: str, results: List[ModuleDoc]) -> str:
        """Format search results."""
        lines = []
        lines.append(self._bold(f"Search results for '{query}'"))
        lines.append(f"{'=' * 60}")
        lines.append('')

        if not results:
            lines.append("No matches found.")
        else:
            for module in results:
                lines.append(f"  {self._code(module.name)}")
                lines.append(f"    {module.brief}")
                lines.append(f"    {self._emphasis(module.qualified_name)}")
                lines.append('')

            lines.append(f"Found {len(results)} matching module(s)")

        return '\n'.join(lines)


# ============================================================================
# PAGER SUPPORT
# ============================================================================

def output_with_pager(text: str, use_pager: bool = True):
    """Output text, optionally through a pager."""
    if not use_pager or not sys.stdout.isatty():
        print(text)
        return

    # Try to use less with color support
    try:
        pager = subprocess.Popen(
            ['less', '-R', '-S'],
            stdin=subprocess.PIPE,
            text=True
        )
        pager.communicate(input=text)
    except FileNotFoundError:
        # Fallback to more or just print
        try:
            pager = subprocess.Popen(
                ['more'],
                stdin=subprocess.PIPE,
                text=True
            )
            pager.communicate(input=text)
        except FileNotFoundError:
            print(text)


# ============================================================================
# MAIN CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="SPS Agent Module Documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python .agent/scripts/help.py                     List all modules
  python .agent/scripts/help.py content_brain       Show content_brain man page
  python .agent/scripts/help.py --search "fact"     Search for 'fact' in docs
  python .agent/scripts/help.py --list              List all modules (explicit)
"""
    )
    parser.add_argument(
        'module',
        nargs='?',
        help='Module name to display (e.g., content_brain)'
    )
    parser.add_argument(
        '--search', '-s',
        metavar='QUERY',
        help='Search for text across all module documentation'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all available modules'
    )
    parser.add_argument(
        '--plain', '-p',
        action='store_true',
        help='Plain text output (no colors)'
    )
    parser.add_argument(
        '--no-pager',
        action='store_true',
        help='Disable pager (less/more)'
    )

    args = parser.parse_args()

    # Find .agent directory
    script_dir = Path(__file__).parent
    agent_dir = script_dir.parent
    if not (agent_dir / 'skills').exists():
        print(f"Error: Cannot find .agent directory structure", file=sys.stderr)
        sys.exit(1)

    # Initialize registry and formatter
    registry = ModuleRegistry(agent_dir)
    registry.scan()
    formatter = ManFormatter(use_color=not args.plain)
    use_pager = not args.no_pager

    # Handle commands
    if args.search:
        results = registry.search(args.search)
        output = formatter.format_search_results(args.search, results)
        output_with_pager(output, use_pager)

    elif args.module:
        module = registry.get(args.module)
        if module:
            output = formatter.format_module(module)
            output_with_pager(output, use_pager)
        else:
            # Try partial match
            all_modules = registry.list_all()
            matches = [m for m in all_modules if args.module.lower() in m.name.lower()]
            if matches:
                print(f"Module '{args.module}' not found. Did you mean:")
                for m in matches[:5]:
                    print(f"  - {m.name}")
            else:
                print(f"Module '{args.module}' not found.", file=sys.stderr)
                print(f"Use --list to see all available modules.", file=sys.stderr)
            sys.exit(1)

    else:
        # Default: list all modules
        modules = registry.list_all()
        output = formatter.format_list(modules)
        output_with_pager(output, use_pager)


if __name__ == "__main__":
    main()
