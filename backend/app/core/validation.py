"""
System validation for macOS ARM64 environment.

Validates:
- Architecture is ARM64
- Platform is macOS (darwin)
- Python version is 3.11+
- No Rosetta translation
- Ollama reachability
"""

from __future__ import annotations

import platform
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional

import httpx


@dataclass
class ValidationResult:
    """Result of a single validation check."""

    name: str
    passed: bool
    message: str
    detail: Optional[str] = None


@dataclass
class SystemValidation:
    """Complete system validation result."""

    checks: list[ValidationResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """Check if all validations passed."""
        return all(check.passed for check in self.checks)

    @property
    def summary(self) -> dict:
        """Return validation summary as dict."""
        return {
            "all_passed": self.all_passed,
            "total": len(self.checks),
            "passed": sum(1 for c in self.checks if c.passed),
            "failed": sum(1 for c in self.checks if not c.passed),
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "message": c.message,
                    "detail": c.detail,
                }
                for c in self.checks
            ],
        }


def check_architecture() -> ValidationResult:
    """Verify system is ARM64."""
    arch = platform.machine()
    passed = arch == "arm64"
    return ValidationResult(
        name="architecture",
        passed=passed,
        message=f"Architecture: {arch}",
        detail="ARM64 required for Apple Silicon optimization"
        if not passed
        else None,
    )


def check_platform() -> ValidationResult:
    """Verify platform is macOS (darwin)."""
    plat = sys.platform
    passed = plat == "darwin"
    return ValidationResult(
        name="platform",
        passed=passed,
        message=f"Platform: {plat}",
        detail="macOS (darwin) required" if not passed else None,
    )


def check_python_version() -> ValidationResult:
    """Verify Python version is 3.11+."""
    version = sys.version_info
    passed = version >= (3, 11)
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    return ValidationResult(
        name="python_version",
        passed=passed,
        message=f"Python: {version_str}",
        detail="Python 3.11+ required" if not passed else None,
    )


def check_rosetta() -> ValidationResult:
    """Check if running under Rosetta translation (should NOT be)."""
    try:
        result = subprocess.run(
            ["sysctl", "-n", "sysctl.proc_translated"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # 0 = native ARM64, 1 = Rosetta translated
        is_translated = result.stdout.strip() == "1"
        passed = not is_translated
        return ValidationResult(
            name="rosetta",
            passed=passed,
            message="No Rosetta translation" if passed else "Running under Rosetta",
            detail="Native ARM64 execution required, disable Rosetta"
            if not passed
            else None,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # If we can't check, assume native on ARM64
        if platform.machine() == "arm64":
            return ValidationResult(
                name="rosetta",
                passed=True,
                message="Rosetta check unavailable, ARM64 confirmed by architecture",
            )
        return ValidationResult(
            name="rosetta",
            passed=False,
            message="Cannot verify Rosetta status",
            detail="Unable to determine if running under Rosetta",
        )


async def check_ollama(base_url: str = "http://localhost:11434") -> ValidationResult:
    """Check if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get("models", []))
                return ValidationResult(
                    name="ollama",
                    passed=True,
                    message=f"Ollama reachable at {base_url} ({model_count} models available)",
                )
            return ValidationResult(
                name="ollama",
                passed=False,
                message=f"Ollama returned status {response.status_code}",
                detail=f"Expected 200 from {base_url}/api/tags",
            )
    except httpx.ConnectError:
        return ValidationResult(
            name="ollama",
            passed=False,
            message=f"Ollama not reachable at {base_url}",
            detail="Ensure Ollama is installed and running: ollama serve",
        )
    except httpx.TimeoutException:
        return ValidationResult(
            name="ollama",
            passed=False,
            message=f"Ollama connection timed out at {base_url}",
            detail="Ollama may be starting up or overloaded",
        )
    except Exception as e:
        return ValidationResult(
            name="ollama",
            passed=False,
            message=f"Ollama check failed: {type(e).__name__}",
            detail=str(e),
        )


def run_sync_checks() -> list[ValidationResult]:
    """Run all synchronous validation checks."""
    return [
        check_architecture(),
        check_platform(),
        check_python_version(),
        check_rosetta(),
    ]


async def run_all_checks(ollama_url: str = "http://localhost:11434") -> SystemValidation:
    """Run all validation checks (sync + async)."""
    validation = SystemValidation()
    validation.checks.extend(run_sync_checks())
    validation.checks.append(await check_ollama(ollama_url))
    return validation
