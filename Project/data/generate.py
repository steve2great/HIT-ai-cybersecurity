"""
Synthetic authentication-event generator for SOC-Copilot.

Why synthetic data?
-------------------
Real corporate auth logs are private and cannot be shared in a student
project. Public datasets (CIC-IDS, UNSW-NB15) are network-flow oriented,
not auth-event oriented, so they would force us to pivot the project away
from the SOC-triage angle.

Instead, we generate a controlled dataset that:

  * has a realistic *benign* population (24-hour usage curve, a handful of
    services, a finite user/IP universe, weekday vs weekend bias);
  * embeds three distinct attack profiles, each tagged with the MITRE
    technique it is meant to represent:

      - T1110.001 Brute Force            -- loud password guessing
      - T1110.003 Password Spraying      -- low-and-slow, many users, few tries
      - T1078     Valid Accounts         -- correct creds from anomalous geo/hour

  * has a configurable contamination ratio (default 3 %, matching Lab 2);
  * is fully reproducible via --seed.

The output CSV is the *only* artefact downstream code depends on, so the
generator is the project's source of truth.
"""

from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Universe
# ---------------------------------------------------------------------------

SERVICES = ["ssh", "rdp", "vpn", "webapp"]
PROTOCOLS = {"ssh": "tcp22", "rdp": "tcp3389", "vpn": "udp1194", "webapp": "tcp443"}

KNOWN_USERS = [
    "alice", "bob", "carol", "dave", "erin", "frank", "grace", "heidi",
    "ivan", "judy", "kevin", "laura", "mallory", "niaj", "olivia",
    "peggy", "quentin", "ruth", "sam", "trent",
]
ADMIN_USERS = ["root", "admin", "administrator", "svc-backup", "svc-ad"]
ALL_USERS = KNOWN_USERS + ADMIN_USERS

# /16 office subnet - assume the company owns 10.20.0.0/16
def _office_ip() -> str:
    return f"10.20.{random.randint(0, 255)}.{random.randint(1, 254)}"

# external IPs the company has seen before (partner VPN, remote workers)
KNOWN_EXTERNAL = [
    "203.0.113.42",   # branch office
    "203.0.113.51",
    "198.51.100.7",   # work-from-home gateway
    "198.51.100.18",
    "198.51.100.99",
]

# pool of attacker-controlled IPs we will use in anomalies
ATTACKER_IPS = [
    "185.243.115.84",   # used in Lab 1 / Lab 3 as a Volt Typhoon IOC
    "45.83.64.219",
    "91.219.236.222",
    "194.31.98.74",
    "5.188.206.13",
]


# ---------------------------------------------------------------------------
# Event schema
# ---------------------------------------------------------------------------

@dataclass
class AuthEvent:
    timestamp: str
    user: str
    source_ip: str
    service: str
    protocol: str
    success: int                # 0 = failed, 1 = succeeded
    failed_attempts_5min: int   # rolling counter; cheap proxy of brute force
    bytes_sent: int
    session_duration_ms: int
    user_is_known: int          # 1 if user is in KNOWN_USERS+ADMIN_USERS, else 0
    ip_is_known: int            # 1 if source_ip is office or KNOWN_EXTERNAL, else 0
    hour: int                   # 0..23 from timestamp, for convenience
    # ground truth, used only for evaluation -- the model never sees this
    is_anomaly: int
    attack_label: str           # "" for benign, e.g. "T1110.001" otherwise


# ---------------------------------------------------------------------------
# Benign behaviour
# ---------------------------------------------------------------------------

def _benign_hour() -> int:
    """Office hours peaked around 10:00 and 14:00, low overnight."""
    # mixture of two normals around 10 and 14 + uniform noise (night shift)
    if random.random() < 0.05:                 # 5 % night-shift legitimate users
        return random.randint(0, 23)
    peak = random.choice([10, 14])
    return int(np.clip(np.random.normal(peak, 2.0), 0, 23))


def _benign_event(t0: datetime) -> AuthEvent:
    user = random.choice(ALL_USERS)
    service = random.choice(SERVICES)
    hour = _benign_hour()
    # weekday minute offset within the day
    minute_in_day = hour * 60 + random.randint(0, 59)
    day_offset = random.randint(0, 6)
    ts = t0 + timedelta(days=day_offset, minutes=minute_in_day, seconds=random.randint(0, 59))

    # 97 % of benign attempts succeed; the 3 % fails are typos / lockouts
    success = int(random.random() > 0.03)
    # if it fails, allow 1-2 prior fails in the rolling window (typical user)
    failed_5min = 0 if success else random.randint(1, 2)

    # office subnet 80 % of the time, known external 20 %
    src_ip = _office_ip() if random.random() < 0.80 else random.choice(KNOWN_EXTERNAL)

    return AuthEvent(
        timestamp=ts.isoformat(timespec="seconds"),
        user=user,
        source_ip=src_ip,
        service=service,
        protocol=PROTOCOLS[service],
        success=success,
        failed_attempts_5min=failed_5min,
        bytes_sent=int(np.clip(np.random.normal(4000, 1500), 100, 50_000)),
        session_duration_ms=int(np.clip(np.random.normal(180_000, 80_000), 1_000, 2_000_000)),
        user_is_known=1,
        ip_is_known=1,
        hour=hour,
        is_anomaly=0,
        attack_label="",
    )


# ---------------------------------------------------------------------------
# Attack behaviour -- three distinct MITRE techniques
# ---------------------------------------------------------------------------

def _attack_brute_force(t0: datetime) -> AuthEvent:
    """T1110.001 -- loud brute force from an external IP, one user, many fails."""
    user = random.choice(ADMIN_USERS)                 # attackers love admin
    hour = random.choice([1, 2, 3, 4, 22, 23])        # off-hours
    minute_in_day = hour * 60 + random.randint(0, 59)
    day_offset = random.randint(0, 6)
    ts = t0 + timedelta(days=day_offset, minutes=minute_in_day, seconds=random.randint(0, 59))

    return AuthEvent(
        timestamp=ts.isoformat(timespec="seconds"),
        user=user,
        source_ip=random.choice(ATTACKER_IPS),
        service="ssh",
        protocol=PROTOCOLS["ssh"],
        success=0,
        failed_attempts_5min=random.randint(15, 60),  # the give-away signal
        bytes_sent=random.randint(80, 400),           # tiny, no actual session
        session_duration_ms=random.randint(200, 2_000),
        user_is_known=1,
        ip_is_known=0,
        hour=hour,
        is_anomaly=1,
        attack_label="T1110.001",
    )


def _attack_password_spray(t0: datetime) -> AuthEvent:
    """T1110.003 -- one external IP, many *different* users, only 1-3 tries each.

    This is the stealthy one. failed_attempts_5min is intentionally LOW
    (because per-user it really is low) -- the signal lives in the
    cross-user pattern, which the per-event model has to pick up via the
    ip_is_known + user_is_known + hour combination.
    """
    user = random.choice(KNOWN_USERS)
    hour = random.randint(8, 18)                      # in-hours camouflage
    minute_in_day = hour * 60 + random.randint(0, 59)
    day_offset = random.randint(0, 6)
    ts = t0 + timedelta(days=day_offset, minutes=minute_in_day, seconds=random.randint(0, 59))

    return AuthEvent(
        timestamp=ts.isoformat(timespec="seconds"),
        user=user,
        source_ip=random.choice(ATTACKER_IPS),
        service=random.choice(["webapp", "vpn"]),
        protocol=PROTOCOLS["webapp"],
        success=0,
        failed_attempts_5min=random.randint(1, 3),    # quiet
        bytes_sent=random.randint(300, 900),
        session_duration_ms=random.randint(500, 3_000),
        user_is_known=1,
        ip_is_known=0,                                # the only clear signal
        hour=hour,
        is_anomaly=1,
        attack_label="T1110.003",
    )


def _attack_valid_accounts(t0: datetime) -> AuthEvent:
    """T1078 -- stolen creds: SUCCESS, known user, but unknown IP and odd hour.

    The hardest of the three -- there is no failed-login signal at all.
    Detection has to come from the combination
    `success=1 & ip_is_known=0 & hour in [0..5] | [22..23]`.
    """
    user = random.choice(KNOWN_USERS + ADMIN_USERS)
    hour = random.choice([0, 1, 2, 3, 4, 5, 23])
    minute_in_day = hour * 60 + random.randint(0, 59)
    day_offset = random.randint(0, 6)
    ts = t0 + timedelta(days=day_offset, minutes=minute_in_day, seconds=random.randint(0, 59))

    return AuthEvent(
        timestamp=ts.isoformat(timespec="seconds"),
        user=user,
        source_ip=random.choice(ATTACKER_IPS),
        service=random.choice(["vpn", "rdp"]),
        protocol=PROTOCOLS["vpn"],
        success=1,
        failed_attempts_5min=0,
        bytes_sent=int(np.clip(np.random.normal(8_000, 3_000), 500, 100_000)),
        session_duration_ms=int(np.clip(np.random.normal(600_000, 200_000), 10_000, 4_000_000)),
        user_is_known=1,
        ip_is_known=0,
        hour=hour,
        is_anomaly=1,
        attack_label="T1078",
    )


# ---------------------------------------------------------------------------
# Dataset assembly
# ---------------------------------------------------------------------------

ATTACK_MIX = [
    (_attack_brute_force,    0.50),   # 50 % of anomalies
    (_attack_password_spray, 0.30),
    (_attack_valid_accounts, 0.20),
]


def _sample_attack(t0: datetime) -> AuthEvent:
    r = random.random()
    acc = 0.0
    for fn, w in ATTACK_MIX:
        acc += w
        if r <= acc:
            return fn(t0)
    return ATTACK_MIX[-1][0](t0)


def generate(n: int, contamination: float, seed: int) -> list[AuthEvent]:
    random.seed(seed)
    np.random.seed(seed)

    # anchor the simulated week at 2024-10-07 Mon 00:00
    t0 = datetime(2024, 10, 7, 0, 0, 0)
    n_attack = int(round(n * contamination))
    n_benign = n - n_attack
    events: list[AuthEvent] = [_benign_event(t0) for _ in range(n_benign)]
    events += [_sample_attack(t0) for _ in range(n_attack)]
    random.shuffle(events)
    return events


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=10_000, help="total events")
    parser.add_argument("--contamination", type=float, default=0.03,
                        help="fraction of events that are anomalous")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).parent / "soc_events.csv")
    args = parser.parse_args()

    events = generate(args.n, args.contamination, args.seed)

    fieldnames = list(asdict(events[0]).keys())
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for ev in events:
            writer.writerow(asdict(ev))

    # quick summary
    from collections import Counter
    labels = Counter(ev.attack_label for ev in events)
    print(f"Wrote {len(events):,} events to {args.out}")
    print("Class distribution:")
    for k, v in sorted(labels.items(), key=lambda kv: -kv[1]):
        tag = k or "benign"
        print(f"  {tag:>12s}  {v:>5d}  ({v / len(events):.2%})")


if __name__ == "__main__":
    main()
