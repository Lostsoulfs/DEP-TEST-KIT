"""Oracle + CLI-contract test for open_redirect (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_open_redirect_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import open_redirect_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.allows_same_site(h.AllowlistRedirect) is True


import pytest  # noqa: E402

# documented open-redirect bypasses (PayloadsAllTheThings; PortSwigger URL-validation cheat sheet)
_OPEN_REDIRECT_BYPASSES = [
    "//evil.com", "https://evil.com", "https:evil.com", "/\\evil.com", "\\/\\/evil.com",
    "https://app.example.evil.com", "https://app.example@evil.com", "////evil.com",
    "https://evil.com/app.example", "/%5cevil.com", "https://app.example.attacker.com",
    "http://evil.com", "javascript:alert(1)",
]


@pytest.mark.parametrize("target", _OPEN_REDIRECT_BYPASSES)
def test_oracle_blocks_open_redirect_bypass(target) -> None:
    host = h._host(h.AllowlistRedirect().resolve(target))
    assert host is None or host in h._ALLOWED, target


_SAFE_TARGETS = ["/dashboard", "/", "/app/settings?next=1", "https://app.example/home", "/a/b#frag"]


@pytest.mark.parametrize("target", _SAFE_TARGETS)
def test_oracle_preserves_safe_target(target) -> None:
    assert h.AllowlistRedirect().resolve(target) == target, target


_GARBAGE_TARGETS = [
    "", "://", "http://", "javascript:alert(1)", "\\\\", "%00", "ht tp://x", "data:text/html,x",
]


@pytest.mark.parametrize("target", _GARBAGE_TARGETS)
def test_oracle_degrades_safely_on_garbage(target) -> None:
    result = h.AllowlistRedirect().resolve(target)
    host = h._host(result)
    assert host is None or host in h._ALLOWED, target


# === our own / batch 4 (original; panel + math bench) ===
# Constantin (surreal/sw) + math: a sanitizer is a PROJECTION -- resolve(resolve(x)) == resolve(x).
# Feeding the cleaned target back in must reach a fixed point (safe path, allowlisted, or "/").
def test_oracle_resolve_is_idempotent_projection() -> None:
    r = h.AllowlistRedirect()
    corpus = ["/dashboard", "https://app.example/x", "https://evil.example/phish", "//evil.com",
              "/\\evil", "javascript:alert(1)", "not a url", "https://evil.com@app.example/y"]
    for x in corpus:
        once = r.resolve(x)
        assert r.resolve(once) == once, x


# Toll (surreal/psych): the userinfo "@" ghost -- the real host is what follows the last "@".
# app.example@evil.com LOOKS allowlisted but goes to evil.com (blocked); the reverse is allowed.
def test_oracle_userinfo_at_ghost_resolves_to_real_host() -> None:
    r = h.AllowlistRedirect()
    assert r.resolve("https://app.example@evil.com/p") == "/"
    assert r.resolve("https://evil.com@app.example/p") == "https://evil.com@app.example/p"
