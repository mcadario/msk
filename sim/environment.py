"""Simulated repository environment.

Models the paper's running example: a repository that migrates
from `make test-integration` to `npm run test:integration`.
"""
 

class SimulatedRepository:
    """
    Version 1: `make test-integration` works.
    Version 2: `make test-integration` fails; `npm run test:integration` works.
    """

    def __init__(self, version: int = 1):
        self.version = version
        self._run_count = 0

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    def execute(self, command: str) -> dict:
        cmd = command.strip()
        self._run_count += 1

        if cmd == "make test-integration":
            return self._make_test()
        if cmd == "npm run test:integration":
            return self._npm_test()
        if cmd in ("ls", "ls -la"):
            return self._ls()
        if cmd in ("cat README.md", "cat readme.md"):
            return self._readme()
        if cmd in ("cat package.json", "cat Makefile"):
            return self._config_file(cmd)
        if cmd.startswith("grep") or cmd.startswith("find"):
            return {"stdout": "(no matches)", "returncode": 1, "success": False}
        return {
            "stdout": f"bash: {cmd}: command not found",
            "returncode": 127,
            "success": False,
        }

    def _make_test(self) -> dict:
        if self.version == 1:
            return {
                "stdout": (
                    "Running integration tests via Makefile...\n"
                    "  ✓  auth tests passed\n"
                    "  ✓  database tests passed\n"
                    f"All tests passed. (run #{self._run_count})"
                ),
                "returncode": 0,
                "success": True,
            }
        return {
            "stdout": (
                "make: *** No rule to make target 'test-integration'.\n"
                "make: Stop.\n"
                "Hint: This project was migrated to npm. "
                "Try: npm run test:integration"
            ),
            "returncode": 2,
            "success": False,
        }

    def _npm_test(self) -> dict:
        return {
            "stdout": (
                "Running integration tests via npm...\n"
                "  ✓  auth suite (12 tests)\n"
                "  ✓  db suite (8 tests)\n"
                f"All tests passed. (run #{self._run_count})"
            ),
            "returncode": 0,
            "success": True,
        }

    def _ls(self) -> dict:
        return {
            "stdout": "Makefile  README.md  package.json  src/  tests/  .env.example",
            "returncode": 0,
            "success": True,
        }

    def _readme(self) -> dict:
        if self.version == 1:
            return {
                "stdout": (
                    "# Project\n\n"
                    "## Running tests\n"
                    "Integration tests: `make test-integration`\n"
                    "Unit tests: `make test-unit`\n"
                ),
                "returncode": 0,
                "success": True,
            }
        return {
            "stdout": (
                "# Project\n\n"
                "## Running tests\n"
                "Integration tests: `npm run test:integration`\n"
                "Unit tests: `npm run test:unit`\n"
                "\n> Migrated from Makefile targets in v2.0"
            ),
            "returncode": 0,
            "success": True,
        }

    def _config_file(self, cmd: str) -> dict:
        if "package.json" in cmd:
            scripts = (
                '"test:integration": "jest --config jest.integration.js"'
                if self.version >= 2
                else '"test": "jest"'
            )
            return {
                "stdout": f'{{"name":"project","scripts":{{{scripts}}}}}',
                "returncode": 0,
                "success": True,
            }
        # Makefile
        if self.version == 1:
            return {
                "stdout": "test-integration:\n\t./scripts/run_integration.sh\n",
                "returncode": 0,
                "success": True,
            }
        return {
            "stdout": "# test-integration target removed — see package.json\n",
            "returncode": 0,
            "success": True,
        }

    # ------------------------------------------------------------------
    # State control
    # ------------------------------------------------------------------

    def migrate_to_v2(self) -> None:
        self.version = 2

    def reset(self) -> None:
        self.version = 1
        self._run_count = 0
