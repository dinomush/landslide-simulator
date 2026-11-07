# Validation results

Automated verification uses Python 3 with NumPy for the numerical model and Node.js
for JavaScript checks. The test commands below were rerun successfully.

## Passed

- `python main.py`: completed and wrote all three JSON outputs.
- `python -m unittest discover -s tests -v`: **16 tests passed**.
- `node --check web/app.js`: syntax check passed.
- `node tests/test_web.cjs`: passed data loading, all map layers, direction vectors,
  Play/Pause/Restart/Previous/Next, scrubbing, end-of-playback behavior, invalid data
  rejection and Python/JavaScript FoS agreement using a DOM/canvas stub.
- Headerless CSV input, JSON configuration and `--help` commands executed.
- All generated JSON numbers checked recursively: no NaN or Infinity.
- Default run has 61 frames, including t=0 and t=60 s; replay JSON is 1,041,543 bytes.
- Saturation and unstable cell counts increase monotonically in the rainy demo;
  minimum FoS decreases monotonically.
- Across saved frames, all existing particles stay at the same or lower sampled
  elevation. There were 11,996 observed particle/frame movements.
- Unit tests verify flat/planar gradients, downhill vectors, hydrology units and
  bounds, cohesion/friction/saturation relationships, finite values, boundaries,
  bilinear interpolation, seed reproducibility and the tiny-initial-drive regression.

## Rainfall comparison

Both runs use the same 100 × 100 demo terrain, 24 rainfall hours and 60 motion seconds.

| Metric | 0 mm/h | 80 mm/h |
|---|---:|---:|
| Final saturation | 0.0393 | 0.8077 |
| Minimum FoS | 1.111 | 0.873 |
| Unstable cells | 0 | 978 |
| Unstable area | 0 m² | 24,450 m² |
| Particles | 0 | 600 |
| Maximum velocity | 0 m/s | 1.406 m/s |

Rain increases saturation and therefore pore pressure `u=m γw H cos²θ`, reducing
FoS. Greater cohesion/friction increases FoS. The driving term `g sinθ` increases
with slope for the model's terrain angles (0–90 degrees). Total default particle
travel is 5,266.8 m summed across all particles.

## Manual browser verification

The JavaScript checks use a simulated DOM/canvas environment. They test application
logic but do not verify the visual appearance or interaction in a real browser.

For a manual check, start the local server described in the README, open the
viewer, confirm that the demo loads, and try each map layer, the vector toggle,
Play/Pause, Restart, Previous/Next and the timeline. At the first frame the
default run has no particles; move toward the end to see rainfall-driven failure
and movement. Also verify offline loading by opening `web/index.html` and
selecting `output/simulation.json`.
