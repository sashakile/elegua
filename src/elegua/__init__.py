"""Eleguá — domain-agnostic multi-tier test harness."""

from elegua.adapter import Adapter, WolframAdapter
from elegua.blobstore import BlobStore
from elegua.bridge import (
    Expected,
    Operation,
    TestCase,
    TestFile,
    TestFileMeta,
    load_sxact_toml,
)
from elegua.comparison import (
    ComparisonPipeline,
    ComparisonResult,
    compare_identity,
    compare_pipeline,
    compare_structural,
)
from elegua.context import ExecutionContext
from elegua.isolation import IsolatedRunner, TestRunResult
from elegua.models import ActionPayload, ValidationToken
from elegua.oracle import OracleClient
from elegua.property import GeneratorRegistry, PropertyResult, PropertyRunner, PropertySpec
from elegua.runner import load_toml_tasks, run_tasks
from elegua.snapshot import RecordingAdapter, ReplayAdapter, SnapshotStore
from elegua.task import EleguaTask, InvalidTransition, TaskStatus
from elegua.wolfram import WolframOracleAdapter

__all__ = [
    "ActionPayload",
    "Adapter",
    "BlobStore",
    "ComparisonPipeline",
    "ComparisonResult",
    "EleguaTask",
    "ExecutionContext",
    "Expected",
    "GeneratorRegistry",
    "InvalidTransition",
    "IsolatedRunner",
    "Operation",
    "OracleClient",
    "PropertyResult",
    "PropertyRunner",
    "PropertySpec",
    "RecordingAdapter",
    "ReplayAdapter",
    "SnapshotStore",
    "TaskStatus",
    "TestCase",
    "TestFile",
    "TestFileMeta",
    "TestRunResult",
    "ValidationToken",
    "WolframAdapter",
    "WolframOracleAdapter",
    "compare_identity",
    "compare_pipeline",
    "compare_structural",
    "load_sxact_toml",
    "load_toml_tasks",
    "run_tasks",
]
