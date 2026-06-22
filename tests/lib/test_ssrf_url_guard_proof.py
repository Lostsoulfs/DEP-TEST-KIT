"""Proof: connection-time IP pinning defeats the DNS rebinding the denylist guard misses.
The pinning guard stays on the public IP; the denylist guard re-resolves to 169.254.169.254."""

from harnesses.lib import ssrf_url_guard_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.allows_ssrf(h.DenylistGuard) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.allows_ssrf(h.PinningGuard) is False


def test_proof_oracle_happy_path() -> None:
    assert h.fetches_public_ok(h.PinningGuard) is True


# --- scenario coverage: the denylist guard is reachable on each variant ---
_MAPPED = "::ffff:169.254.169.254"
_SSRF_ATTACKS = {
    "decimal_ip": ("http://2852039166/", lambda host: "169.254.169.254"),
    "hex_ip": ("http://0xA9FEA9FE/", lambda host: "169.254.169.254"),
    "ipv6_loopback": ("http://[::1]/", lambda host: "::1"),
    "ipv4_mapped_v6": (f"http://[{_MAPPED}]/", lambda host: _MAPPED),
    "metadata_hostname": ("http://metadata.internal/", lambda host: "169.254.169.254"),
    "internal_rfc1918": ("http://intranet.corp/", lambda host: "10.0.0.5"),
}


def test_proof_denylist_guard_reaches_internal_on_each() -> None:
    import ipaddress
    for name, (url, resolver) in _SSRF_ATTACKS.items():
        try:
            reached = h.DenylistGuard().fetch(url, resolver)
        except h.Blocked:
            reached = None
        assert reached is not None and not ipaddress.ip_address(reached).is_global, name


# --- second pass: the denylist guard is reachable on the harder variants too ---
def test_proof_denylist_guard_reaches_internal_on_harder_variants() -> None:
    import ipaddress
    cases = {
        "userinfo_confusion": ("http://trusted.example@intranet/", lambda host: "10.1.1.1"),
        "octal_ip": ("http://0251.0376.0251.0376/", lambda host: "169.254.169.254"),
    }
    for name, (url, resolver) in cases.items():
        try:
            reached = h.DenylistGuard().fetch(url, resolver)
        except h.Blocked:
            reached = None
        assert reached is not None and not ipaddress.ip_address(reached).is_global, name


import pytest  # noqa: E402

# --- pass 4 (researched): the string denylist is bypassed by encoded/alternate host forms ---
_SSRF_BYPASSES = [
    ("metadata.google.internal", "169.254.169.254"),
    ("100.100.100.200", "100.100.100.200"),
    ("2852039166", "169.254.169.254"),
    ("0xA9FEA9FE", "169.254.169.254"),
    ("0251.0376.0251.0376", "169.254.169.254"),
    ("127.1", "127.0.0.1"),
    ("0", "0.0.0.0"),
    ("[::1]", "::1"),
    ("[::ffff:169.254.169.254]", "::ffff:169.254.169.254"),
    ("[::ffff:7f00:1]", "::ffff:127.0.0.1"),
    ("10.0.0.1", "10.0.0.1"),
    ("192.168.1.1", "192.168.1.1"),
    ("172.16.0.1", "172.16.0.1"),
    ("１２７.0.0.1", "127.0.0.1"),
]


@pytest.mark.parametrize("host,internal_ip", _SSRF_BYPASSES)
def test_proof_denylist_bypassed_by_encoding(host, internal_ip) -> None:
    import ipaddress
    try:
        reached = h.DenylistGuard().fetch("http://" + host + "/", lambda x: internal_ip)
    except h.Blocked:
        reached = None
    assert reached is not None and not ipaddress.ip_address(reached).is_global, host


_SSRF_TARGETS_2 = [
    ("169.254.169.254.", "169.254.169.254"),
    ("0x7f000001", "127.0.0.1"),
    ("017700000001", "127.0.0.1"),
    ("127.0.0.1.nip.io", "127.0.0.1"),
    ("[0:0:0:0:0:ffff:a9fe:a9fe]", "::ffff:169.254.169.254"),
    ("①②⑦.0.0.1", "127.0.0.1"),
    ("metadata", "169.254.169.254"),
    ("169.254.169.254%2f", "169.254.169.254"),
]


@pytest.mark.parametrize("host,internal_ip", _SSRF_TARGETS_2)
def test_proof_denylist_bypassed_2(host, internal_ip) -> None:
    import ipaddress
    try:
        reached = h.DenylistGuard().fetch("http://" + host + "/", lambda x: internal_ip)
    except h.Blocked:
        reached = None
    assert reached is not None and not ipaddress.ip_address(reached).is_global, host
