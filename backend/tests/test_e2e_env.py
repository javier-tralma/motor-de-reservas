import os
import subprocess
import sys
from pathlib import Path


def test_run_e2e_script_defines_all_required_settings_in_clean_env():
    """
    Verify that frontend/scripts/run_e2e.sh exports all required Settings
    variables before invoking setup_e2e.py, without requiring a .env file
    or external environment variables.
    """
    repo_root = Path(__file__).parent.parent.parent
    run_e2e_script = repo_root / "frontend" / "scripts" / "run_e2e.sh"
    backend_dir = repo_root / "backend"

    assert run_e2e_script.exists(), "frontend/scripts/run_e2e.sh must exist"

    # Extract export statements from the top of run_e2e.sh before any Docker or command execution
    script_lines = run_e2e_script.read_text(encoding="utf-8").splitlines()
    export_lines = [line.strip() for line in script_lines if line.strip().startswith("export ")]

    export_block = "\n".join(export_lines)
    assert "E2E_DATABASE_URL=" in export_block
    assert "BUSINESS_ID=" in export_block
    assert "FRONTEND_URL=" in export_block
    assert "RATE_LIMIT_SECRET=" in export_block
    assert "SESSION_SECRET=" in export_block
    assert "EMAIL_PROVIDER=" in export_block

    # Run Python in a completely clean environment (env -i) with only PATH preserved,
    # sourcing the export lines from run_e2e.sh and verifying Settings instantiates successfully.
    python_cmd = (
        f"{export_block}\n"
        f'export DATABASE_URL="$E2E_DATABASE_URL"\n'
        f'export PYTHONPATH="{backend_dir}"\n'
        f'"{sys.executable}" -c \'\n'
        f"from app.core.config import Settings\n"
        f"s = Settings(_env_file=None)\n"
        f'assert s.APP_ENV == "e2e"\n'
        f'assert s.BUSINESS_ID == "00000000-0000-0000-0000-000000000001"\n'
        f'assert s.FRONTEND_URL == "http://127.0.0.1:4173"\n'
        f'assert s.SESSION_SECRET == "e2e-session-secret-key-test-32-bytes"\n'
        f'assert s.RATE_LIMIT_SECRET == "e2e-secret-key-test-32-bytes"\n'
        f'assert s.EMAIL_PROVIDER == "noop"\n'
        f'assert "booking_e2e" in s.DATABASE_URL\n'
        f'print("SETTINGS_OK")\n'
        f"'\n"
    )

    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    res = subprocess.run(
        ["bash", "-c", python_cmd],
        cwd=str(backend_dir),
        env=env,
        capture_output=True,
        text=True,
    )

    assert res.returncode == 0, f"Clean env Settings initialization failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
    assert "SETTINGS_OK" in res.stdout
