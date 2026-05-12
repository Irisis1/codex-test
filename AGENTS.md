# AGENTS.md

## Project role

This repository is used for Capytaine-based linear potential-flow BEM simulations of fixed circular-cylinder ring arrays in waves.

## Environment

Use Python 3.11 if possible.

Preferred installation method:

```bash
conda env create -f environment.yml
conda activate capytaine-codex
```

Alternative installation method:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Main executable script

Run the main simulation script with:

```bash
python run_ring_array.py
```

## Modeling assumptions

- Use linear potential-flow theory.
- Use fixed-body diffraction only.
- The circular cylinders are fixed.
- Keep all dimensions in SI units.
- Use water depth h = 0.60 m.
- Use cylinder radius a = 0.06 m.
- Use cylinder draft d = 0.598 m.
- Use ring radius R = 0.30 m.
- Compare 4, 6, and 8 cylinder arrays under identical probe definitions.

## Probe definitions

Center five points:

```text
P0 = (0.0, 0.0)
P1 = (0.1, 0.0)
P2 = (-0.1, 0.0)
P3 = (0.0, 0.1)
P4 = (0.0, -0.1)
```

Front and rear probes:

```text
front = (-2.0, 0.0)
rear  = ( 2.0, 0.0)
```

## Required outputs

Save numerical results into outputs/.

Save figures into figures/.

## Important restrictions

Do not change physical parameters without explaining why.

Do not silently change normalization definitions.

Do not run the full period sweep unless explicitly requested. For testing, use only a small smoke test such as N=4 and T=1.00 s.
