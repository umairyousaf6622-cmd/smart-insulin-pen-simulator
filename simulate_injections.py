"""
Phase 1 - Synthetic data generator for a smart insulin pen.

Simulates the sensor stream (plunger force + plunger velocity) from a pen that
has a load cell on the thumb button and a linear encoder on the plunger rod.

Three scenarios are generated:
    normal             - smooth press, steady plateau, full dose, needle hold
    fast_injection     - force overshoot / spike, dose delivered too quickly
    premature_release  - thumb lifts early, plunger stops, incomplete dose

Physics (simplified, quasi-static):
    The force you apply must first overcome the rubber-stopper friction, then
    push insulin through the needle. Flow through a thin needle follows the
    Hagen-Poiseuille law:  Q = (pi * r^4 * dP) / (8 * mu * L)
    With dP = F_net / A_plunger and plunger velocity v = Q / A_plunger:

        v = (F_applied - F_friction) / c      where   c = 8*mu*L*A^2 / (pi*r^4)

    So c is a "hydraulic damping" coefficient (N*s/m) set by needle geometry
    and insulin viscosity. Plunger inertia is neglected (it is tiny compared
    with the viscous and friction forces).

Usage:
    python simulate_injections.py                  # 200 trials per scenario
    python simulate_injections.py --n 500 --seed 7
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Sampling configuration
# --------------------------------------------------------------------------
FS_HZ = 50                       # sensor sampling rate
DT = 1.0 / FS_HZ                 # seconds per sample
WINDOW_S = 12.0                  # length of each recorded injection
N_SAMPLES = int(WINDOW_S * FS_HZ)
TIME = np.arange(N_SAMPLES) * DT

# --------------------------------------------------------------------------
# Device / fluid parameters (typical insulin pen values)
# --------------------------------------------------------------------------
PLUNGER_DIAMETER_M = 9.4e-3                     # 3 mL cartridge bore
PLUNGER_AREA_M2 = np.pi * (PLUNGER_DIAMETER_M / 2) ** 2
NEEDLE_RADIUS_M = 0.133e-3 / 2                  # 31G needle inner radius
NEEDLE_LENGTH_M = 6e-3                          # needle + hub, effective length
VISCOSITY_PA_S = 1.1e-3                         # insulin solution ~ water

DOSE_UNITS = 20                                 # target dose (U-100 insulin)
UNITS_PER_ML = 100
DOSE_VOLUME_M3 = DOSE_UNITS / UNITS_PER_ML * 1e-6
TRAVEL_M = DOSE_VOLUME_M3 / PLUNGER_AREA_M2     # plunger travel for full dose
TRAVEL_MM = TRAVEL_M * 1e3

# c = 8*mu*L*A^2 / (pi*r^4)   [N*s/m]
HYDRAULIC_DAMPING = (
    8 * VISCOSITY_PA_S * NEEDLE_LENGTH_M * PLUNGER_AREA_M2 ** 2
) / (np.pi * NEEDLE_RADIUS_M ** 4)

SCENARIOS = ("normal", "fast_injection", "premature_release")


# --------------------------------------------------------------------------
# Building blocks
# --------------------------------------------------------------------------
def _smooth_noise(rng: np.random.Generator, width: int = 25) -> np.ndarray:
    """Slow, unit-variance noise used to mimic a wobbling thumb."""
    noise = np.convolve(rng.normal(0, 1, N_SAMPLES), np.ones(width) / width, mode="same")
    return noise / noise.std()


def _applied_force(rng, f_plateau, t_start, ramp_s, overshoot_frac) -> np.ndarray:
    """Thumb force vs time: smooth ramp -> plateau (+ optional overshoot spike)."""
    s = np.clip((TIME - t_start) / ramp_s, 0.0, 1.0)
    force = f_plateau * (3 * s**2 - 2 * s**3)                       # smoothstep ramp

    sigma = rng.uniform(0.12, 0.25)                                 # spike width (s)
    spike = np.exp(-0.5 * ((TIME - (t_start + ramp_s)) / sigma) ** 2)
    force += overshoot_frac * f_plateau * spike * s

    force += 0.03 * f_plateau * _smooth_noise(rng) * s              # hand wobble
    return force


def _apply_release(force: np.ndarray, t_release: float, tau: float = 0.08) -> np.ndarray:
    """Thumb lifts off: force decays exponentially to zero after t_release."""
    envelope = np.where(TIME <= t_release, 1.0, np.exp(-(TIME - t_release) / tau))
    return force * envelope


def _integrate_plunger(force: np.ndarray, f_fric: float):
    """
    Step the plunger forward in time.
    v = max(F - F_friction, 0) / c ; motion stops at the dose-stop (full travel).
    Returns velocity [m/s] and position [m].
    """
    velocity = np.zeros_like(force)
    position = np.zeros_like(force)
    pos = 0.0
    for i, f in enumerate(force):
        if pos < TRAVEL_M:
            v = max(f - f_fric, 0.0) / HYDRAULIC_DAMPING
            pos = min(pos + v * DT, TRAVEL_M)
            velocity[i] = v
        position[i] = pos
    return velocity, position


# --------------------------------------------------------------------------
# One injection
# --------------------------------------------------------------------------
def generate_trial(scenario: str, rng: np.random.Generator):
    """Return (signals DataFrame, metadata dict) for a single injection."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")

    f_fric = rng.normal(3.0, 0.35)          # stopper friction varies pen to pen (N)
    t_start = rng.uniform(0.4, 1.0)         # when the user starts pressing (s)
    ramp_s = rng.uniform(0.3, 0.8)          # how quickly force builds (s)

    if scenario == "fast_injection":
        v_target = rng.uniform(0.9, 3.0) * 1e-3     # m/s  (0.9 - 3.0 mm/s)
        overshoot = rng.uniform(0.10, 0.80)         # force spike (some are mild)
    else:
        v_target = rng.uniform(0.35, 1.1) * 1e-3    # m/s  (0.35 - 1.1 mm/s, brisk-but-OK press)
        overshoot = rng.uniform(0.0, 0.25)          # natural overshoot

    # Force needed to hold the desired plunger speed: friction + viscous load
    f_plateau = f_fric + HYDRAULIC_DAMPING * v_target
    force = _applied_force(rng, f_plateau, t_start, ramp_s, overshoot)

    # Pass 1: when would the dose finish if the user never let go?
    _, pos_free = _integrate_plunger(force, f_fric)
    done = np.flatnonzero(pos_free >= TRAVEL_M)
    t_done = TIME[done[0]] if done.size else WINDOW_S

    # Decide when the thumb comes off the button
    if scenario == "premature_release":
        t_release = t_start + rng.uniform(0.3, 0.97) * (t_done - t_start)
    else:
        t_release = t_done + rng.uniform(0.5, 2.5)  # needle "hold" after dose

    force = _apply_release(force, t_release)

    # Pass 2: final plunger motion with the real force profile
    velocity, position = _integrate_plunger(force, f_fric)
    delivered_pct = position[-1] / TRAVEL_M * 100

    # ---- Sensor model: noise, tremor, calibration error ----
    tremor_hz = rng.uniform(6, 10)
    amplitude = np.clip(force / f_plateau, 0, 1)
    tremor = 0.08 * np.sin(2 * np.pi * tremor_hz * TIME + rng.uniform(0, 2 * np.pi)) * amplitude
    force_meas = np.clip(force + tremor + rng.normal(0, 0.08, N_SAMPLES), 0, None)

    encoder_gain = rng.normal(1.0, 0.02)                                 # +/-2 % calibration
    velocity_meas = velocity * 1e3 * encoder_gain + rng.normal(0, 0.03, N_SAMPLES)  # mm/s
    position_meas = np.cumsum(velocity_meas) * DT                         # firmware estimate (mm)

    signals = pd.DataFrame(
        {
            "time_s": TIME,
            "force_N": force_meas,
            "velocity_mm_s": velocity_meas,
            "position_mm": position_meas,
        }
    )
    meta = {
        "scenario": scenario,
        "is_successful": int(scenario == "normal"),
        "true_dose_delivered_pct": round(delivered_pct, 2),
    }
    return signals, meta


# --------------------------------------------------------------------------
# Dataset
# --------------------------------------------------------------------------
def generate_dataset(n_per_scenario: int = 200, seed: int = 42):
    """Generate a labelled dataset (long format) and a per-trial metadata table."""
    rng = np.random.default_rng(seed)
    frames, metas = [], []
    trial_id = 0
    for scenario in SCENARIOS:
        for _ in range(n_per_scenario):
            signals, meta = generate_trial(scenario, rng)
            signals.insert(0, "trial_id", trial_id)
            signals["scenario"] = meta["scenario"]
            signals["is_successful"] = meta["is_successful"]
            frames.append(signals)
            metas.append({"trial_id": trial_id, **meta})
            trial_id += 1
    return pd.concat(frames, ignore_index=True), pd.DataFrame(metas)


def plot_examples(seed: int, out_path: Path) -> None:
    """Save a figure with one example of each scenario (great for the README)."""
    rng = np.random.default_rng(seed)
    titles = {
        "normal": "Normal / optimal",
        "fast_injection": "Too fast (force spike)",
        "premature_release": "Premature release",
    }
    colors = {"normal": "tab:green", "fast_injection": "tab:red", "premature_release": "tab:orange"}
    fig, axes = plt.subplots(3, 3, figsize=(13, 8), sharex=True)
    for col, scenario in enumerate(SCENARIOS):
        sig, meta = generate_trial(scenario, rng)
        axes[0, col].plot(sig["time_s"], sig["force_N"], color=colors[scenario])
        axes[1, col].plot(sig["time_s"], sig["velocity_mm_s"], color=colors[scenario])
        axes[2, col].plot(sig["time_s"], sig["position_mm"], color=colors[scenario])
        axes[2, col].axhline(TRAVEL_MM, ls="--", color="gray", lw=1)
        axes[0, col].set_title(f"{titles[scenario]}\n(dose delivered: {meta['true_dose_delivered_pct']:.0f}%)")
        axes[2, col].set_xlabel("Time (s)")
    axes[0, 0].set_ylabel("Plunger force (N)")
    axes[1, 0].set_ylabel("Plunger velocity (mm/s)")
    axes[2, 0].set_ylabel("Plunger position (mm)")
    for ax in axes.ravel():
        ax.grid(alpha=0.3)
    fig.suptitle(f"Simulated smart-pen injection profiles (target dose: {DOSE_UNITS} U, dashed = full travel)")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic smart-insulin-pen data.")
    parser.add_argument("--n", type=int, default=200, help="trials per scenario")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    data, meta = generate_dataset(args.n, args.seed)

    (root / "data").mkdir(exist_ok=True)
    data.to_csv(root / "data" / "injection_dataset.csv", index=False)
    meta.to_csv(root / "data" / "trial_metadata.csv", index=False)
    plot_examples(args.seed, root / "figures" / "sample_injection_profiles.png")

    print(f"Hydraulic damping c      : {HYDRAULIC_DAMPING:,.0f} N*s/m")
    print(f"Plunger travel for {DOSE_UNITS} U : {TRAVEL_MM:.2f} mm")
    print(f"Trials generated         : {meta.shape[0]} ({args.n} per scenario)")
    print(f"Rows in dataset          : {data.shape[0]:,}")
    print("\nTrue dose delivered (%) by scenario:")
    print(meta.groupby("scenario")["true_dose_delivered_pct"].describe()[["mean", "min", "max"]].round(1))
    print(f"\nSaved to {root / 'data'} and {root / 'figures'}")


if __name__ == "__main__":
    main()
