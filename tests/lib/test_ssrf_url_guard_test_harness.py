"""Oracle + CLI-contract test for ssrf_url_guard (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_ssrf_url_guard_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import ssrf_url_guard_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.fetches_public_ok(h.PinningGuard) is True


# --- scenario coverage: more SSRF variants the pinning guard must block ---
_MAPPED = "::ffff:169.254.169.254"
SSRF_ATTACKS = {
    "decimal_ip": ("http://2852039166/", lambda host: "169.254.169.254"),
    "hex_ip": ("http://0xA9FEA9FE/", lambda host: "169.254.169.254"),
    "ipv6_loopback": ("http://[::1]/", lambda host: "::1"),
    "ipv4_mapped_v6": (f"http://[{_MAPPED}]/", lambda host: _MAPPED),
    "metadata_hostname": ("http://metadata.internal/", lambda host: "169.254.169.254"),
    "internal_rfc1918": ("http://intranet.corp/", lambda host: "10.0.0.5"),
}


def _ssrf_reached(make_guard, url, resolver):
    try:
        return make_guard().fetch(url, resolver)
    except h.Blocked:
        return None


def test_oracle_blocks_every_ssrf_variant() -> None:
    for name, (url, resolver) in SSRF_ATTACKS.items():
        assert _ssrf_reached(h.PinningGuard, url, resolver) is None, name


def test_oracle_allows_public_host() -> None:
    reached = _ssrf_reached(h.PinningGuard, "http://example.com/", lambda host: "93.184.216.34")
    assert reached == "93.184.216.34"


# --- second pass: harder variants + benign robustness ---
SSRF_ATTACKS_2 = {
    "userinfo_confusion": ("http://trusted.example@intranet/", lambda host: "10.1.1.1"),
    "unspecified_addr": ("http://0.0.0.0/", lambda host: "0.0.0.0"),
    "octal_ip": ("http://0251.0376.0251.0376/", lambda host: "169.254.169.254"),
}


def test_oracle_blocks_harder_ssrf_variants() -> None:
    for name, (url, resolver) in SSRF_ATTACKS_2.items():
        assert _ssrf_reached(h.PinningGuard, url, resolver) is None, name


def test_oracle_allows_public_ipv6() -> None:
    addr = "2606:2800:220:1:248:1893:25c8:1946"
    assert _ssrf_reached(h.PinningGuard, f"http://[{addr}]/", lambda host: addr) == addr


# --- third pass: malformed URLs resolving internal are still blocked ---
def test_oracle_never_reaches_internal_on_malformed_urls() -> None:
    import ipaddress
    for url in ["", "http://", "not-a-url", "http://[::zz]/", "ftp://x/"]:
        try:
            reached = h.PinningGuard().fetch(url, lambda host: "10.0.0.1")
        except Exception:
            reached = None
        assert reached is None or ipaddress.ip_address(reached).is_global, url


import pytest  # noqa: E402

# --- pass 4 (researched corpus): documented SSRF metadata endpoints + IP-encoding bypasses ---
# Sources: HackTricks Cloud SSRF; vulnsy SSRF cheat-sheet 2026; FastGPT GHSA-jhqw-944x-xh94.
_SSRF_TARGETS = [
    ("169.254.169.254", "169.254.169.254"),            # AWS / Azure IMDS
    ("metadata.google.internal", "169.254.169.254"),   # GCP
    ("100.100.100.200", "100.100.100.200"),            # Alibaba
    ("2852039166", "169.254.169.254"),                 # decimal
    ("0xA9FEA9FE", "169.254.169.254"),                 # hex
    ("0251.0376.0251.0376", "169.254.169.254"),        # octal
    ("127.0.0.1", "127.0.0.1"),
    ("127.1", "127.0.0.1"),                            # short form
    ("0", "0.0.0.0"),
    ("localhost", "127.0.0.1"),
    ("[::1]", "::1"),
    ("[::ffff:169.254.169.254]", "::ffff:169.254.169.254"),  # IPv4-mapped IPv6
    ("[::ffff:7f00:1]", "::ffff:127.0.0.1"),
    ("10.0.0.1", "10.0.0.1"),                          # RFC1918
    ("192.168.1.1", "192.168.1.1"),
    ("172.16.0.1", "172.16.0.1"),
    ("１２７.0.0.1", "127.0.0.1"),         # full-width unicode digits
]


@pytest.mark.parametrize("host,internal_ip", _SSRF_TARGETS)
def test_oracle_blocks_documented_ssrf_target(host, internal_ip) -> None:
    import ipaddress
    try:
        reached = h.PinningGuard().fetch("http://" + host + "/", lambda x: internal_ip)
    except Exception:
        reached = None
    assert reached is None or ipaddress.ip_address(reached).is_global, host


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
def test_oracle_blocks_ssrf_target_2(host, internal_ip) -> None:
    import ipaddress
    try:
        reached = h.PinningGuard().fetch("http://" + host + "/", lambda x: internal_ip)
    except Exception:
        reached = None
    assert reached is None or ipaddress.ip_address(reached).is_global, host


# === our own / batch 1 (original, reasoned from the oracle's own logic) ===
# Toll (surreal/psych): the IPv4-mapped IPv6 "ghost" -- looks v6, is a v4 address underneath.
def test_oracle_allows_ipv4_mapped_public_ip() -> None:
    import ipaddress
    reached = h.PinningGuard().fetch("http://[::ffff:93.184.216.34]/",
                                     lambda host: "::ffff:93.184.216.34")
    assert ipaddress.ip_address(reached).is_global  # mapped-public global -> no over-block


# Constantin (surreal/sw): metamorphic stickiness -- the pin holds across many later flips.
def test_oracle_pin_sticks_across_multiple_flips() -> None:
    seq = ["93.184.216.34", "169.254.169.254", "10.0.0.1", "127.0.0.1"]

    def resolver(host):
        return seq.pop(0) if seq else "169.254.169.254"

    assert h.PinningGuard().fetch("http://rebind/", resolver) == "93.184.216.34"
