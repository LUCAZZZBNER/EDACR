"""Shared task identity validation for queue and standalone assembly."""
from pathlib import Path
from typing import Any


def validate_manifest_tasks(manifest: Any) -> list[dict[str, Any]]:
    if not isinstance(manifest, dict) or not isinstance(manifest.get("tasks"), list):
        raise ValueError("manifest.tasks must be a list")
    tasks = []
    seen_keys, seen_files, seen_results = set(), set(), set()
    required = ("thread_key", "input_file", "input_sha256", "stratum", "worker_id")
    for ordinal, value in enumerate(manifest["tasks"], 1):
        if not isinstance(value, dict):
            raise ValueError(f"manifest task {ordinal} must be an object")
        missing = [key for key in required if key not in value]
        if missing:
            raise ValueError(f"manifest task {ordinal} missing {','.join(missing)}")
        key, input_file = value["thread_key"], value["input_file"]
        if not isinstance(key, str) or not key:
            raise ValueError(f"manifest task {ordinal} has invalid thread_key")
        if not isinstance(input_file, str) or not input_file:
            raise ValueError(f"manifest task {ordinal} has invalid input_file")
        if not isinstance(value["input_sha256"], str) or not value["input_sha256"]:
            raise ValueError(f"manifest task {ordinal} has invalid input_sha256")
        normalised = Path(input_file)
        if normalised.is_absolute() or ".." in normalised.parts:
            raise ValueError(f"manifest task {ordinal} input_file escapes run-dir")
        input_file = normalised.as_posix()
        if key in seen_keys:
            raise ValueError(f"duplicate thread_key: {key}")
        if input_file in seen_files:
            raise ValueError(f"duplicate input_file: {input_file}")
        # Results use the basename, even if an input is in a nested directory.
        if normalised.name in seen_results:
            raise ValueError(f"duplicate result filename: {normalised.name}")
        seen_keys.add(key)
        seen_files.add(input_file)
        seen_results.add(normalised.name)
        if input_file != value["input_file"]:
            value = {**value, "input_file": input_file}
        tasks.append(value)
    full = manifest.get("scope") == "full" or any(t["stratum"] == "full" for t in tasks)
    if full and "population_threads" in manifest:
        population = manifest["population_threads"]
        if type(population) is not int or population < 0:
            raise ValueError("population_threads must be a nonnegative integer")
        if len(tasks) > population or (manifest.get("status") == "complete" and len(tasks) != population):
            raise ValueError("full manifest population does not match unique task count")
    return tasks
