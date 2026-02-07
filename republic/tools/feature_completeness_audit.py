#!/usr/bin/env python3
"""
Feature Completeness Audit (Phase 20 - Semantic Completeness)
================================================================
Beyond structural analysis - checks that features are ACTUALLY USED.

Catches:
- Write-Only Data: Tables/files written to but never read
- Incomplete Integrations: Functions that exist but never called
- Isolated Features: Code that stores but doesn't retrieve

Run: python3 republic/tools/feature_completeness_audit.py
"""

import os
import ast
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Project paths
BASE_DIR = Path("/Users/zmoore-macbook/Desktop/LEF Ai")
REPUBLIC_DIR = BASE_DIR / "republic"
DB_PATH = BASE_DIR / "republic.db"
LOGS_DIR = BASE_DIR / "The_Bridge" / "Logs"


class FeatureCompletenessAudit:
    """
    Audits that implemented features participate in active OODA loops.
    Identifies 'dead-end' data flows where information goes in but never comes out.
    """

    def __init__(self):
        self.issues = defaultdict(list)
        self.stats = {
            'tables_scanned': 0,
            'write_only_tables': 0,
            'functions_defined': 0,
            'functions_uncalled': 0,
            'features_incomplete': 0
        }

    def audit_database_tables(self):
        """
        Scan Python files for SQL patterns to detect write-only tables.
        A table is "write-only" if we INSERT/UPDATE but never SELECT.
        """
        table_operations = defaultdict(lambda: {'writes': [], 'reads': []})

        # Scan all Python files for SQL patterns
        for py_file in REPUBLIC_DIR.rglob("*.py"):
            try:
                content = py_file.read_text(errors='ignore')

                # Find INSERT/UPDATE statements (writes)
                insert_pattern = r"INSERT\s+INTO\s+(\w+)"
                update_pattern = r"UPDATE\s+(\w+)\s+SET"

                for match in re.finditer(insert_pattern, content, re.IGNORECASE):
                    table = match.group(1)
                    table_operations[table]['writes'].append(str(py_file.name))

                for match in re.finditer(update_pattern, content, re.IGNORECASE):
                    table = match.group(1)
                    table_operations[table]['writes'].append(str(py_file.name))

                # Find SELECT statements (reads) - handle multi-line SQL
                # Pattern handles: FROM tablename, FROM tablename alias, FROM tablename AS alias
                select_pattern = r"FROM\s+(\w+)(?:\s+(?:AS\s+)?\w+)?(?:\s|,|$)"
                for match in re.finditer(select_pattern, content, re.IGNORECASE | re.MULTILINE):
                    table = match.group(1)
                    table_operations[table]['reads'].append(str(py_file.name))

            except Exception:
                pass

        # Identify write-only tables
        for table, ops in table_operations.items():
            self.stats['tables_scanned'] += 1
            if ops['writes'] and not ops['reads']:
                self.stats['write_only_tables'] += 1
                writers = list(set(ops['writes']))[:3]  # Limit to 3 examples
                self.issues['write_only_tables'].append({
                    'table': table,
                    'writers': writers,
                    'severity': 'HIGH' if len(ops['writes']) > 2 else 'MEDIUM'
                })

    def audit_function_calls(self):
        """
        Scan for functions that are defined but never called anywhere.
        (Excluding __init__, test functions, and MixIn interface methods)
        """
        defined_functions = defaultdict(list)  # func_name -> [file_path]
        called_functions = set()

        excluded_names = {
            '__init__', '__str__', '__repr__', '__enter__', '__exit__',
            'main', 'run', 'decide', 'send', 'speak', 'on_intent',
            'setup', 'teardown', 'setUp', 'tearDown'
        }

        for py_file in REPUBLIC_DIR.rglob("*.py"):
            try:
                content = py_file.read_text(errors='ignore')
                tree = ast.parse(content)

                # Collect function definitions
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        name = node.name
                        if not name.startswith('_') or name.startswith('__'):
                            if name not in excluded_names and not name.startswith('test_'):
                                defined_functions[name].append(str(py_file.name))

                    # Collect function calls
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            called_functions.add(node.func.id)
                        elif isinstance(node.func, ast.Attribute):
                            called_functions.add(node.func.attr)

            except Exception:
                pass

        # Find functions that are defined but never called
        for func_name, files in defined_functions.items():
            self.stats['functions_defined'] += 1
            if func_name not in called_functions:
                self.stats['functions_uncalled'] += 1
                # Only flag if defined in 1 place (not an interface)
                if len(files) == 1:
                    self.issues['uncalled_functions'].append({
                        'function': func_name,
                        'file': files[0],
                        'severity': 'MEDIUM'
                    })

    def audit_skill_library(self):
        """
        Specific check: Is the skill library being both saved AND recalled?
        This is the canonical example of incomplete integration.
        """
        has_save = False
        has_recall = False

        for py_file in REPUBLIC_DIR.rglob("*.py"):
            try:
                content = py_file.read_text(errors='ignore')

                # Check for skill save patterns
                if re.search(r"INSERT\s+INTO\s+skills", content, re.IGNORECASE):
                    has_save = True

                # Check for skill recall patterns
                if re.search(r"_recall_skill|SELECT.*FROM\s+skills", content, re.IGNORECASE):
                    has_recall = True

            except Exception:
                pass

        if has_save and not has_recall:
            self.issues['incomplete_features'].append({
                'feature': 'Skill Library',
                'status': 'SAVES but never RECALLS',
                'severity': 'CRITICAL'
            })
            self.stats['features_incomplete'] += 1
        elif has_save and has_recall:
            # All good - feature is complete
            pass

    def generate_report(self):
        """Generate markdown report of feature completeness issues."""
        total_issues = (
            self.stats['write_only_tables'] +
            len(self.issues['uncalled_functions']) +
            self.stats['features_incomplete']
        )

        # Calculate Fidelity Index
        total_features = (
            self.stats['tables_scanned'] +
            self.stats['functions_defined'] +
            1  # Skill Library
        )
        active_features = total_features - total_issues
        fidelity_index = (active_features / total_features * 100) if total_features > 0 else 100

        # Determine status
        if fidelity_index >= 90:
            status = "✅ FULLY FUNCTIONAL"
        elif fidelity_index >= 70:
            status = "🟡 MOSTLY FUNCTIONAL"
        elif fidelity_index >= 50:
            status = "🟠 PARTIALLY FUNCTIONAL"
        else:
            status = "🔴 FEATURE INCOMPLETE"

        report = f"""# Feature Completeness Audit
## Phase 20: Semantic Completeness Check

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Fidelity Index**: {fidelity_index:.1f}%
**Status**: {status}

---

## Summary

| Metric | Value |
|--------|-------|
| Tables Scanned | {self.stats['tables_scanned']} |
| Write-Only Tables | {self.stats['write_only_tables']} |
| Functions Defined | {self.stats['functions_defined']} |
| Uncalled Functions | {len(self.issues['uncalled_functions'])} |
| Incomplete Features | {self.stats['features_incomplete']} |
| **Total Issues** | **{total_issues}** |

---
"""

        # Write-only tables
        if self.issues['write_only_tables']:
            report += "\n## 🗄️ Write-Only Tables\n\nData goes in but never comes out.\n\n"
            for issue in self.issues['write_only_tables']:
                report += f"- **{issue['table']}** [{issue['severity']}]\n"
                report += f"  - Writers: `{', '.join(issue['writers'])}`\n"

        # Uncalled functions
        if self.issues['uncalled_functions']:
            report += "\n## 📞 Uncalled Functions\n\nDefined but never invoked.\n\n"
            for issue in self.issues['uncalled_functions'][:10]:  # Limit display
                report += f"- `{issue['function']}()` in `{issue['file']}`\n"
            if len(self.issues['uncalled_functions']) > 10:
                report += f"\n*...and {len(self.issues['uncalled_functions']) - 10} more*\n"

        # Incomplete features
        if self.issues['incomplete_features']:
            report += "\n## ⚠️ Incomplete Features\n\nFeatures with broken data flows.\n\n"
            for issue in self.issues['incomplete_features']:
                report += f"- **{issue['feature']}**: {issue['status']} [{issue['severity']}]\n"
        else:
            report += "\n## ✅ Feature Integration\n\nSkill Library: SAVES and RECALLS - Fully integrated.\n"

        report += f"""
---

## Recommendations

1. **Write-Only Tables**: Add SELECT queries or implement consumers for stored data.
2. **Uncalled Functions**: Either wire them into the active loop or mark as `# INTENTIONAL: Reserved for Phase X`.
3. **Incomplete Features**: Ensure all data flows are bidirectional (store AND retrieve).

---

*Authored by Feature Completeness Audit*
*Fidelity Index: {fidelity_index:.1f}%*
"""
        return report, fidelity_index


if __name__ == "__main__":
    print("Starting Feature Completeness Audit...")
    print()

    auditor = FeatureCompletenessAudit()

    print("📊 Auditing database table usage...")
    auditor.audit_database_tables()

    print("📞 Auditing function call graph...")
    auditor.audit_function_calls()

    print("📚 Auditing skill library integration...")
    auditor.audit_skill_library()

    report, score = auditor.generate_report()

    # Print summary
    print()
    print("=" * 50)
    print(f"FIDELITY INDEX: {score:.1f}%")
    print("=" * 50)
    print()

    # Save report
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    report_path = LOGS_DIR / f"FeatureCompleteness_Audit_{timestamp}.md"

    with open(report_path, 'w') as f:
        f.write(report)

    print(f"📄 Report saved to: {report_path}")
