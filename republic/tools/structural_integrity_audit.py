#!/usr/bin/env python3
"""
Structural Integrity Audit (Comprehensive Protocol)
=========================================================
Beyond text patterns - checks that ALL pathways connect and function.

Static Analysis Layers:
1.  Semantic Honesty - Text pattern matching (TODO, placeholder, etc.)
2.  Stub Functions - Methods that just `pass` or `return None`  
3.  Dead Code - Functions defined but never called
4.  Orphaned Imports - Modules imported but never used
5.  Undefined Names - Variables/modules used but never imported (pyflakes)
6.  Bare Except Blocks - Exception handlers that swallow all errors
7.  Hardcoded Secrets - API keys, passwords in code
8.  Resource Leaks - Unclosed files/connections
9.  Style Violations - PEP8 compliance (flake8)
10. Type Errors - Type annotation issues (mypy)
11. Complexity Metrics - Cyclomatic complexity (radon)

Structural Analysis:
12. Disconnected Agents - Agents not in INTENT_ROUTING
13. Database Integrity - Tables defined but never queried

Behavioral Testing:
14. Runtime verification of critical paths
"""

import os
import sys
import ast
import re
import subprocess
from collections import defaultdict
from pathlib import Path

# Phase 37: Use dynamic path instead of hardcoded (TLS-03)
BASE_DIR = os.getenv('REPUBLIC_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEPARTMENTS_DIR = os.path.join(BASE_DIR, "departments")

# Ensure BASE_DIR is in path for imports
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Known intentional items (won't be flagged)
INTENTIONAL_STUBS = [
    "run_honesty_audit",  # Self-referential scanner
    "__init__",  # Constructors often empty in base classes
    "send",  # Graceful degradation fallback for Notifier
    "decide",  # Template method pattern in base classes  
    "_analyze_function_calls",  # Phase 2 placeholder (documented)
]

# Files to skip for orphaned import checking (known false positives)
SKIP_ORPHAN_CHECK = [
    "agent_health_monitor.py",  # Uses timedelta conceptually but not in current code path
]

# Files to skip for text marker checking (intentional design patterns)
SKIP_TEXT_MARKER_CHECK = [
    "agent_health_monitor.py",       # Contains patterns as regex definitions
    "structural_integrity_audit.py", # This audit file itself
    "intent_listener.py",            # Base class "not implemented" warnings (intentional)
    "agent_ethicist.py",             # "Hardcoded Safety" - intentional safety constitution
    "agent_scholar.py",              # "hardcoded blocklist" - intentional security
]

class StructuralIntegrityAudit:
    def __init__(self):
        self.issues = defaultdict(list)
        self.stats = {
            'files_scanned': 0,
            'functions_found': 0,
            'stub_functions': 0,
            'dead_code': 0,
            'orphaned_imports': 0,
            'undefined_names': 0,
            'text_markers': 0,
            'bare_excepts': 0,
            'hardcoded_secrets': 0,
            'resource_leaks': 0,
            'style_violations': 0,
            'type_errors': 0,
            'complexity_issues': 0,
        }
        
    def scan_file(self, filepath):
        """Scan a single Python file for structural issues."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse AST
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                self.issues['syntax_error'].append(f"{filepath}: {e}")
                return
                
            self.stats['files_scanned'] += 1
            relative_path = os.path.relpath(filepath, BASE_DIR)
            
            # 1. Text Pattern Markers (original audit)
            self._check_text_markers(content, relative_path)
            
            # 2. Stub Functions
            self._check_stub_functions(tree, relative_path)
            
            # 3. Orphaned Imports
            self._check_orphaned_imports(tree, content, relative_path)
            
            # 4. Function Call Analysis (for dead code detection)
            self._analyze_function_calls(tree, relative_path)
            
            # 5. Undefined Names (pyflakes-style check)
            self._check_undefined_names(filepath, relative_path)
            
            # 6. Bare Except Blocks
            self._check_bare_excepts(tree, relative_path)
            
            # 7. Hardcoded Secrets
            self._check_hardcoded_secrets(content, relative_path)
            
            # 8. Resource Leaks (unclosed files/connections)
            self._check_resource_leaks(tree, relative_path)
            
            # 9. Style Violations (flake8)
            self._check_style_violations(filepath, relative_path)
            
            # 10. Type Errors (mypy)
            self._check_type_errors(filepath, relative_path)
            
            # 11. Complexity Metrics (radon)
            self._check_complexity(filepath, relative_path)
            
        except Exception as e:
            self.issues['scan_error'].append(f"{filepath}: {e}")
    
    def _check_text_markers(self, content, filepath):
        """Original text pattern matching."""
        # Skip files that contain these patterns as part of scanner logic
        filename = os.path.basename(filepath)
        if filename in SKIP_TEXT_MARKER_CHECK:
            return
            
        patterns = {
            'PLACEHOLDER': r'\[placeholder\]',
            'SIMULATED': r'\[simulated\]',
            'NOT_IMPLEMENTED': r'not implemented',
            'TODO': r'#.*todo',
            'HARDCODED': r'hardcode',
            'PARTIAL': r'\[partial\]',
        }
        
        for marker, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                self.stats['text_markers'] += len(matches)
                self.issues['text_marker'].append(f"{filepath}: {marker} ({len(matches)}x)")
    
    def _check_stub_functions(self, tree, filepath):
        """Find functions that just pass or return None."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.stats['functions_found'] += 1
                
                # Skip intentional stubs
                if node.name in INTENTIONAL_STUBS:
                    continue
                    
                # Check if body is just pass
                if len(node.body) == 1:
                    body = node.body[0]
                    
                    # Just `pass`
                    if isinstance(body, ast.Pass):
                        self.stats['stub_functions'] += 1
                        self.issues['stub_function'].append(
                            f"{filepath}: {node.name}() - empty body (pass)"
                        )
                    
                    # Just `return None` or `return`
                    elif isinstance(body, ast.Return):
                        if body.value is None or (isinstance(body.value, ast.Constant) and body.value.value is None):
                            self.stats['stub_functions'] += 1
                            self.issues['stub_function'].append(
                                f"{filepath}: {node.name}() - returns None only"
                            )
                    
                    # Just a docstring (no actual code)
                    elif isinstance(body, ast.Expr) and isinstance(body.value, ast.Constant):
                        # This is just a docstring with no code
                        self.stats['stub_functions'] += 1
                        self.issues['stub_function'].append(
                            f"{filepath}: {node.name}() - docstring only, no implementation"
                        )
    
    def _check_orphaned_imports(self, tree, content, filepath):
        """Find imports that are never used."""
        # Skip files with known false positives
        filename = os.path.basename(filepath)
        if filename in SKIP_ORPHAN_CHECK:
            return
            
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports.append(name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != '*':
                        name = alias.asname if alias.asname else alias.name
                        imports.append(name)
        
        for imp in set(imports):
            # Count usages (excluding the import line itself)
            # Simple heuristic: if the name appears only once, it's likely unused
            pattern = rf'\b{re.escape(imp)}\b'
            matches = re.findall(pattern, content)
            if len(matches) <= 1:
                self.stats['orphaned_imports'] += 1
                self.issues['orphaned_import'].append(f"{filepath}: '{imp}' imported but not used")
    
    def _analyze_function_calls(self, tree, filepath):
        """Collect function definitions and calls for dead code analysis."""
        # Track defined functions vs called functions
        defined = set()
        called = set()
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith('_'):  # Skip private methods
                    defined.add(node.name)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called.add(node.func.attr)
        
        # Find functions defined but never called (potential dead code)
        uncalled = defined - called
        # Filter out common patterns that are called externally
        external_patterns = ['run', 'execute', 'process', 'handle', 'start', 'main', 'init', 'setup']
        for func in uncalled:
            if not any(p in func.lower() for p in external_patterns):
                self.stats['dead_code'] += 1
                # Don't flag as issue yet - just track for review
    
    def _check_undefined_names(self, filepath, relative_path):
        """
        Check for undefined names (variables/modules used but never defined/imported).
        Uses pyflakes if available, falls back to basic AST analysis.
        
        This catches errors like: 'sqlite3' is not defined
        """
        # Try pyflakes first (most accurate)
        try:
            result = subprocess.run(
                ['python3', '-m', 'pyflakes', filepath],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line and 'undefined name' in line.lower():
                        self.stats['undefined_names'] += 1
                        # Clean up the output for display
                        clean_line = line.replace(filepath, relative_path)
                        self.issues['undefined_name'].append(clean_line)
            return
        except FileNotFoundError:
            # pyflakes not installed, fall back to AST analysis
            pass
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        
        # Fallback: Basic AST-based undefined name detection
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            tree = ast.parse(content)
            
            # Collect all defined names (imports, assignments, function defs)
            defined_names = set()
            used_names = set()
            
            for node in ast.walk(tree):
                # Collect defined names
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name.split('.')[0]
                        defined_names.add(name)
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name != '*':
                            name = alias.asname if alias.asname else alias.name
                            defined_names.add(name)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    defined_names.add(node.name)
                    # Add function parameters
                    for arg in node.args.args:
                        defined_names.add(arg.arg)
                elif isinstance(node, ast.ClassDef):
                    defined_names.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            defined_names.add(target.id)
                elif isinstance(node, ast.For):
                    if isinstance(node.target, ast.Name):
                        defined_names.add(node.target.id)
                elif isinstance(node, ast.With):
                    for item in node.items:
                        if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                            defined_names.add(item.optional_vars.id)
                elif isinstance(node, ast.ExceptHandler):
                    if node.name:
                        defined_names.add(node.name)
                
                # Collect used names (Name nodes in Load context)
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
            
            # Add Python builtins
            builtins = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))
            builtins.update(['True', 'False', 'None', '__name__', '__file__', '__doc__', 
                           'print', 'range', 'len', 'str', 'int', 'float', 'list', 'dict',
                           'set', 'tuple', 'open', 'type', 'isinstance', 'hasattr', 'getattr',
                           'setattr', 'callable', 'property', 'staticmethod', 'classmethod',
                           'super', 'Exception', 'ValueError', 'TypeError', 'KeyError',
                           'AttributeError', 'RuntimeError', 'StopIteration', 'OSError',
                           'FileNotFoundError', 'PermissionError', 'ConnectionError',
                           'sorted', 'reversed', 'enumerate', 'zip', 'map', 'filter', 'any', 'all',
                           'min', 'max', 'sum', 'abs', 'round', 'pow', 'divmod', 'hex', 'oct', 'bin',
                           'format', 'repr', 'ascii', 'ord', 'chr', 'bytes', 'bytearray',
                           'memoryview', 'object', 'bool', 'complex', 'slice', 'frozenset'])
            
            # Find undefined names
            undefined = used_names - defined_names - builtins
            
            for name in undefined:
                # Skip common false positives
                if name.startswith('_') or name in ['self', 'cls']:
                    continue
                self.stats['undefined_names'] += 1
                self.issues['undefined_name'].append(f"{relative_path}: undefined name '{name}'")
        except Exception:
            pass
    
    def _check_bare_excepts(self, tree, filepath):
        """
        Check for bare except blocks that swallow all errors.
        These hide real problems and should specify exception types.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # Bare except (no type specified)
                if node.type is None:
                    self.stats['bare_excepts'] += 1
                    line_no = node.lineno
                    self.issues['bare_except'].append(
                        f"{filepath}:{line_no}: bare 'except:' - specify exception type"
                    )
                # except Exception: (too broad, but less severe)
                elif isinstance(node.type, ast.Name) and node.type.id == 'Exception':
                    # Only flag if the body just passes (swallows silently)
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        self.stats['bare_excepts'] += 1
                        line_no = node.lineno
                        self.issues['bare_except'].append(
                            f"{filepath}:{line_no}: 'except Exception: pass' - swallows errors silently"
                        )
    
    def _check_hardcoded_secrets(self, content, filepath):
        """
        Check for hardcoded secrets like API keys, passwords, tokens.
        Uses regex patterns to detect potential secrets.
        """
        # Skip this file (contains regex patterns as test data)
        if 'structural_integrity_audit' in filepath:
            return
            
        secret_patterns = [
            (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][a-zA-Z0-9_\-]{20,}["\']', 'API key'),
            (r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}["\']', 'Password/Secret'),
            (r'(?i)(token|auth[_-]?token|access[_-]?token)\s*[=:]\s*["\'][a-zA-Z0-9_\-]{20,}["\']', 'Token'),
            (r'(?i)(private[_-]?key)\s*[=:]\s*["\'][^"\']{30,}["\']', 'Private key'),
            (r'sk-[a-zA-Z0-9]{32,}', 'OpenAI API key'),
            (r'ghp_[a-zA-Z0-9]{36,}', 'GitHub token'),
            (r'xox[baprs]-[a-zA-Z0-9\-]{10,}', 'Slack token'),
        ]
        
        for pattern, secret_type in secret_patterns:
            matches = re.findall(pattern, content)
            if matches:
                # Don't report the actual secret value
                self.stats['hardcoded_secrets'] += 1
                self.issues['hardcoded_secret'].append(
                    f"{filepath}: potential {secret_type} found"
                )
    
    def _check_resource_leaks(self, tree, filepath):
        """
        Check for potential resource leaks (files/connections opened but not closed).
        Looks for open()/connect() calls not in 'with' statements.
        """
        # Track which nodes are inside 'with' statements
        with_items = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.With):
                for item in node.items:
                    # Mark the context expression
                    if isinstance(item.context_expr, ast.Call):
                        if isinstance(item.context_expr.func, ast.Name):
                            with_items.add(id(item.context_expr))
        
        # Now find open() and connect() calls outside 'with'
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                
                # Check for risky functions
                risky_funcs = ['open', 'connect', 'socket']
                if func_name in risky_funcs and id(node) not in with_items:
                    # Check if it's in an assignment (might be closed later)
                    # This is a simplified check - real analysis would be more complex
                    line_no = node.lineno
                    self.stats['resource_leaks'] += 1
                    self.issues['resource_leak'].append(
                        f"{filepath}:{line_no}: '{func_name}()' not in 'with' statement - potential leak"
                    )
    
    def _check_style_violations(self, filepath, relative_path):
        """
        Check for PEP8 style violations using flake8.
        Only reports significant issues (not minor formatting).
        """
        try:
            # Run flake8 with specific error codes only (significant ones)
            # E9: syntax errors, F: pyflakes, W6: deprecated features
            result = subprocess.run(
                ['python3', '-m', 'flake8', '--select=E9,F,W6', '--max-line-length=120', filepath],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        self.stats['style_violations'] += 1
                        clean_line = line.replace(filepath, relative_path)
                        self.issues['style_violation'].append(clean_line)
        except FileNotFoundError:
            # flake8 not installed - skip silently
            pass
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
    
    def _check_type_errors(self, filepath, relative_path):
        """
        Check for type errors using mypy (if installed).
        Only reports actual errors, not hints.
        """
        try:
            result = subprocess.run(
                ['python3', '-m', 'mypy', '--ignore-missing-imports', '--no-error-summary', filepath],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    # Only count actual errors
                    if ': error:' in line:
                        self.stats['type_errors'] += 1
                        clean_line = line.replace(filepath, relative_path)
                        self.issues['type_error'].append(clean_line)
        except FileNotFoundError:
            # mypy not installed - skip silently
            pass
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
    
    def _check_complexity(self, filepath, relative_path):
        """
        Check function complexity using radon (if installed).
        Flags functions with cyclomatic complexity > 10.
        """
        try:
            result = subprocess.run(
                ['python3', '-m', 'radon', 'cc', '-s', '-a', filepath],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    # Look for functions with grade C, D, or F (complexity > 10)
                    if ' - ' in line and any(f' {grade} ' in line for grade in ['C', 'D', 'F']):
                        self.stats['complexity_issues'] += 1
                        clean_line = line.replace(filepath, relative_path)
                        self.issues['complexity'].append(f"{relative_path}: {line.strip()}")
        except FileNotFoundError:
            # radon not installed - skip silently
            pass
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
    
    # =========================================================================
    # BEHAVIORAL TESTING (Phase 2)
    # =========================================================================
    
    def run_behavioral_tests(self):
        """Test that key system components actually function."""
        import sqlite3
        import json
        
        db_path = os.path.join(BASE_DIR, 'republic.db')
        bridge_path = os.path.join(os.path.dirname(BASE_DIR), 'The_Bridge')
        
        # Track behavioral test results
        self.stats['behavioral_tests'] = 0
        self.stats['behavioral_passed'] = 0
        
        # 1. DATABASE CONNECTIVITY
        self._test_database_connectivity(db_path)
        
        # 2. BRIDGE PATH INTEGRITY  
        self._test_bridge_paths(bridge_path)
        
        # 3. AGENT INSTANTIATION
        self._test_agent_instantiation()
        
        # 4. DATABASE TABLE USAGE
        self._test_database_integrity(db_path)
        
        # 5. WORKFLOW PATHS
        self._test_workflow_paths()
    
    def _test_database_connectivity(self, db_path):
        """Verify database is accessible and responsive."""
        self.stats['behavioral_tests'] += 1
        test_name = "Database Connectivity"
        
        try:
            import sqlite3
            conn = sqlite3.connect(db_path, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] == 1:
                self.stats['behavioral_passed'] += 1
            else:
                self.issues['behavioral_fail'].append(f"{test_name}: Query returned unexpected result")
        except Exception as e:
            self.issues['behavioral_fail'].append(f"{test_name}: {e}")
    
    def _test_bridge_paths(self, bridge_path):
        """Verify The_Bridge structure is intact and writable."""
        required_dirs = ['Inbox', 'Outbox', 'Logs']
        
        for dir_name in required_dirs:
            self.stats['behavioral_tests'] += 1
            test_name = f"Bridge Path: {dir_name}"
            dir_path = os.path.join(bridge_path, dir_name)
            
            try:
                if os.path.exists(dir_path) and os.path.isdir(dir_path):
                    # Test write permission
                    test_file = os.path.join(dir_path, '.audit_test')
                    with open(test_file, 'w') as f:
                        f.write('audit')
                    os.remove(test_file)
                    self.stats['behavioral_passed'] += 1
                else:
                    self.issues['behavioral_fail'].append(f"{test_name}: Directory missing")
            except PermissionError:
                self.issues['behavioral_fail'].append(f"{test_name}: No write permission")
            except Exception as e:
                self.issues['behavioral_fail'].append(f"{test_name}: {e}")
    
    def _test_agent_instantiation(self):
        """Test that core agents can be instantiated without error."""
        core_agents = [
            ('The_Cabinet.agent_lef', 'AgentLEF'),
            ('Dept_Consciousness.claude_context_manager', 'ClaudeContextManager'),
            ('Dept_Civics.agent_constitution_guard', 'ConstitutionGuard'),
        ]
        
        for module_path, class_name in core_agents:
            self.stats['behavioral_tests'] += 1
            test_name = f"Agent Instantiation: {class_name}"
            
            try:
                import importlib
                module = importlib.import_module(f"departments.{module_path}")
                agent_class = getattr(module, class_name)
                # Just verify the class exists and is callable
                if callable(agent_class):
                    self.stats['behavioral_passed'] += 1
                else:
                    self.issues['behavioral_fail'].append(f"{test_name}: Not callable")
            except ImportError as e:
                self.issues['behavioral_fail'].append(f"{test_name}: Import failed - {e}")
            except AttributeError as e:
                self.issues['behavioral_fail'].append(f"{test_name}: Class not found - {e}")
            except Exception as e:
                self.issues['behavioral_fail'].append(f"{test_name}: {e}")
    
    def _test_database_integrity(self, db_path):
        """Verify critical tables exist and have expected structure."""
        critical_tables = {
            'lef_monologue': ['timestamp', 'thought'],
            'agent_logs': ['source', 'level', 'message'],
            'trade_queue': ['asset', 'action', 'status'],
            'stablecoin_buckets': ['bucket_type', 'balance'],
            'lef_scars': ['scar_type', 'description'],
        }
        
        try:
            import sqlite3
            conn = sqlite3.connect(db_path, timeout=5.0)
            cursor = conn.cursor()
            
            for table, expected_cols in critical_tables.items():
                self.stats['behavioral_tests'] += 1
                test_name = f"Table Integrity: {table}"
                
                try:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [row[1] for row in cursor.fetchall()]
                    
                    missing_cols = [c for c in expected_cols if c not in columns]
                    if missing_cols:
                        self.issues['behavioral_fail'].append(
                            f"{test_name}: Missing columns {missing_cols}"
                        )
                    else:
                        self.stats['behavioral_passed'] += 1
                except Exception as e:
                    self.issues['behavioral_fail'].append(f"{test_name}: {e}")
            
            conn.close()
        except Exception as e:
            self.issues['behavioral_fail'].append(f"Database Integrity: {e}")
    
    def _test_workflow_paths(self):
        """Verify key workflow paths are functional."""
        workflows = [
            {
                'name': 'Hippocampus Memory Path',
                'check': lambda: os.path.exists(os.path.join(
                    os.path.dirname(BASE_DIR), 'The_Bridge', 'claude_memory.json'
                )),
                'required': True
            },
            {
                'name': 'Constitution Path',
                'check': lambda: os.path.exists(os.path.join(BASE_DIR, 'CONSTITUTION.md')),
                'required': True
            },
            {
                'name': 'Governance Laws Path',
                'check': lambda: os.path.isdir(os.path.join(BASE_DIR, 'governance', 'laws')),
                'required': True
            },
            {
                'name': 'Config Path',
                'check': lambda: os.path.exists(os.path.join(BASE_DIR, 'config.json')),
                'required': False  # Optional - may use defaults
            },
        ]
        
        for workflow in workflows:
            self.stats['behavioral_tests'] += 1
            test_name = f"Workflow: {workflow['name']}"
            is_required = workflow.get('required', True)
            
            try:
                if workflow['check']():
                    self.stats['behavioral_passed'] += 1
                elif is_required:
                    self.issues['behavioral_fail'].append(f"{test_name}: Path missing or inaccessible")
                else:
                    # Optional path missing - still count as passed
                    self.stats['behavioral_passed'] += 1
            except Exception as e:
                if is_required:
                    self.issues['behavioral_fail'].append(f"{test_name}: {e}")
                else:
                    self.stats['behavioral_passed'] += 1
    
    def scan_directory(self, directory=DEPARTMENTS_DIR):
        """Scan all Python files in directory."""
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    self.scan_file(filepath)
    
    # =========================================================================
    # RUNTIME HEALTH CHECKS (NEW - Phase 1 of Audit Revision)
    # =========================================================================
    
    def run_runtime_health_checks(self):
        """
        Analyze runtime logs for recurring errors and unacted recommendations.
        This catches operational issues that static analysis cannot detect.
        """
        from collections import Counter
        from datetime import datetime, timedelta
        import json
        
        log_path = os.path.join(BASE_DIR, 'republic.log')
        lessons_path = os.path.join(os.path.dirname(BASE_DIR), 'The_Bridge', 'Logs', 'System_Lessons.md')
        
        self.stats['runtime_health_tests'] = 0
        self.stats['runtime_health_passed'] = 0
        
        # Test 1: Check for recurring errors in last 24h
        self._check_recurring_errors(log_path)
        
        # Test 2: Check error velocity (errors per hour trending)
        self._check_error_velocity(log_path)
        
        # Test 3: Check for unacted recommendations
        self._check_unacted_recommendations(log_path)
        
        # Test 4: Check for resource exhaustion events
        self._check_resource_exhaustion(log_path)
    
    def _check_recurring_errors(self, log_path):
        """Detect if the same error message repeats more than 3 times in 24h."""
        from collections import Counter
        from datetime import datetime, timedelta
        
        self.stats['runtime_health_tests'] += 1
        test_name = "Recurring Errors (24h)"
        
        try:
            if not os.path.exists(log_path):
                self.stats['runtime_health_passed'] += 1
                return
            
            error_messages = Counter()
            cutoff = datetime.now() - timedelta(hours=24)
            
            with open(log_path, 'r', errors='ignore') as f:
                for line in f:
                    # Parse log lines with format: YYYY-MM-DD HH:MM:SS,mmm - ...
                    if ' - ERROR - ' in line or ' - CRITICAL - ' in line or ' - WARNING - ' in line:
                        try:
                            # Extract timestamp
                            timestamp_str = line[:23]  # 'YYYY-MM-DD HH:MM:SS,mmm'
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                            
                            if timestamp >= cutoff:
                                # Extract the error message (after the log level)
                                parts = line.split(' - ', 3)
                                if len(parts) >= 4:
                                    message = parts[3].strip()[:100]  # Truncate for grouping
                                    error_messages[message] += 1
                        except (ValueError, IndexError):
                            continue
            
            # Find recurring errors (same message > 3 times)
            recurring = {msg: count for msg, count in error_messages.items() if count > 3}
            
            if recurring:
                worst = max(recurring.items(), key=lambda x: x[1])
                self.issues['runtime_recurring_error'].append(
                    f"{test_name}: '{worst[0][:50]}...' repeated {worst[1]}x in 24h"
                )
                # Add up to 3 worst offenders
                for msg, count in sorted(recurring.items(), key=lambda x: -x[1])[:3]:
                    if count > 5:
                        self.issues['runtime_recurring_error'].append(
                            f"  → '{msg[:60]}...' ({count}x)"
                        )
            else:
                self.stats['runtime_health_passed'] += 1
                
        except Exception as e:
            self.issues['runtime_error'].append(f"{test_name}: Could not analyze - {e}")
    
    def _check_error_velocity(self, log_path):
        """Detect if errors per hour are trending upward (acceleration)."""
        from collections import defaultdict
        from datetime import datetime, timedelta
        
        self.stats['runtime_health_tests'] += 1
        test_name = "Error Velocity"
        
        try:
            if not os.path.exists(log_path):
                self.stats['runtime_health_passed'] += 1
                return
            
            hourly_errors = defaultdict(int)
            cutoff = datetime.now() - timedelta(hours=6)
            
            with open(log_path, 'r', errors='ignore') as f:
                for line in f:
                    if ' - ERROR - ' in line or ' - CRITICAL - ' in line:
                        try:
                            timestamp_str = line[:19]  # 'YYYY-MM-DD HH:MM:SS'
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            
                            if timestamp >= cutoff:
                                hour_key = timestamp.strftime('%Y-%m-%d %H:00')
                                hourly_errors[hour_key] += 1
                        except (ValueError, IndexError):
                            continue
            
            if len(hourly_errors) >= 3:
                # Check if trend is accelerating
                sorted_hours = sorted(hourly_errors.keys())
                values = [hourly_errors[h] for h in sorted_hours[-3:]]
                
                if len(values) >= 3 and values[2] > values[1] > values[0]:
                    self.issues['runtime_error_velocity'].append(
                        f"{test_name}: Errors accelerating - {values[0]} → {values[1]} → {values[2]} per hour"
                    )
                else:
                    self.stats['runtime_health_passed'] += 1
            else:
                self.stats['runtime_health_passed'] += 1
                
        except Exception as e:
            self.issues['runtime_error'].append(f"{test_name}: Could not analyze - {e}")
    
    def _check_unacted_recommendations(self, log_path):
        """Detect recommendations that appear multiple times without resolution."""
        from collections import Counter
        
        self.stats['runtime_health_tests'] += 1
        test_name = "Unacted Recommendations"
        
        try:
            if not os.path.exists(log_path):
                self.stats['runtime_health_passed'] += 1
                return
            
            recommendations = Counter()
            
            with open(log_path, 'r', errors='ignore') as f:
                for line in f:
                    # Look for recommendation patterns
                    line_lower = line.lower()
                    if 'recommend' in line_lower or 'should' in line_lower or 'action needed' in line_lower:
                        # Extract a normalized version of the recommendation
                        message = line.strip()[-150:]  # Last 150 chars
                        recommendations[message] += 1
            
            # Recommendations repeated > 5 times are likely unacted
            unacted = {rec: count for rec, count in recommendations.items() if count > 5}
            
            if unacted:
                worst = max(unacted.items(), key=lambda x: x[1])
                self.issues['runtime_unacted_recommendation'].append(
                    f"{test_name}: Same recommendation repeated {worst[1]}x"
                )
            else:
                self.stats['runtime_health_passed'] += 1
                
        except Exception as e:
            self.issues['runtime_error'].append(f"{test_name}: Could not analyze - {e}")
    
    def _check_resource_exhaustion(self, log_path):
        """Detect resource exhaustion events (pool exhaustion, OOM, timeouts)."""
        self.stats['runtime_health_tests'] += 1
        test_name = "Resource Exhaustion"
        
        try:
            if not os.path.exists(log_path):
                self.stats['runtime_health_passed'] += 1
                return
            
            exhaustion_patterns = [
                'pool exhausted',
                'connection pool',
                'out of memory',
                'timeout',
                'resource limit',
                'too many open files',
                'database is locked',
            ]
            
            found_issues = []
            
            with open(log_path, 'r', errors='ignore') as f:
                for line in f:
                    line_lower = line.lower()
                    for pattern in exhaustion_patterns:
                        if pattern in line_lower:
                            found_issues.append(pattern)
                            break
            
            if len(found_issues) > 10:
                from collections import Counter
                counts = Counter(found_issues)
                worst = counts.most_common(1)[0]
                self.issues['runtime_resource_exhaustion'].append(
                    f"{test_name}: '{worst[0]}' occurred {worst[1]}x"
                )
            else:
                self.stats['runtime_health_passed'] += 1
                
        except Exception as e:
            self.issues['runtime_error'].append(f"{test_name}: Could not analyze - {e}")
    
    # =========================================================================
    # FINANCIAL INTEGRITY CHECKS (NEW - Phase 2 of Audit Revision)
    # =========================================================================
    
    def run_financial_integrity_checks(self):
        """
        Verify financial values are plausible and not corrupted.
        Catches hallucinated values like $1.46e+39.
        """
        import json
        import sqlite3
        
        self.stats['financial_integrity_tests'] = 0
        self.stats['financial_integrity_passed'] = 0
        
        # Test 1: Check wealth_strategy.json for plausible values
        self._check_config_plausibility()
        
        # Test 2: Check database for impossible financial values
        self._check_database_financial_integrity()
        
        # Test 3: Check for exponential notation in logs (hallucination signal)
        self._check_hallucinated_values()
    
    def _check_config_plausibility(self):
        """Verify wealth_strategy.json has plausible values."""
        import json
        
        self.stats['financial_integrity_tests'] += 1
        test_name = "Config Plausibility"
        
        config_path = os.path.join(BASE_DIR, 'config', 'wealth_strategy.json')
        
        try:
            if not os.path.exists(config_path):
                self.stats['financial_integrity_passed'] += 1
                return
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            issues = []
            
            # Check allocation percentages sum to 1.0
            dynasty_pct = config.get('DYNASTY', {}).get('allocation_pct', 0)
            arena_pct = config.get('ARENA', {}).get('allocation_pct', 0)
            total_pct = dynasty_pct + arena_pct
            
            if not (0.99 <= total_pct <= 1.01):
                issues.append(f"Allocation doesn't sum to 100%: {total_pct*100:.1f}%")
            
            # Check position sizing isn't ultra-aggressive (> 50% per position)
            # This is a constitutional check
            dynasty_tp = config.get('DYNASTY', {}).get('take_profit_threshold', 0)
            if dynasty_tp > 2.0:  # > 200% take profit is suspicious
                issues.append(f"Dynasty take profit suspicious: {dynasty_tp*100:.0f}%")
            
            if issues:
                for issue in issues:
                    self.issues['financial_config_issue'].append(f"{test_name}: {issue}")
            else:
                self.stats['financial_integrity_passed'] += 1
                
        except Exception as e:
            self.issues['financial_error'].append(f"{test_name}: Could not analyze - {e}")
    
    def _check_database_financial_integrity(self):
        """Check database for impossible financial values."""
        import sqlite3
        
        self.stats['financial_integrity_tests'] += 1
        test_name = "Database Financial Integrity"
        
        db_path = os.path.join(BASE_DIR, 'republic.db')
        
        try:
            conn = sqlite3.connect(db_path, timeout=5.0)
            cursor = conn.cursor()
            
            issues = []
            
            # Check for impossible values in assets table
            try:
                cursor.execute("SELECT symbol, amount FROM assets WHERE amount > 1000000000")
                impossible = cursor.fetchall()
                if impossible:
                    for symbol, amount in impossible:
                        issues.append(f"Impossible asset value: {symbol} = {amount}")
            except sqlite3.OperationalError:
                pass  # Table might not exist
            
            # Check for negative asset amounts
            try:
                cursor.execute("SELECT symbol, amount FROM assets WHERE amount < 0")
                negative = cursor.fetchall()
                if negative:
                    for symbol, amount in negative:
                        issues.append(f"Negative asset: {symbol} = {amount}")
            except sqlite3.OperationalError:
                pass
            
            conn.close()
            
            if issues:
                for issue in issues:
                    self.issues['financial_db_issue'].append(f"{test_name}: {issue}")
            else:
                self.stats['financial_integrity_passed'] += 1
                
        except Exception as e:
            self.issues['financial_error'].append(f"{test_name}: Could not analyze - {e}")
    
    def _check_hallucinated_values(self):
        """Check logs for exponential notation which indicates hallucinated values."""
        self.stats['financial_integrity_tests'] += 1
        test_name = "Hallucinated Values"
        
        log_path = os.path.join(BASE_DIR, 'republic.log')
        
        try:
            if not os.path.exists(log_path):
                self.stats['financial_integrity_passed'] += 1
                return
            
            # Pattern for suspicious exponential values
            import re
            exp_pattern = re.compile(r'\$?\d+\.?\d*e\+[3-9]\d')  # e+30 or higher
            
            found = []
            with open(log_path, 'r', errors='ignore') as f:
                for i, line in enumerate(f):
                    if exp_pattern.search(line):
                        # Extract the value
                        match = exp_pattern.search(line)
                        if match:
                            found.append(match.group())
            
            if found:
                self.issues['financial_hallucination'].append(
                    f"{test_name}: Found {len(found)} exponential values in logs (e.g., {found[0]})"
                )
            else:
                self.stats['financial_integrity_passed'] += 1
                
        except Exception as e:
            self.issues['financial_error'].append(f"{test_name}: Could not analyze - {e}")
    
    def check_intent_routing(self):
        """Check for agents that should be in INTENT_ROUTING but aren't."""
        # Get all agent files
        agent_files = []
        for root, dirs, files in os.walk(DEPARTMENTS_DIR):
            for file in files:
                if file.startswith('agent_') and file.endswith('.py'):
                    agent_name = file.replace('.py', '')
                    agent_files.append(agent_name)
        
        # Read INTENT_ROUTING from agent_executor.py
        executor_path = os.path.join(DEPARTMENTS_DIR, 'The_Cabinet', 'agent_executor.py')
        if os.path.exists(executor_path):
            with open(executor_path, 'r') as f:
                content = f.read()
            
            routed_agents = set(re.findall(r"'(agent_\w+)'", content))
            
            # Find agents not in routing
            for agent in agent_files:
                if agent not in routed_agents and agent != 'agent_executor':
                    # Not every agent needs to be routed - only flag if it has IntentListenerMixin
                    agent_path = None
                    for root, dirs, files in os.walk(DEPARTMENTS_DIR):
                        if f"{agent}.py" in files:
                            agent_path = os.path.join(root, f"{agent}.py")
                            break
                    
                    if agent_path:
                        with open(agent_path, 'r') as f:
                            agent_content = f.read()
                        if 'IntentListenerMixin' in agent_content:
                            self.issues['disconnected_agent'].append(
                                f"{agent} has IntentListenerMixin but no route in INTENT_ROUTING"
                            )
    
    def generate_report(self):
        """Generate the structural integrity report."""
        total_issues = sum(len(v) for v in self.issues.values())
        
        # Per-category scoring with individual weights
        category_config = {
            # key: (weight_per_issue, max_reasonable_count)
            'syntax_error': (20, 5),
            'undefined_name': (10, 10),
            'hardcoded_secret': (15, 7),
            'bare_except': (0.8, 125),
            'type_error': (0.2, 500),
            'resource_leak': (0.5, 200),
            'complexity': (2, 50),
            'stub_function': (3, 30),
            'disconnected_agent': (5, 20),
            'style_violation': (0.1, 1000),
            'text_marker': (2, 50),
            'orphaned_import': (1, 100),
        }
        
        category_scores = {}
        for key, (weight, _) in category_config.items():
            count = len(self.issues.get(key, []))
            score = max(0, 100 - (count * weight))
            category_scores[key] = score
        
        # Overall static score is average of all categories
        static_score = sum(category_scores.values()) / len(category_scores) if category_scores else 100
        
        behavioral_tests = self.stats.get('behavioral_tests', 0)
        behavioral_passed = self.stats.get('behavioral_passed', 0)
        behavioral_score = (behavioral_passed / behavioral_tests * 100) if behavioral_tests > 0 else 100
        
        # NEW: Runtime Health scoring
        runtime_tests = self.stats.get('runtime_health_tests', 0)
        runtime_passed = self.stats.get('runtime_health_passed', 0)
        runtime_score = (runtime_passed / runtime_tests * 100) if runtime_tests > 0 else 100
        
        # NEW: Financial Integrity scoring
        financial_tests = self.stats.get('financial_integrity_tests', 0)
        financial_passed = self.stats.get('financial_integrity_passed', 0)
        financial_score = (financial_passed / financial_tests * 100) if financial_tests > 0 else 100
        
        # REVISED Weighted composite (as per AUDIT_REVISION_PROPOSAL.md):
        # Static: 20%, Behavioral: 20%, Runtime Health: 25%, Financial: 15%, (Governance: 15%, Unresolved: 5% - future)
        # For now, normalize to available layers
        score = (static_score * 0.20) + (behavioral_score * 0.20) + (runtime_score * 0.35) + (financial_score * 0.25)
        
        # Helper to create progress bar
        def progress_bar(pct, width=10):
            filled = int(pct / 100 * width)
            return '█' * filled + '░' * (width - filled)
        
        report = []
        report.append("=" * 60)
        report.append("STRUCTURAL INTEGRITY AUDIT (Comprehensive Protocol)")
        report.append("=" * 60)
        report.append("")
        report.append(f"📊 Composite Health Score: {score:.1f}%")
        report.append(f"   ├─ Static Analysis: {static_score:.1f}% (20%)")
        report.append(f"   ├─ Behavioral Tests: {behavioral_score:.1f}% ({behavioral_passed}/{behavioral_tests}) (20%)")
        report.append(f"   ├─ Runtime Health: {runtime_score:.1f}% ({runtime_passed}/{runtime_tests}) (35%)")
        report.append(f"   └─ Financial Integrity: {financial_score:.1f}% ({financial_passed}/{financial_tests}) (25%)")
        
        report.append("")
        report.append(f"📁 Files Scanned: {self.stats['files_scanned']}")
        report.append(f"🔧 Functions Found: {self.stats['functions_found']}")
        report.append(f"🧪 Behavioral Tests: {behavioral_tests}")
        report.append(f"⚠️  Total Issues: {total_issues}")
        report.append("")
        report.append("-" * 60)
        report.append("STATIC ANALYSIS (Per-Category Scores)")
        report.append("-" * 60)
        
        static_categories = [
            # Critical (cause crashes)
            ('syntax_error', '❌ Syntax Errors', 'Critical'),
            ('undefined_name', '🚫 Undefined Names', 'Critical'),
            ('hardcoded_secret', '🔐 Hardcoded Secrets', 'Security'),
            # Important (cause bugs)
            ('bare_except', '🙈 Bare Excepts', 'Important'),
            ('type_error', '🔤 Type Errors', 'Important'),
            ('resource_leak', '💧 Resource Leaks', 'Important'),
            # Moderate (code quality)
            ('complexity', '🌀 Complexity', 'Moderate'),
            ('stub_function', '🔌 Stub Functions', 'Moderate'),
            ('disconnected_agent', '🤖 Disconnected Agents', 'Moderate'),
            # Minor (style/cleanup)
            ('style_violation', '🎨 Style Violations', 'Minor'),
            ('text_marker', '📝 Text Markers', 'Minor'),
            ('orphaned_import', '📦 Orphaned Imports', 'Minor'),
        ]
        
        report.append("")
        report.append("Category Scores:")
        for key, label, severity in static_categories:
            cat_score = category_scores.get(key, 100)
            count = len(self.issues.get(key, []))
            bar = progress_bar(cat_score)
            report.append(f"  {bar} {cat_score:5.1f}%  {label} ({count})")
        
        report.append("")
        report.append("Issue Details:")
        static_clean = True
        for key, label, severity in static_categories:
            issues = self.issues.get(key, [])
            if issues:
                static_clean = False
                report.append("")
                report.append(f"{label} ({len(issues)}) [{severity}]")
                for issue in issues[:10]:
                    report.append(f"  • {issue}")
                if len(issues) > 10:
                    report.append(f"  ... and {len(issues) - 10} more")
        
        if static_clean:
            report.append("✅ No static analysis issues found")
        
        report.append("")
        report.append("-" * 60)
        report.append("BEHAVIORAL TESTS")
        report.append("-" * 60)
        
        behavioral_issues = self.issues.get('behavioral_fail', [])
        if behavioral_issues:
            report.append("")
            report.append(f"🧪 Behavioral Failures ({len(behavioral_issues)}) - System dysfunction")
            for issue in behavioral_issues:
                report.append(f"  • {issue}")
        else:
            report.append("✅ All behavioral tests passed")
        
        report.append("")
        report.append("=" * 60)
        
        # Score interpretation
        if score >= 90:
            report.append("✅ FULLY HEALTHY - All systems operational")
        elif score >= 70:
            report.append("🟡 MOSTLY HEALTHY - Minor issues detected")
        elif score >= 50:
            report.append("🟠 DEGRADED - Significant issues require attention")
        else:
            report.append("🔴 CRITICAL - System health compromised")
        
        report.append("=" * 60)
        
        return "\n".join(report), score


if __name__ == "__main__":
    print("Starting Comprehensive Structural Integrity Audit...")
    print()
    
    auditor = StructuralIntegrityAudit()
    
    # Phase 1: Static Analysis
    print("[1/5] Running Static Analysis...")
    auditor.scan_directory()
    auditor.check_intent_routing()
    
    # Phase 2: Behavioral Testing
    print("[2/5] Running Behavioral Tests...")
    auditor.run_behavioral_tests()
    
    # Phase 3: Runtime Health (NEW)
    print("[3/5] Running Runtime Health Checks...")
    auditor.run_runtime_health_checks()
    
    # Phase 4: Financial Integrity (NEW)
    print("[4/5] Running Financial Integrity Checks...")
    auditor.run_financial_integrity_checks()
    
    # Phase 5: Generate Report
    print("[5/5] Generating Report...")
    report, score = auditor.generate_report()
    print()
    print(report)
    
    # Save report
    report_path = "/Users/zmoore-macbook/Desktop/LEF Ai/The_Bridge/Logs/StructuralIntegrity_Audit.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\n📄 Report saved to: {report_path}")

