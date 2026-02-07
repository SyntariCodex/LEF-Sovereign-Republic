"""
ProjectMemory (The Long-Term Planner)
Devin-style multi-day goal tracking for LEF.

Enables LEF to maintain project context across sessions:
- Named projects with deadlines and progress tracking
- Task slicing for atomic, verifiable sub-tasks
- Progress auto-calculation from task completion
- Context injection for prompt enrichment

Usage:
    from republic.system.project_memory import get_project_memory
    
    pm = get_project_memory()
    project_id = pm.create_project("Portfolio Rebalance Q1", "Shift 20% to ETH")
    pm.add_task(project_id, "Analyze current allocation")
    pm.add_task(project_id, "Generate rebalance orders")
    pm.complete_task(task_id)
"""

import sqlite3
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any


class ProjectMemory:
    """
    Devin-style multi-day goal tracking.
    
    Maintains project context across cycles and sessions, enabling:
    - Persistent goal tracking
    - Task decomposition and progress metrics
    - Context injection for agents
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'republic.db')
        self.db_path = db_path
        self._ensure_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_tables(self):
        """Create projects and project_tasks tables if not exist."""
        conn = self._get_connection()
        try:
            # Projects table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    status TEXT DEFAULT 'ACTIVE',
                    priority INTEGER DEFAULT 50,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    target_date TIMESTAMP,
                    completed_at TIMESTAMP,
                    progress_pct REAL DEFAULT 0,
                    owner_agent TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_status 
                ON projects(status)
            """)
            
            # Project tasks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    assigned_agent TEXT,
                    notes TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_project 
                ON project_tasks(project_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_status 
                ON project_tasks(status)
            """)
            
            conn.commit()
            logging.debug("[PROJECT_MEMORY] 📋 Tables ready.")
        finally:
            conn.close()
    
    def create_project(
        self,
        name: str,
        description: str = None,
        target_date: str = None,
        owner_agent: str = None,
        priority: int = 50,
        metadata: Dict = None
    ) -> int:
        """
        Create a new project (long-term goal).
        
        Args:
            name: Unique project name
            description: What this project aims to achieve
            target_date: Optional deadline (ISO format)
            owner_agent: Which agent owns this project
            priority: 1-100 (higher = more important)
            metadata: Additional JSON data
            
        Returns:
            Project ID
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO projects (name, description, target_date, owner_agent, priority, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                description,
                target_date,
                owner_agent,
                priority,
                json.dumps(metadata) if metadata else None
            ))
            conn.commit()
            project_id = cursor.lastrowid
            logging.info(f"[PROJECT_MEMORY] 📋 Created project '{name}' (ID: {project_id})")
            return project_id
        finally:
            conn.close()
    
    def add_task(
        self,
        project_id: int,
        title: str,
        assigned_agent: str = None,
        notes: str = None
    ) -> int:
        """
        Add a task to a project (task slicing).
        
        Args:
            project_id: Parent project
            title: What needs to be done
            assigned_agent: Which agent should handle this
            notes: Additional context
            
        Returns:
            Task ID
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO project_tasks (project_id, title, assigned_agent, notes)
                VALUES (?, ?, ?, ?)
            """, (project_id, title, assigned_agent, notes))
            conn.commit()
            task_id = cursor.lastrowid
            logging.debug(f"[PROJECT_MEMORY] ➕ Added task '{title}' to project {project_id}")
            return task_id
        finally:
            conn.close()
    
    def complete_task(self, task_id: int, notes: str = None):
        """Mark a task as complete and update project progress."""
        conn = self._get_connection()
        try:
            # Update task
            conn.execute("""
                UPDATE project_tasks 
                SET status = 'DONE', completed_at = CURRENT_TIMESTAMP, notes = COALESCE(?, notes)
                WHERE id = ?
            """, (notes, task_id))
            
            # Get project ID
            cursor = conn.execute("SELECT project_id FROM project_tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                project_id = row[0]
                self._update_progress(conn, project_id)
            
            conn.commit()
            logging.info(f"[PROJECT_MEMORY] ✅ Task {task_id} completed")
        finally:
            conn.close()
    
    def start_task(self, task_id: int):
        """Mark a task as in progress."""
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE project_tasks SET status = 'IN_PROGRESS' WHERE id = ?
            """, (task_id,))
            conn.commit()
        finally:
            conn.close()
    
    def block_task(self, task_id: int, reason: str):
        """Mark a task as blocked."""
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE project_tasks SET status = 'BLOCKED', notes = ? WHERE id = ?
            """, (reason, task_id))
            conn.commit()
        finally:
            conn.close()
    
    def _update_progress(self, conn, project_id: int):
        """Auto-calculate project progress from task completion."""
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'DONE' THEN 1 ELSE 0 END) as done
            FROM project_tasks 
            WHERE project_id = ?
        """, (project_id,))
        row = cursor.fetchone()
        
        if row and row['total'] > 0:
            progress = (row['done'] / row['total']) * 100
            conn.execute("""
                UPDATE projects SET progress_pct = ? WHERE id = ?
            """, (progress, project_id))
            
            # Auto-complete project if all tasks done
            if progress >= 100:
                conn.execute("""
                    UPDATE projects 
                    SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (project_id,))
                logging.info(f"[PROJECT_MEMORY] 🎉 Project {project_id} completed!")
    
    def get_active_projects(self) -> List[Dict]:
        """Get all active projects with progress info."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT p.*, 
                    (SELECT COUNT(*) FROM project_tasks WHERE project_id = p.id) as total_tasks,
                    (SELECT COUNT(*) FROM project_tasks WHERE project_id = p.id AND status = 'DONE') as done_tasks,
                    (SELECT COUNT(*) FROM project_tasks WHERE project_id = p.id AND status = 'BLOCKED') as blocked_tasks
                FROM projects p
                WHERE p.status = 'ACTIVE'
                ORDER BY p.priority DESC, p.created_at ASC
            """)
            
            projects = []
            for row in cursor.fetchall():
                projects.append({
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'priority': row['priority'],
                    'progress_pct': row['progress_pct'],
                    'target_date': row['target_date'],
                    'owner_agent': row['owner_agent'],
                    'total_tasks': row['total_tasks'],
                    'done_tasks': row['done_tasks'],
                    'blocked_tasks': row['blocked_tasks']
                })
            
            return projects
        finally:
            conn.close()
    
    def get_project_context(self, project_id: int) -> Dict:
        """
        Get full project context for prompt injection.
        
        Returns dict with project info, all tasks, and recent activity.
        """
        conn = self._get_connection()
        try:
            # Get project
            cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            project = cursor.fetchone()
            if not project:
                return {}
            
            # Get tasks
            cursor = conn.execute("""
                SELECT * FROM project_tasks 
                WHERE project_id = ? 
                ORDER BY status = 'IN_PROGRESS' DESC, status = 'PENDING' DESC, created_at ASC
            """, (project_id,))
            tasks = [dict(row) for row in cursor.fetchall()]
            
            return {
                'project': dict(project),
                'tasks': tasks,
                'pending': [t for t in tasks if t['status'] == 'PENDING'],
                'in_progress': [t for t in tasks if t['status'] == 'IN_PROGRESS'],
                'done': [t for t in tasks if t['status'] == 'DONE'],
                'blocked': [t for t in tasks if t['status'] == 'BLOCKED']
            }
        finally:
            conn.close()
    
    def get_next_tasks(self, agent_name: str = None, limit: int = 5) -> List[Dict]:
        """
        Get next tasks for an agent to work on.
        
        Prioritizes:
        1. IN_PROGRESS tasks (resume work)
        2. PENDING tasks from high-priority projects
        """
        conn = self._get_connection()
        try:
            if agent_name:
                cursor = conn.execute("""
                    SELECT t.*, p.name as project_name, p.priority as project_priority
                    FROM project_tasks t
                    JOIN projects p ON t.project_id = p.id
                    WHERE t.status IN ('PENDING', 'IN_PROGRESS')
                    AND p.status = 'ACTIVE'
                    AND (t.assigned_agent = ? OR t.assigned_agent IS NULL)
                    ORDER BY t.status = 'IN_PROGRESS' DESC, p.priority DESC
                    LIMIT ?
                """, (agent_name, limit))
            else:
                cursor = conn.execute("""
                    SELECT t.*, p.name as project_name, p.priority as project_priority
                    FROM project_tasks t
                    JOIN projects p ON t.project_id = p.id
                    WHERE t.status IN ('PENDING', 'IN_PROGRESS')
                    AND p.status = 'ACTIVE'
                    ORDER BY t.status = 'IN_PROGRESS' DESC, p.priority DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_context_for_prompt(self) -> str:
        """Generate context string for prompt injection."""
        projects = self.get_active_projects()
        
        if not projects:
            return ""
        
        context = "\n### Active Projects\n"
        for p in projects[:5]:  # Top 5 by priority
            progress_bar = "█" * int(p['progress_pct'] / 10) + "░" * (10 - int(p['progress_pct'] / 10))
            context += f"- **{p['name']}** [{progress_bar}] {p['progress_pct']:.0f}%"
            if p['blocked_tasks'] > 0:
                context += f" ⚠️ {p['blocked_tasks']} blocked"
            context += "\n"
        
        return context
    
    def complete_project(self, project_id: int):
        """Manually mark a project as complete."""
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE projects 
                SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP, progress_pct = 100
                WHERE id = ?
            """, (project_id,))
            conn.commit()
        finally:
            conn.close()
    
    def pause_project(self, project_id: int):
        """Pause a project."""
        conn = self._get_connection()
        try:
            conn.execute("UPDATE projects SET status = 'PAUSED' WHERE id = ?", (project_id,))
            conn.commit()
        finally:
            conn.close()
    
    def resume_project(self, project_id: int):
        """Resume a paused project."""
        conn = self._get_connection()
        try:
            conn.execute("UPDATE projects SET status = 'ACTIVE' WHERE id = ?", (project_id,))
            conn.commit()
        finally:
            conn.close()
    
    def get_stats(self) -> Dict:
        """Get project memory statistics."""
        conn = self._get_connection()
        try:
            stats = {}
            
            # Project counts by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count FROM projects GROUP BY status
            """)
            stats['projects_by_status'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Task counts
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count FROM project_tasks GROUP BY status
            """)
            stats['tasks_by_status'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Average progress of active projects
            cursor = conn.execute("""
                SELECT AVG(progress_pct) FROM projects WHERE status = 'ACTIVE'
            """)
            row = cursor.fetchone()
            stats['avg_active_progress'] = round(row[0], 1) if row[0] else 0
            
            return stats
        finally:
            conn.close()


# Singleton instance
_memory = None

def get_project_memory(db_path: str = None) -> ProjectMemory:
    """Get or create the singleton ProjectMemory."""
    global _memory
    if _memory is None:
        _memory = ProjectMemory(db_path)
    return _memory


# Self-test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("PROJECT MEMORY - Self Test")
    print("=" * 60)
    
    pm = get_project_memory()
    
    # Create test project
    print("\nCreating test project...")
    try:
        project_id = pm.create_project(
            "Test Project Memory",
            "Verify the project tracking system works",
            owner_agent="TestAgent"
        )
    except sqlite3.IntegrityError:
        # Project already exists
        conn = pm._get_connection()
        cursor = conn.execute("SELECT id FROM projects WHERE name = 'Test Project Memory'")
        project_id = cursor.fetchone()[0]
        conn.close()
        print(f"Using existing project: {project_id}")
    
    # Add tasks
    print("Adding tasks...")
    task1 = pm.add_task(project_id, "Create tables")
    task2 = pm.add_task(project_id, "Write ProjectMemory class")
    task3 = pm.add_task(project_id, "Test integration")
    
    # Complete some tasks
    print("Completing tasks...")
    pm.complete_task(task1)
    pm.start_task(task2)
    
    # Get active projects
    projects = pm.get_active_projects()
    print(f"\nActive projects: {len(projects)}")
    for p in projects:
        print(f"  - {p['name']}: {p['progress_pct']:.0f}% ({p['done_tasks']}/{p['total_tasks']} tasks)")
    
    # Get context for prompt
    context = pm.get_context_for_prompt()
    print(f"\nContext for prompt:\n{context}")
    
    # Show stats
    stats = pm.get_stats()
    print(f"\nStats: {stats}")
    
    print("\n" + "=" * 60)
    print("✅ Self-test complete")
