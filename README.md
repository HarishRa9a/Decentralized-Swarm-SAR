# Swarm SAR Simulation

This project simulates a multi-drone search-and-rescue mission in a grid or continuous urban environment. Drones explore the map, share information, detect victims, handle communication limits, and log mission metrics during the run.

## Project Structure

- `main.py` - Entry point for the simulation.
- `config.py` - Main configuration values for environment size, drones, sensors, rendering, logging, and failures.
- `agents/` - Drone agent behavior, belief state, and utility model.
- `environment/` - Grid/continuous environment generation and entities.
- `perception/` - Sensor models such as GPS, lidar, compass, odometer, and semantic sensing.
- `communication/` - Message broadcasting and map merging.
- `simulation/` - Simulation loop, metrics, and trace logging.
- `visualization/` - Matplotlib-based simulation and metrics renderers.
- `logs/` - Generated trace and metrics output files.

## Requirements

Use Python 3.10 or newer. Install the runtime dependencies:

```bash
pip install numpy matplotlib
```

The `auxp/arcade_renderer.py` file also supports an Arcade renderer experiment. If you want to work with that file, install Arcade too:

```bash
pip install arcade
```

## Run Method

From the `sar` folder, run:

```bash
python main.py
```

The program will ask for two inputs:

```text
Choose movement mode: 1. MAZE (default) / 2. FLOORPLAN
Show metric visuals: 1. YES / 2. NO (default)
```

Run with defaults by pressing Enter for both prompts:

```text
Choose movement mode: 1. MAZE (default) / 2. FLOORPLAN
Show metric visuals: 1. YES / 2. NO (default)
```

Choose floorplan mode and enable metrics:

```text
Choose movement mode: 1. MAZE (default) / 2. FLOORPLAN 2
Show metric visuals: 1. YES / 2. NO (default) 1
```

## Configuration

Most simulation settings are in `config.py`.

Common values to adjust:

- `NUM_DRONES` - Number of drones in the mission.
- `MAX_STEPS` - Maximum simulation steps.
- `RENDER` - Enable or disable visualization.
- `SHOW_METRICS_DASHBOARD` - Show live metric charts.
- `GRID_WIDTH` and `GRID_HEIGHT` - Map size.
- `SENSOR_RANGE`, `LIDAR_RANGE`, `SEMANTIC_RANGE` - Sensor behavior.
- `COMMUNICATION_RANGE` - Drone communication range.
- `ENABLE_DRONE_FAILURES` - Enable scheduled drone failures.

## Outputs

When logging is enabled, the simulation writes:

- `logs/agent_trace.jsonl` - Per-agent trace data.
- `logs/mission_metrics.jsonl` - Mission metrics over time.

These files can be inspected after a run to review coverage, overlap, detections, rescues, communication behavior, and mission summary data.

## Notes

- The default visualization path uses Matplotlib through `visualization/renderer.py`.
- If rendering is slow, set `RENDER = False` in `config.py`.
- If the metrics dashboard is not needed, answer `2` at the metrics prompt or set `SHOW_METRICS_DASHBOARD = False`.
