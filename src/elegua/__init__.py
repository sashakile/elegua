"""Eleguá — domain-agnostic multi-tier test harness."""

from elegua.adapter import Adapter, WolframAdapter
from elegua.blobstore import BlobStore
from elegua.comparison import (
    ComparisonResult,
    compare_identity,
    compare_pipeline,
    compare_structural,
)
from elegua.models import ActionPayload, ValidationToken
from elegua.property import GeneratorRegistry, PropertyResult, PropertyRunner, PropertySpec
from elegua.runner import load_toml_tasks, run_tasks
from elegua.task import EleguaTask, InvalidTransition, TaskStatus

__all__ = [
    "ActionPayload",
    "Adapter",
    "BlobStore",
    "ComparisonResult",
    "EleguaTask",
    "GeneratorRegistry",
    "InvalidTransition",
    "PropertyResult",
    "PropertyRunner",
    "PropertySpec",
    "TaskStatus",
    "ValidationToken",
    "WolframAdapter",
    "compare_identity",
    "compare_pipeline",
    "compare_structural",
    "load_toml_tasks",
    "run_tasks",
]
