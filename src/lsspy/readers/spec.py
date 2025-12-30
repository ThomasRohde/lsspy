"""YAML spec file reader."""

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from lsspy.models import Task


class SpecReader:
    """Read data from spec.yaml."""

    def __init__(self, spec_path: Path) -> None:
        """Initialize the reader.

        Args:
            spec_path: Path to spec.yaml file
        """
        self.spec_path = spec_path

    def read(self) -> dict[str, Any]:
        """Read the spec file.

        Returns:
            Parsed YAML data

        Raises:
            FileNotFoundError: If spec file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        if not self.spec_path.exists():
            raise FileNotFoundError(f"Spec file not found: {self.spec_path}")

        with open(self.spec_path) as f:
            data = yaml.safe_load(f)
            return data if data is not None else {}

    def read_safe(self) -> dict[str, Any]:
        """Read the spec file with error handling.

        Returns:
            Parsed YAML data or empty dict on error
        """
        try:
            return self.read()
        except (OSError, FileNotFoundError, yaml.YAMLError):
            return {}

    def get_tasks(self) -> list[dict[str, Any]]:
        """Get all tasks from spec as dictionaries.

        Returns:
            List of task dictionaries
        """
        spec = self.read_safe()
        tasks_dict = spec.get("tasks", {})

        # Convert dict of tasks to list, adding ID from key
        if isinstance(tasks_dict, dict):
            return [{"id": task_id, **task_data} for task_id, task_data in tasks_dict.items()]
        return []

    def get_tasks_typed(self) -> list[Task]:
        """Get all tasks from spec as typed Task objects.

        Returns:
            List of Task model instances
        """
        tasks_data = self.get_tasks()
        tasks = []

        for task_dict in tasks_data:
            try:
                # Map spec fields to Task model fields (handle both snake_case and camelCase)
                task = Task(
                    id=task_dict.get("id", ""),
                    title=task_dict.get("title", ""),
                    description=task_dict.get("description", ""),
                    acceptanceCriteria=task_dict.get(
                        "acceptance_criteria", task_dict.get("acceptanceCriteria", [])
                    ),
                    status=task_dict.get("status", "ready"),
                    priority=task_dict.get("priority", 999),
                    labels=task_dict.get("labels", []),
                    locks=task_dict.get("locks", []),
                    dependencies=task_dict.get("depends_on", task_dict.get("dependsOn", [])),
                    dependents=task_dict.get("dependents", []),
                    createdAt=task_dict.get("created_at", task_dict.get("createdAt")),
                    updatedAt=task_dict.get("updated_at", task_dict.get("updatedAt")),
                    prdSource=task_dict.get("prd_source", task_dict.get("prdSource")),
                )
                tasks.append(task)
            except Exception:
                # Skip invalid tasks
                continue

        return tasks

    def get_task_by_id(self, task_id: str) -> dict[str, Any] | None:
        """Get a specific task by ID.

        Args:
            task_id: Task ID to find

        Returns:
            Task dictionary or None if not found
        """
        tasks = self.get_tasks()
        for task in tasks:
            if task.get("id") == task_id:
                return task
        return None

    def get_tasks_by_label(self, label: str) -> list[dict[str, Any]]:
        """Get tasks with a specific label.

        Args:
            label: Label to filter by

        Returns:
            List of task dictionaries with the label
        """
        tasks = self.get_tasks()
        return [t for t in tasks if label in t.get("labels", [])]

    def get_tasks_by_status(self, status: str) -> list[dict[str, Any]]:
        """Get tasks with a specific status.

        Args:
            status: Status to filter by (ready/done/verified)

        Returns:
            List of task dictionaries with the status
        """
        tasks = self.get_tasks()
        return [t for t in tasks if t.get("status") == status]

    def check_file_health(self) -> dict[str, Any]:
        """Check spec file health and accessibility.

        Returns:
            Health status dictionary
        """
        health: dict[str, Any] = {
            "exists": self.spec_path.exists(),
            "readable": False,
            "valid_yaml": False,
            "task_count": 0,
            "error": None,
        }

        if not health["exists"]:
            health["error"] = "Spec file not found"
            return health

        try:
            spec = self.read()
            health["readable"] = True
            health["valid_yaml"] = True
            health["task_count"] = len(spec.get("tasks", []))
        except yaml.YAMLError as e:
            health["readable"] = True
            health["error"] = f"YAML parsing error: {e}"
        except Exception as e:
            health["error"] = str(e)

        return health
