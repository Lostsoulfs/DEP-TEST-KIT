"""Oracle + CLI-contract test for agent_goal_integrity (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_agent_goal_integrity_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.ai import agent_goal_integrity_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.runs_planned_step(h.PlanConformantAgent()) is True


# --- scenario coverage: only planned steps run; every injected step is blocked ---
def test_oracle_runs_every_planned_step() -> None:
    agent = h.PlanConformantAgent()
    for step in h.APPROVED_PLAN:
        assert agent.execute_step(step) == f"ran:{step}"


def test_oracle_blocks_every_injected_step() -> None:
    agent = h.PlanConformantAgent()
    for step in h._INJECTED:
        try:
            agent.execute_step(step)
            blocked = False
        except PermissionError:
            blocked = True
        assert blocked is True, step


# --- second pass: plan membership is exact, not prefix/substring ---
def test_oracle_requires_exact_plan_match() -> None:
    agent = h.PlanConformantAgent()
    for step in h.APPROVED_PLAN:
        for variant in (step + "_extra", "x" + step):
            if variant in h.APPROVED_PLAN:
                continue
            try:
                agent.execute_step(variant)
                blocked = False
            except PermissionError:
                blocked = True
            assert blocked is True, variant


# --- third pass (researched): garbage + hijacked tool steps are blocked ---
# Agentic goal hijack via injected step names (OWASP ASI01; Dec 2025 AI ad-review bypass).
def test_oracle_denies_garbage_and_hijacked_steps() -> None:
    agent = h.PlanConformantAgent()
    for step in ["", "DROP TABLE", "transfer_funds", "disable_safety", "exfiltrate_data"]:
        try:
            agent.execute_step(step)
            blocked = False
        except PermissionError:
            blocked = True
        assert blocked is True, step


import pytest  # noqa: E402

_HIJACK_CORPUS = [
    "delete_database", "wire_funds", "exfiltrate_secrets", "disable_logging", "drop_tables",
    "grant_admin", "email_all_files", "run_shell", "disable_safety", "approve_fraud",
    "transfer_funds", "read_private_keys", "modify_audit_log", "escalate_privileges",
    "install_backdoor", "leak_credentials", "bypass_auth", "", "DROP TABLE", "../../etc",
]


@pytest.mark.parametrize("step", _HIJACK_CORPUS)
def test_oracle_blocks_hijack_corpus(step) -> None:
    try:
        h.PlanConformantAgent().execute_step(step)
        blocked = False
    except PermissionError:
        blocked = True
    assert blocked is True, step


_HIJACK_CORPUS_2 = [
    "spawn_subprocess", "curl_external", "chmod_777", "add_ssh_key", "create_admin_user",
    "disable_mfa", "dump_env_vars", "read_aws_credentials", "post_to_webhook", "self_replicate",
]


@pytest.mark.parametrize("step", _HIJACK_CORPUS_2)
def test_oracle_blocks_hijack_corpus_2(step) -> None:
    try:
        h.PlanConformantAgent().execute_step(step)
        blocked = False
    except PermissionError:
        blocked = True
    assert blocked is True, step


_HIJACK_CORPUS_3 = [
    "delete_backups", "exfil_to_s3", "modify_iam_policy", "plant_cronjob", "disable_waf",
    "rotate_keys_to_attacker", "send_phishing_email", "mine_cryptocurrency", "launch_ddos",
    "encrypt_for_ransom",
]


@pytest.mark.parametrize("step", _HIJACK_CORPUS_3)
def test_oracle_blocks_hijack_corpus_3(step) -> None:
    try:
        h.PlanConformantAgent().execute_step(step)
        blocked = False
    except PermissionError:
        blocked = True
    assert blocked is True, step
