"""
Directory Scanner with Throttling

Provides throttled directory scanning to prevent file handle exhaustion
when multiple agents scan the same directories simultaneously.

Usage:
    from system.directory_scanner import list_dir_throttled
    
    files = list_dir_throttled('/path/to/governance/house')
"""

import os
import threading
import logging

# Semaphore limits concurrent directory scans
_scan_semaphore = threading.Semaphore(3)  # Max 3 concurrent scans

logger = logging.getLogger(__name__)


def list_dir_throttled(path: str, filter_ext: str = None) -> list:
    """
    List directory contents with concurrency throttling.
    
    Args:
        path: Directory path to scan
        filter_ext: Optional extension filter (e.g., '.json')
        
    Returns:
        List of filenames in directory
    """
    with _scan_semaphore:
        try:
            if not os.path.exists(path):
                return []
            
            files = os.listdir(path)
            
            if filter_ext:
                files = [f for f in files if f.endswith(filter_ext)]
            
            return files
        except OSError as e:
            logger.warning(f"[SCANNER] Directory scan failed for {path}: {e}")
            return []


def list_json_files(path: str) -> list:
    """Convenience function to list only .json files."""
    return list_dir_throttled(path, filter_ext='.json')


def walk_dir_throttled(path: str, filter_ext: str = None, max_depth: int = 10):
    """
    Walk directory tree with throttling to prevent file handle exhaustion.
    
    Args:
        path: Root directory path to walk
        filter_ext: Optional extension filter (e.g., '.md')
        max_depth: Maximum recursion depth (default 10)
        
    Yields:
        Tuples of (root, dirs, files) like os.walk, but throttled
    """
    if not os.path.exists(path):
        return
        
    def _walk_recursive(current_path, depth=0):
        if depth > max_depth:
            return
            
        with _scan_semaphore:
            try:
                entries = os.listdir(current_path)
            except OSError as e:
                logger.warning(f"[SCANNER] Walk failed for {current_path}: {e}")
                return
        
        dirs = []
        files = []
        
        for entry in entries:
            full_path = os.path.join(current_path, entry)
            if os.path.isdir(full_path):
                dirs.append(entry)
            else:
                if filter_ext is None or entry.endswith(filter_ext):
                    files.append(entry)
        
        yield current_path, dirs, files
        
        for d in dirs:
            yield from _walk_recursive(os.path.join(current_path, d), depth + 1)
    
    yield from _walk_recursive(path)


def count_files(path: str, filter_ext: str = None) -> int:
    """Count files in directory without returning full list."""
    return len(list_dir_throttled(path, filter_ext))
