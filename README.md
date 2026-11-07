# Landslide Risk & Terrain Simulation Tool

A small university project demonstrating matrices, finite differences, gradients,
vectors, derivatives and numerical time integration. Python generates a complete
experiment; a lightweight HTML Canvas viewer replays the saved results.

**This project is a simplified educational model and must not be used as a real-world engineering landslide warning or safety system.**

## Installation

Use Python 3.10 or newer. From this directory:

```sh
python -m pip install -r requirements.txt
```

NumPy is the only required Python package. The web viewer uses standard browser
features and does not require a separate web framework or database.

On Windows, if the Python launcher is available, the same commands can be run
with `py -3` instead of `python`:

```powershell
py -3 -m pip install -r requirements.txt
py -3 main.py
```

## Running the demo

```sh
python main.py
python -m http.server 8000 --bind 127.0.0.1
```

Open **http://localhost:8000/web/**. Leave the server terminal running; Ctrl+C stops it.
The server only serves files. It never runs simulations in response to browser requests.
Default runs use a deterministic 100 × 100 synthetic DEM containing a hill,
steep escarpment and valley. A matching CSV is included in `sample_data/`.

Alternatively, double-click `web/index.html` and use **Select simulation.json** to open
`output/simulation.json`. This offline method avoids the browser's restriction on
fetching sibling files through `file://` URLs.

Select elevation, slope, Factor of Safety, risk or particle layers. Play/Pause,
Restart, Previous, Next and the timeline operate entirely on saved frames. The
direction-vector checkbox adds sparse downhill arrows. White particles are active;
dark particles have stopped. Restart resets replay and does not rerun Python.
Parameters shown in the viewer are read-only; regenerate JSON to change an experiment.

## Running with a custom DEM

```sh
python main.py --dem sample_data/demo_dem.csv --rainfall 40 --duration 60
python main.py --dem sample_data/demo_dem.csv --cell-size 5 --rainfall 80 --rainfall-hours 24 --cohesion 10 --friction-angle 30 --soil-depth 2 --dt 0.2 --output output/custom
python main.py --help
```

A DEM is a rectangular, headerless CSV of finite elevations in **metres**, with at
least two rows and columns. Grid spacing is square and in metres. Missing values,
NaN and Infinity are rejected; nodata must be filled before importing. Maximum
size is 250,000 cells; the intended size is 100–150 cells per side. Coordinates
are x along columns and y along rows, with origin at the top-left; increasing y
points down on the canvas. CSV is the only implemented input format.

Custom output directories do not change the viewer's default URL. Select that
directory's `simulation.json` using the file picker.

## Mathematical model

### Terrain gradient and slope

Elevation is a dense matrix `Z[i,j]`. Grid spacing is `d` metres. Interior finite
differences use:

```text
gx = ∂Z/∂x ≈ (Z[i,j+1] - Z[i,j-1]) / (2d)
gy = ∂Z/∂y ≈ (Z[i+1,j] - Z[i-1,j]) / (2d)
∇Z = [gx, gy]
s = |∇Z| = sqrt(gx² + gy²)
θ = atan(s)
D = -∇Z / s     (D = [0,0] on flat terrain)
```

One-sided differences are used at the boundaries. Slope θ is stored in radians,
and converted to degrees for reports and the slope legend.

### Water saturation

```text
Rm = rainfall_mm_per_hour / 1000                 [m/hour]
dm/dt = kin Rm/H - kd m
m_next = clamp(m + (kin Rm/H - kd m) Δt_h, 0, 1)
```

`m` is saturation (0–1), `kin` is infiltration efficiency (0–1), `H` is soil depth
in metres, `kd` is drainage rate in 1/hour and `Δt_h` is **hours**, not seconds.
Rainfall, soil parameters and initial water content are spatially uniform, so one
saturation scalar represents the whole matrix without duplicating identical data.
The hydrology function also accepts arrays. Large drainage steps are substepped.

**Two explicit clocks:** by default 24 rainfall hours are mapped linearly onto
60 motion seconds. Each outer motion step uses
`Δt_h = Δt_seconds × rainfall_duration_hours / simulation_duration`.
This deliberate time compression makes rainfall effects visible during replay.
It is an illustrative coupling, not a physical 60-second rainfall forecast. Set
`--rainfall-hours` and `--duration` independently. To use matching physical clocks,
set rainfall hours to motion seconds divided by 3600; rainfall effects will then
usually be very small during a short run.

### Factor of Safety

```text
u = m γw H cos²θ
FS = [c + (γs H cos²θ - u) tanφ] / [γs H sinθ cosθ]
```

`c`: cohesion in kPa (kN/m²); `γs`, `γw`: soil/water unit weight in kN/m³;
`H`: soil depth in m; `u`: pore pressure in kPa; `φ`: friction angle, configured
in degrees then converted to radians. FS is dimensionless. A nearly flat cell
gets the finite stable sentinel `flat_fos=1000`. The reported mean FoS includes
these sentinels. A small epsilon protects division.

Default educational risk classes are FS < 1 unstable; 1 ≤ FS < 1.2 high;
1.2 ≤ FS < 1.5 moderate; FS ≥ 1.5 relatively stable. The three visualization
thresholds are configurable and **are not official hazard standards**. Physical
source detection remains FS < 1 even if visualization thresholds are changed.

### Acceleration and integration

```text
a_drive = g sinθ
instability = max(0, 1-FS)
A = a_drive × instability × D - damping × V
V_next = V + A Δt_s
P_next = P + V_next Δt_s
```

`g` is gravity (m/s²); `P=[x,y]` is position (m); `V=[vx,vy]` is velocity (m/s);
`A` is acceleration (m/s²); `Δt_s` is seconds; damping is in 1/s. This is
semi-implicit Euler: the velocity update is explicit, and position uses the new
velocity. Local gradient and FS are sampled bilinearly. The interpolated gradient
sets local θ and D. Internal substeps limit damping error and cell traversal.

Unstable cells release at most one particle each. When a step has more candidate
cells than the remaining budget, sampling is weighted by `1-FS` and uses a seeded
random generator. The total budget is global, so early source cells can consume
it before later cells fail. Particles are markers, not a conserved mass estimate.
Particles damp on stable/flat terrain, stop at small speed when drive vanishes,
stop at the DEM edge and stop on an attempted uphill step. A tiny positive drive
keeps a newly unstable particle eligible to accelerate as rainfall grows. Stopped
particles are not reactivated. Integration ends at the configured duration.

## Input parameters

Central defaults live in `simulator/config.py`. A JSON configuration can override
any field; explicit CLI arguments take precedence:

```sh
python main.py --config sample_data/config.example.json --rainfall 100
```

| Parameter | Default | Units / purpose |
|---|---:|---|
| cell_size | 5 | m, square node spacing |
| rainfall_mm_per_hour | 80 | mm/hour |
| rainfall_duration_hours | 24 | hours of rainfall exposure |
| infiltration_coefficient | 0.9 | dimensionless, 0–1 |
| drainage_coefficient | 0.01 | 1/hour |
| initial_saturation | 0.05 | fraction, 0–1 |
| cohesion | 10 | kPa |
| friction_angle | 30 | degrees, 0 ≤ φ < 90 |
| soil_depth | 2 | m |
| soil_unit_weight | 18 | kN/m³ |
| water_unit_weight | 9.81 | kN/m³ |
| risk_thresholds | [1, 1.2, 1.5] | increasing dimensionless thresholds |
| simulation_dt | 0.2 | outer step, seconds |
| simulation_duration | 60 | motion seconds |
| frame_interval | 1 | seconds between saved frames (at outer step boundaries) |
| particle_count_limit | 600 | maximum markers, allowed 0–2000 |
| damping | 0.6 | 1/second |
| random_seed | 42 | deterministic integer seed |
| gravity | 9.81 | m/s² |
| stop_speed | 0.02 | m/s |
| epsilon | 1e-10 | numerical protection |
| flat_fos | 1000 | stable sentinel for flat terrain |
| max_motion_substep | 0.05 | seconds |

Negative/non-finite parameters are rejected. Soil unit weight must be at least
water unit weight. Very small timesteps or very long runs can exceed the explicit
step/frame limits and are rejected with an explanation. Very high rainfall clamps
saturation at 1. Saturation can fall under little rainfall due to drainage.

## Output files

- `output/simulation.json`: metadata, terrain matrices once, parameters, summary
  and all saved frames. Each frame has time in motion seconds, rainfall hours,
  saturation, minimum FS, unstable/moving counts and compact particle rows.
- `output/risk_map.json`: final FoS matrix, risk matrix, category labels and thresholds.
- `output/summary.json`: elevation/slope statistics, initial/final stability,
  rainfall, unstable count/area, particle count, peak speed and total distance.

Particle columns are `[x, y, vx, vy, active]`; their row index is a persistent ID.
Matrices are row-major nested arrays. `terrain.risk` is the **final** risk matrix.
The viewer uses stored slope, parameters and each frame's saturation to evaluate
the inexpensive FS formula and render time-dependent risk without invoking Python.
Frames do not duplicate terrain or risk matrices. Initial and final frames are
always saved. JSON output rejects NaN/Infinity rather than emitting invalid JSON.
Unstable area is an educational cell-count estimate `count × cell_size²`, not a
surveyed polygon area. Total distance sums all particle travel, not runout length.

## Project structure

```text
landslide_mvp/
  main.py
  requirements.txt
  README.md
  VALIDATION.md
  simulator/
    __init__.py
    config.py
    terrain.py
    hydrology.py
    stability.py
    dynamics.py
    simulation.py
    utils.py
  web/
    index.html
    app.js
    styles.css
  sample_data/
    demo_dem.csv
    config.example.json
  output/
    simulation.json
    risk_map.json
    summary.json
  tests/
    test_terrain.py
    test_hydrology.py
    test_stability.py
    test_simulation.py
    test_web.cjs
```

## Tests

```sh
python -m unittest discover -s tests -v
```

Optional JavaScript unit checks (only for development; Node is not needed to use
the application):

```sh
node --check web/app.js
node tests/test_web.cjs
```

The JavaScript test uses a small in-memory DOM/canvas stub to exercise loading,
replay handlers and layers. It does not replace visual browser testing. See
`VALIDATION.md` for actual results and any outstanding verification.

## Limitations

Constant rainfall; uniform soil/saturation; no groundwater routing, pore-pressure
diffusion, changing terrain, erosion, entrainment, volume conservation, collisions,
deposition physics or georeferencing. Particle acceleration is an illustrative
FoS-weighted rule, not a debris-flow solver. Bilinear sampling, uphill stopping
and irreversible settling are deliberate simplifications. Dense CSV grids and
saved frames are kept small for student laptops. Calibration against real terrain
and observations has not been performed. No engineering or safety claims are made.

