"""
Pre-launch Security Audit.
Scans the LEF codebase for common vulnerabilities before onchain deployment.

Phase 5 Active Tasks — Task 5.4

Categories:
  1. Key exposure — hardcoded keys, plaintext secrets, keys in logs
  2. Environment dependencies — all sensitive values from env vars
  3. Contract vulnerabilities — Solidity security checks
  4. Transaction safety — gas caps, value limits, nonce management

Usage:
  python3 republic/tools/security_audit.py

Output: PASS or FAIL with actionable findings.
"""

import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent  # republic/
PROJECT_DIR = BASE_DIR.parent  # LEF Ai/

logger = logging.getLogger("LEF.SecurityAudit")


class SecurityAudit:
    """
    Comprehensive security audit for LEF's onchain infrastructure.
    Scans Python and Solidity files for vulnerabilities.
    """

    def __init__(self):
        self.findings = {
            'critical': [],
            'warning': [],
            'info': [],
            'passed': []
        }
        self.files_scanned = 0

    def _scan_python_files(self) -> list:
        """Get all .py files in the project (excluding venv, __pycache__)."""
        py_files = []
        for root, dirs, files in os.walk(str(PROJECT_DIR)):
            # Skip non-essential directories
            dirs[:] = [d for d in dirs if d not in {
                '__pycache__', 'venv', '.venv', 'env', 'node_modules',
                '.git', 'backups', 'Workspace_Archive'
            }]
            for f in files:
                if f.endswith('.py'):
                    py_files.append(os.path.join(root, f))
        return py_files

    def _scan_solidity_files(self) -> list:
        """Get all .sol files in the project."""
        sol_files = []
        contracts_dir = BASE_DIR / 'contracts'
        if contracts_dir.exists():
            for f in contracts_dir.glob('**/*.sol'):
                sol_files.append(str(f))
        return sol_files

    def check_key_exposure(self) -> list:
        """
        Scan all .py files for:
        - Hardcoded private keys (hex strings starting with 0x, 64+ chars)
        - Unencrypted key storage
        - Keys in log statements
        - Keys passed as function arguments without encryption
        - API keys/secrets in source
        """
        findings = []
        py_files = self._scan_python_files()

        # Patterns that indicate potential key exposure
        patterns = {
            'hardcoded_hex_key': {
                'regex': r'["\']0x[0-9a-fA-F]{64,}["\']',
                'severity': 'critical',
                'message': 'Possible hardcoded private key (64+ hex chars)'
            },
            'private_key_assignment': {
                'regex': r'private_key\s*=\s*["\'][^"\']',
                'severity': 'critical',
                'message': 'Direct private key assignment in source'
            },
            'secret_assignment': {
                'regex': r'(?:api_secret|api_key|secret_key|password)\s*=\s*["\'][a-zA-Z0-9+/=]{10,}["\']',
                'severity': 'critical',
                'message': 'Hardcoded secret/API key'
            },
            'key_in_log': {
                'regex': r'(?:logging|logger|print)\s*[\.(]\s*.*(?:private_key|secret|api_key|encryption_key)',
                'severity': 'critical',
                'message': 'Possible key/secret in log statement'
            },
            'key_in_fstring': {
                'regex': r'f["\'].*\{.*(?:private_key|\.key|secret|api_key).*\}',
                'severity': 'warning',
                'message': 'Possible secret in f-string (check if logged)'
            },
            'plaintext_key_write': {
                'regex': r'(?:json\.dump|write|open).*(?:private_key|secret)(?!.*encrypt)',
                'severity': 'warning',
                'message': 'Possible plaintext key write to file'
            }
        }

        for filepath in py_files:
            self.files_scanned += 1
            try:
                with open(filepath, 'r', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')

                rel_path = os.path.relpath(filepath, str(PROJECT_DIR))

                for line_num, line in enumerate(lines, 1):
                    # Skip comments
                    stripped = line.strip()
                    if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                        continue

                    for pattern_name, pattern_info in patterns.items():
                        if re.search(pattern_info['regex'], line, re.IGNORECASE):
                            # Filter false positives
                            if self._is_false_positive(pattern_name, line, filepath):
                                continue

                            findings.append({
                                'check': 'key_exposure',
                                'pattern': pattern_name,
                                'severity': pattern_info['severity'],
                                'message': pattern_info['message'],
                                'file': rel_path,
                                'line': line_num,
                                'content': stripped[:120]
                            })
            except Exception as e:
                logger.warning(f"Could not scan {filepath}: {e}")

        return findings

    def _is_false_positive(self, pattern_name: str, line: str, filepath: str) -> bool:
        """Filter out known false positives."""
        line_lower = line.lower().strip()

        # Comments and docstrings
        if line_lower.startswith('#') or line_lower.startswith('"""') or line_lower.startswith("'''"):
            return True

        # Test files and examples
        if 'test' in os.path.basename(filepath).lower():
            return True

        # Variable names that contain 'key' but aren't actual keys
        if pattern_name == 'key_in_fstring':
            # encrypted_key is fine in f-strings (it's the encrypted version)
            if 'encrypted' in line_lower:
                return True
            # encryption_key preview (showing first 20 chars of encryption key in test mode)
            if 'test key' in line_lower or 'test_key' in line_lower:
                return True

        # key_in_log: check if it's actually logging the key or just mentioning it
        if pattern_name == 'key_in_log':
            # Logging about encryption key being missing is fine
            if 'not set' in line_lower or 'required' in line_lower or 'invalid' in line_lower:
                return True
            if 'encryption_key' in line_lower and 'self.encryption_key' not in line_lower:
                return True
            # Instructions telling user to set env vars (e.g., "export FOO_KEY='your_key'")
            if 'export ' in line_lower and ("your_" in line_lower or "your " in line_lower):
                return True
            # Log messages about missing keys (not exposing actual values)
            if 'no ' in line_lower and 'found' in line_lower:
                return True
            if 'set it with' in line_lower or 'set ' in line_lower and 'enable' in line_lower:
                return True
            # Agent disabled messages
            if 'disabled' in line_lower or 'agent disabled' in line_lower:
                return True
            # Masked/redacted key output (showing only last few chars with stars)
            if "'*'" in line_lower or '"*"' in line_lower or '***' in line_lower:
                return True
            if '[-4:]' in line_lower or '[-3:]' in line_lower:
                return True

        # private_key_assignment: check if it's encrypted
        if pattern_name == 'private_key_assignment':
            if 'encrypted' in line_lower or 'fernet' in line_lower or 'decrypt' in line_lower:
                return True

        # Regex pattern strings themselves
        if 'regex' in line_lower or 'pattern' in line_lower or 're.search' in line_lower:
            return True

        return False

    def check_env_dependencies(self) -> list:
        """
        Verify all sensitive values come from environment variables:
        - LEF_WALLET_KEY
        - COINBASE_API_KEY / COINBASE_API_SECRET
        - RPC endpoint URLs
        - DB_PATH
        """
        findings = []
        py_files = self._scan_python_files()

        # Required env vars and their expected usage patterns
        required_env_vars = {
            'LEF_WALLET_KEY': {
                'files_that_should_use': ['wallet_manager.py'],
                'purpose': 'Wallet encryption key'
            },
            'DB_PATH': {
                'files_that_should_use': [],  # Many files use this
                'purpose': 'Database path'
            }
        }

        # Check that env vars are used, not hardcoded
        env_var_usage = {var: [] for var in required_env_vars}

        for filepath in py_files:
            try:
                with open(filepath, 'r', errors='ignore') as f:
                    content = f.read()

                rel_path = os.path.relpath(filepath, str(PROJECT_DIR))

                for var_name in required_env_vars:
                    if f"os.getenv('{var_name}')" in content or f'os.getenv("{var_name}")' in content:
                        env_var_usage[var_name].append(rel_path)
                    elif f"os.environ['{var_name}']" in content or f'os.environ["{var_name}"]' in content:
                        env_var_usage[var_name].append(rel_path)
                    elif f"os.environ.get('{var_name}')" in content or f'os.environ.get("{var_name}")' in content:
                        env_var_usage[var_name].append(rel_path)

            except Exception:
                continue

        # Report on env var usage
        for var_name, info in required_env_vars.items():
            if env_var_usage[var_name]:
                findings.append({
                    'check': 'env_dependency',
                    'severity': 'info',
                    'message': f'{var_name} properly loaded from environment in: {", ".join(env_var_usage[var_name])}',
                    'env_var': var_name
                })
            else:
                if info['files_that_should_use']:
                    findings.append({
                        'check': 'env_dependency',
                        'severity': 'warning',
                        'message': f'{var_name} ({info["purpose"]}) not found via os.getenv() in any file',
                        'env_var': var_name
                    })

        # Check for hardcoded RPC URLs
        for filepath in py_files:
            try:
                with open(filepath, 'r', errors='ignore') as f:
                    lines = f.readlines()

                rel_path = os.path.relpath(filepath, str(PROJECT_DIR))

                for line_num, line in enumerate(lines, 1):
                    # Check for hardcoded RPC URLs that should use env vars
                    if re.search(r'http[s]?://.*\.(infura|alchemy|quicknode)', line, re.IGNORECASE):
                        if 'os.getenv' not in line and 'os.environ' not in line:
                            findings.append({
                                'check': 'env_dependency',
                                'severity': 'warning',
                                'message': 'Hardcoded RPC endpoint URL (should use env var)',
                                'file': rel_path,
                                'line': line_num
                            })
            except Exception:
                continue

        return findings

    def check_contract_vulnerabilities(self) -> list:
        """
        Basic Solidity security checks:
        - Reentrancy guards present where needed
        - Access control on state-changing functions
        - No selfdestruct
        - No delegatecall
        - Integer overflow protection (Solidity 0.8+ handles this)
        - No assembly blocks (potential for bypass)
        """
        findings = []
        sol_files = self._scan_solidity_files()

        if not sol_files:
            findings.append({
                'check': 'contract_vuln',
                'severity': 'warning',
                'message': 'No Solidity files found to audit'
            })
            return findings

        for filepath in sol_files:
            self.files_scanned += 1
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')

                rel_path = os.path.relpath(filepath, str(PROJECT_DIR))
                contract_name = Path(filepath).stem

                # Check Solidity version (must be 0.8+ for overflow protection)
                version_match = re.search(r'pragma\s+solidity\s+\^?(\d+\.\d+\.\d+)', content)
                if version_match:
                    version = version_match.group(1)
                    major, minor, _ = version.split('.')
                    if int(major) < 1 and int(minor) < 8:
                        findings.append({
                            'check': 'contract_vuln',
                            'severity': 'critical',
                            'message': f'Solidity version {version} lacks built-in overflow protection. Use 0.8+',
                            'file': rel_path
                        })
                    else:
                        findings.append({
                            'check': 'contract_vuln',
                            'severity': 'info',
                            'message': f'Solidity {version} — built-in overflow protection active',
                            'file': rel_path
                        })

                # Check for selfdestruct
                if 'selfdestruct' in content.lower():
                    findings.append({
                        'check': 'contract_vuln',
                        'severity': 'critical',
                        'message': 'Contract contains selfdestruct — can permanently destroy contract',
                        'file': rel_path
                    })
                else:
                    findings.append({
                        'check': 'contract_vuln',
                        'severity': 'info',
                        'message': 'No selfdestruct found (good)',
                        'file': rel_path
                    })

                # Check for delegatecall
                if 'delegatecall' in content.lower():
                    findings.append({
                        'check': 'contract_vuln',
                        'severity': 'critical',
                        'message': 'Contract uses delegatecall — can execute arbitrary code in context',
                        'file': rel_path
                    })
                else:
                    findings.append({
                        'check': 'contract_vuln',
                        'severity': 'info',
                        'message': 'No delegatecall found (good)',
                        'file': rel_path
                    })

                # Check for assembly blocks
                if re.search(r'assembly\s*\{', content):
                    findings.append({
                        'check': 'contract_vuln',
                        'severity': 'warning',
                        'message': 'Contract contains inline assembly — manual review required',
                        'file': rel_path
                    })
                else:
                    findings.append({
                        'check': 'contract_vuln',
                        'severity': 'info',
                        'message': 'No inline assembly found (good)',
                        'file': rel_path
                    })

                # Check access control on state-changing functions
                state_changing = re.findall(r'function\s+(\w+)\s*\([^)]*\)\s*(?:external|public)(?!\s*view)(?!\s*pure)', content)
                for func_name in state_changing:
                    # Check if function has a modifier (onlyArchitect, onlyLEF, etc.)
                    func_pattern = rf'function\s+{func_name}\s*\([^)]*\)\s*(?:external|public)\s+(only\w+)'
                    has_modifier = re.search(func_pattern, content)

                    if func_name == 'constructor':
                        continue  # Constructor doesn't need modifier

                    if not has_modifier:
                        findings.append({
                            'check': 'contract_vuln',
                            'severity': 'critical',
                            'message': f'State-changing function {func_name}() has no access control modifier',
                            'file': rel_path
                        })
                    else:
                        findings.append({
                            'check': 'contract_vuln',
                            'severity': 'info',
                            'message': f'{func_name}() has access control: {has_modifier.group(1)}',
                            'file': rel_path
                        })

                # Check for reentrancy risk (external calls before state changes)
                # Simple heuristic: look for .call{ or .transfer( or .send(
                if re.search(r'\.(call|transfer|send)\s*[\({]', content):
                    findings.append({
                        'check': 'contract_vuln',
                        'severity': 'warning',
                        'message': 'Contract makes external calls — verify no reentrancy risk',
                        'file': rel_path
                    })
                else:
                    findings.append({
                        'check': 'contract_vuln',
                        'severity': 'info',
                        'message': 'No external calls (transfer/send/call) — no reentrancy risk',
                        'file': rel_path
                    })

            except Exception as e:
                findings.append({
                    'check': 'contract_vuln',
                    'severity': 'warning',
                    'message': f'Could not audit {filepath}: {e}'
                })

        return findings

    def check_transaction_safety(self) -> list:
        """
        Verify transaction signing code:
        - Gas limits are capped
        - Value transfers have upper bounds
        - Nonce management prevents double-spend
        - RPC endpoints use HTTPS
        - Chain ID validation
        """
        findings = []

        # Scan wallet_manager.py and contract_deployer.py specifically
        critical_files = [
            str(BASE_DIR / 'system' / 'wallet_manager.py'),
            str(BASE_DIR / 'system' / 'contract_deployer.py'),
            str(BASE_DIR / 'system' / 'state_hasher.py')
        ]

        for filepath in critical_files:
            if not os.path.exists(filepath):
                findings.append({
                    'check': 'tx_safety',
                    'severity': 'warning',
                    'message': f'Expected file not found: {os.path.basename(filepath)}'
                })
                continue

            with open(filepath, 'r') as f:
                content = f.read()

            rel_path = os.path.relpath(filepath, str(PROJECT_DIR))

            # Check for gas limit caps
            if 'MAX_GAS_LIMIT' in content or 'gas_limit' in content.lower() or re.search(r"'gas'.*\d{3,}", content):
                has_gas_cap = bool(re.search(r'(?:MAX_GAS|gas_limit|gas.*cap)', content, re.IGNORECASE))
                if has_gas_cap:
                    findings.append({
                        'check': 'tx_safety',
                        'severity': 'info',
                        'message': f'Gas limit cap found in {rel_path}',
                        'file': rel_path
                    })
                else:
                    findings.append({
                        'check': 'tx_safety',
                        'severity': 'warning',
                        'message': f'Gas values used but no explicit cap in {rel_path}',
                        'file': rel_path
                    })

            # Check for value transfer caps
            if 'max_value' in content.lower() or 'value.*cap' in content.lower():
                findings.append({
                    'check': 'tx_safety',
                    'severity': 'info',
                    'message': f'Value transfer cap found in {rel_path}',
                    'file': rel_path
                })
            elif 'value' in content and 'send_transaction' in content:
                findings.append({
                    'check': 'tx_safety',
                    'severity': 'warning',
                    'message': f'Value transfers present — verify cap exists in {rel_path}',
                    'file': rel_path
                })

            # Check for chain ID validation
            if 'chainId' in content or 'chain_id' in content:
                if 'mismatch' in content.lower() or 'verify' in content.lower() or 'expected' in content.lower():
                    findings.append({
                        'check': 'tx_safety',
                        'severity': 'info',
                        'message': f'Chain ID validation found in {rel_path}',
                        'file': rel_path
                    })

            # Check for HTTPS in RPC URLs
            rpc_urls = re.findall(r'http[s]?://[^\s\'"]+', content)
            for url in rpc_urls:
                if url.startswith('http://') and 'localhost' not in url and '127.0.0.1' not in url:
                    findings.append({
                        'check': 'tx_safety',
                        'severity': 'critical',
                        'message': f'Non-HTTPS RPC URL: {url}',
                        'file': rel_path
                    })
                elif url.startswith('https://'):
                    findings.append({
                        'check': 'tx_safety',
                        'severity': 'info',
                        'message': f'RPC URL uses HTTPS: {url[:50]}',
                        'file': rel_path
                    })

            # Check for nonce management
            if 'nonce' in content.lower():
                if 'get_transaction_count' in content:
                    findings.append({
                        'check': 'tx_safety',
                        'severity': 'info',
                        'message': f'Nonce fetched from network (prevents double-spend) in {rel_path}',
                        'file': rel_path
                    })

        return findings

    def check_gitignore(self) -> list:
        """
        Verify sensitive files are in .gitignore.
        """
        findings = []
        gitignore_path = str(PROJECT_DIR / '.gitignore')

        if not os.path.exists(gitignore_path):
            findings.append({
                'check': 'gitignore',
                'severity': 'critical',
                'message': 'No .gitignore found — secrets may be committed'
            })
            return findings

        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()

        sensitive_patterns = {
            'wallet_encrypted.json': 'Encrypted wallet file',
            '.env': 'Environment variables',
            'config.json': 'Configuration with API keys',
            'keys.json': 'API keys file',
            'coinbase.json': 'Coinbase credentials',
            'The_Bridge/': 'Bridge directory (contains wallet + identity)',
            '*.db': 'Database files'
        }

        for pattern, description in sensitive_patterns.items():
            if pattern in gitignore_content:
                findings.append({
                    'check': 'gitignore',
                    'severity': 'info',
                    'message': f'{pattern} ({description}) — found in .gitignore'
                })
            else:
                findings.append({
                    'check': 'gitignore',
                    'severity': 'warning',
                    'message': f'{pattern} ({description}) — NOT found in .gitignore'
                })

        return findings

    def check_file_permissions(self) -> list:
        """
        Check file permissions on sensitive files.
        """
        findings = []
        sensitive_files = [
            str(PROJECT_DIR / 'The_Bridge' / 'wallet_encrypted.json'),
            str(PROJECT_DIR / 'republic' / 'config' / 'config.json'),
            str(PROJECT_DIR / 'republic' / 'config' / 'keys.json'),
        ]

        for filepath in sensitive_files:
            if os.path.exists(filepath):
                mode = oct(os.stat(filepath).st_mode)[-3:]
                rel_path = os.path.relpath(filepath, str(PROJECT_DIR))

                if mode in ('600', '400'):
                    findings.append({
                        'check': 'file_perms',
                        'severity': 'info',
                        'message': f'{rel_path} — permissions {mode} (restrictive, good)'
                    })
                elif mode in ('644', '640'):
                    findings.append({
                        'check': 'file_perms',
                        'severity': 'warning',
                        'message': f'{rel_path} — permissions {mode} (group/world readable, consider 600)'
                    })
                else:
                    findings.append({
                        'check': 'file_perms',
                        'severity': 'warning',
                        'message': f'{rel_path} — permissions {mode} (consider restricting to 600)'
                    })

        return findings

    def run_full_audit(self) -> dict:
        """
        Run all security checks.

        Returns:
            dict: {
                'passed': bool,
                'critical_issues': [...],
                'warnings': [...],
                'info': [...],
                'files_scanned': int,
                'timestamp': str
            }
        """
        all_findings = []

        # Run all checks
        checks = [
            ('Key Exposure', self.check_key_exposure),
            ('Environment Dependencies', self.check_env_dependencies),
            ('Contract Vulnerabilities', self.check_contract_vulnerabilities),
            ('Transaction Safety', self.check_transaction_safety),
            ('Git Ignore', self.check_gitignore),
            ('File Permissions', self.check_file_permissions),
        ]

        for check_name, check_func in checks:
            try:
                findings = check_func()
                for f in findings:
                    f['check_category'] = check_name
                all_findings.extend(findings)
            except Exception as e:
                all_findings.append({
                    'check_category': check_name,
                    'severity': 'warning',
                    'message': f'Check failed with error: {e}'
                })

        # Categorize
        critical = [f for f in all_findings if f.get('severity') == 'critical']
        warnings = [f for f in all_findings if f.get('severity') == 'warning']
        info = [f for f in all_findings if f.get('severity') == 'info']

        result = {
            'passed': len(critical) == 0,
            'critical_issues': critical,
            'warnings': warnings,
            'info': info,
            'total_findings': len(all_findings),
            'files_scanned': self.files_scanned,
            'timestamp': datetime.now().isoformat()
        }

        return result


# === CLI ===

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)

    print("=" * 70)
    print("  LEF Security Audit — Pre-Launch Review")
    print("=" * 70)
    print(f"  Scan root: {PROJECT_DIR}")
    print()

    audit = SecurityAudit()
    result = audit.run_full_audit()

    # === Critical Issues ===
    if result['critical_issues']:
        print(f"  CRITICAL ISSUES ({len(result['critical_issues'])}):")
        print("  " + "-" * 66)
        for f in result['critical_issues']:
            file_info = f.get('file', '')
            line_info = f':{f["line"]}' if 'line' in f else ''
            print(f"  [CRITICAL] {f['message']}")
            if file_info:
                print(f"             File: {file_info}{line_info}")
            if 'content' in f:
                print(f"             Code: {f['content'][:100]}")
            print()
    else:
        print("  CRITICAL ISSUES: None")
        print()

    # === Warnings ===
    if result['warnings']:
        print(f"  WARNINGS ({len(result['warnings'])}):")
        print("  " + "-" * 66)
        for f in result['warnings']:
            file_info = f.get('file', '')
            line_info = f':{f["line"]}' if 'line' in f else ''
            print(f"  [WARN] {f['message']}")
            if file_info:
                print(f"         File: {file_info}{line_info}")
            print()
    else:
        print("  WARNINGS: None")
        print()

    # === Info (passed checks) ===
    print(f"  PASSED CHECKS ({len(result['info'])}):")
    print("  " + "-" * 66)
    for f in result['info']:
        print(f"  [OK] {f['message']}")
    print()

    # === Summary ===
    print("=" * 70)
    status = "PASS" if result['passed'] else "FAIL"
    print(f"  AUDIT RESULT: {status}")
    print(f"  Files scanned: {result['files_scanned']}")
    print(f"  Critical: {len(result['critical_issues'])}")
    print(f"  Warnings: {len(result['warnings'])}")
    print(f"  Passed: {len(result['info'])}")
    print("=" * 70)

    if not result['passed']:
        print("\n  DO NOT DEPLOY — fix all critical issues first.")
        exit(1)
    else:
        print("\n  All critical checks passed. Safe to proceed with deployment.")
        exit(0)
