import tkinter as tk
from tkinter import ttk
import time
from utils.constants import VICTIM, WALL


COLOR_UNKNOWN = "#eee5d2"
COLOR_EXPLORED = "#d7eef7"
COLOR_SENSED = "#f5d76e"
COLOR_WALL = "#2f3b45"
COLOR_VICTIM = "#c84646"
COLOR_DRONE = "#087f75"
COLOR_FAILED = "#737373"
COLOR_NO_COM = "#e6b267"
COLOR_GRID_LINE = "#000000"


class SimulationControlPanel:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Swarm SAR Simulation")
        self.root.geometry("1180x690")
        self.running = False
        self.step_requested = False
        self.stop_requested = False
        self.closed = False
        self._stat_vars = {}
        self.canvas = None

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._build()

    def _build(self):
        container = ttk.Frame(self.root, padding=10)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg="#eee6d3", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True, padx=(0, 14))

        sidebar = ttk.Frame(container, width=350)
        sidebar.pack(side="right", fill="y")
        sidebar.pack_propagate(False)

        title = ttk.Label(sidebar, text="Simulation Controls", font=("Segoe UI", 14, "bold"))
        title.pack(anchor="w", pady=(0, 10))

        buttons = ttk.Frame(sidebar)
        buttons.pack(fill="x")

        ttk.Button(buttons, text="Start", command=self.start).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ttk.Button(buttons, text="Pause", command=self.pause).pack(side="left", expand=True, fill="x", padx=6)
        ttk.Button(buttons, text="Step", command=self.step_once).pack(side="left", expand=True, fill="x", padx=(6, 0))
        ttk.Button(sidebar, text="Reset / Stop", command=self.request_stop).pack(fill="x", pady=(8, 16))

        stats_frame = ttk.LabelFrame(sidebar, text="Stats", padding=10)
        stats_frame.pack(fill="both", expand=True)

        for row, key in enumerate(
            [
                "Status",
                "Step",
                "Coverage",
                "Explored",
                "Victims Rescued",
                "Victims Detected",
                "False Detections",
                "Overlap",
                "Repeated Visits",
                "Active Drones",
                "Failed Drones",
            ]
        ):
            ttk.Label(stats_frame, text=f"{key}:").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
            value = tk.StringVar(value="-")
            ttk.Label(stats_frame, textvariable=value).grid(row=row, column=1, sticky="w", pady=2)
            self._stat_vars[key] = value

        stats_frame.columnconfigure(1, weight=1)
        self._stat_vars["Status"].set("Ready")

        self._build_legend(sidebar)

    def _build_legend(self, parent):
        legend = ttk.LabelFrame(parent, text="Color Index", padding=10)
        legend.pack(fill="x", pady=(10, 0))

        items = [
            ("Unexplored", COLOR_UNKNOWN),
            ("Explored", COLOR_EXPLORED),
            ("Sensed now", COLOR_SENSED),
            ("Wall", COLOR_WALL),
            ("Victim", COLOR_VICTIM),
            ("Drone", COLOR_DRONE),
            ("Failed drone", COLOR_FAILED),
        ]

        for row, (label, color) in enumerate(items):
            swatch = tk.Canvas(legend, width=18, height=14, highlightthickness=1, highlightbackground=COLOR_GRID_LINE)
            swatch.create_rectangle(0, 0, 18, 14, fill=color, outline=COLOR_GRID_LINE)
            swatch.grid(row=row, column=0, sticky="w", pady=2, padx=(0, 8))
            ttk.Label(legend, text=label).grid(row=row, column=1, sticky="w", pady=2)

    def start(self):
        self.running = True

    def pause(self):
        self.running = False

    def step_once(self):
        self.step_requested = True
        self.running = False

    def request_stop(self):
        self.stop_requested = True
        self.running = False
        self._stat_vars["Status"].set("Stopping")

    def close(self):
        self.closed = True
        self.stop_requested = True
        self.root.destroy()

    def should_advance(self):
        if self.running:
            return True
        if self.step_requested:
            self.step_requested = False
            return True
        return False

    def update(self, simulator):
        if self.closed:
            return

        self.draw_map(simulator.env, simulator.agents)
        latest = simulator.metrics.latest()
        total_cells = simulator.env.grid_map.width * simulator.env.grid_map.height
        explored = int(round(latest.get("coverage_all_cells", 0.0) * total_cells))
        active = sum(1 for agent in simulator.agents if agent.is_active)
        failed = sum(1 for agent in simulator.agents if agent.failed)

        status = "Running" if self.running else "Paused"
        if self.stop_requested:
            status = "Stopping"

        values = {
            "Status": status,
            "Step": simulator.step_count,
            "Coverage": f"{latest.get('coverage', 0.0) * 100:.2f}%",
            "Explored": f"{explored}/{total_cells}",
            "Victims Rescued": f"{latest.get('rescued_victims', 0)}/{simulator.env.total_victims}",
            "Victims Detected": latest.get("detected_victims", 0),
            "False Detections": latest.get("false_positives", 0),
            "Overlap": f"{latest.get('overlap', 0.0) * 100:.2f}%",
            "Repeated Visits": latest.get("repeated_visits", 0),
            "Active Drones": active,
            "Failed Drones": failed,
        }

        for key, value in values.items():
            self._stat_vars[key].set(str(value))

        self.root.update_idletasks()
        self.root.update()
        time.sleep(0)

    def draw_map(self, env, agents):
        if self.canvas is None:
            return

        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())

        if getattr(env, "mode", "grid") == "continuous":
            self._draw_continuous(env, agents, width, height)
        else:
            self._draw_grid(env, agents, width, height)

    def _draw_grid(self, env, agents, width, height):
        grid_map = env.grid_map
        rows = grid_map.height
        cols = grid_map.width
        cell = min(width / max(cols, 1), height / max(rows, 1))
        x_offset = (width - cols * cell) / 2
        y_offset = (height - rows * cell) / 2
        explored = self._team_explored(agents)
        sensed = self._team_sensed(agents)

        for row in range(rows):
            for col in range(cols):
                value = grid_map.get_cell(row, col)
                if value == WALL:
                    color = COLOR_WALL
                elif value == VICTIM:
                    color = COLOR_VICTIM
                elif (row, col) in sensed:
                    color = COLOR_SENSED
                elif (row, col) in explored:
                    color = COLOR_EXPLORED
                else:
                    color = COLOR_UNKNOWN

                x1 = x_offset + col * cell
                y1 = y_offset + row * cell
                x2 = x1 + cell
                y2 = y1 + cell
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=COLOR_GRID_LINE, width=1)

        radius = max(5, cell * 0.34)
        for agent in agents:
            row, col = agent.position
            cx = x_offset + col * cell + cell / 2
            cy = y_offset + row * cell + cell / 2
            fill = COLOR_FAILED if agent.is_failed else COLOR_DRONE
            self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill=fill, outline="")
            self.canvas.create_text(cx, cy, text="*" if agent.is_failed else str(agent.id), fill="#ffffff", font=("Segoe UI", max(7, int(radius)), "bold"))

    def _draw_continuous(self, env, agents, width, height):
        world_width = max(env.world_width, 1e-6)
        world_height = max(env.world_height, 1e-6)
        scale = min(width / world_width, height / world_height)
        x_offset = (width - world_width * scale) / 2
        y_offset = (height - world_height * scale) / 2
        explored = self._team_explored(agents)
        sensed = self._team_sensed(agents)

        cell_size = getattr(env, "cell_size", 1.0)
        for row in range(env.grid_map.height):
            for col in range(env.grid_map.width):
                x1, y1 = self._world_to_canvas(col * cell_size, row * cell_size, scale, x_offset, y_offset)
                x2, y2 = self._world_to_canvas((col + 1) * cell_size, (row + 1) * cell_size, scale, x_offset, y_offset)
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=COLOR_UNKNOWN, outline="")

        for row, col in explored:
            if not env.grid_map.in_bounds(row, col):
                continue
            if not env.grid_map.can_move(row, col):
                continue

            x1, y1 = self._world_to_canvas(col * cell_size, row * cell_size, scale, x_offset, y_offset)
            x2, y2 = self._world_to_canvas((col + 1) * cell_size, (row + 1) * cell_size, scale, x_offset, y_offset)
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=COLOR_EXPLORED, outline="")

        for row, col in sensed:
            if not env.grid_map.in_bounds(row, col):
                continue
            if not env.grid_map.can_move(row, col):
                continue

            x1, y1 = self._world_to_canvas(col * cell_size, row * cell_size, scale, x_offset, y_offset)
            x2, y2 = self._world_to_canvas((col + 1) * cell_size, (row + 1) * cell_size, scale, x_offset, y_offset)
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=COLOR_SENSED, outline="")

        for zone in getattr(env.playground, "communication_zones", []):
            x1, y1 = self._world_to_canvas(zone.x, zone.y, scale, x_offset, y_offset)
            x2, y2 = self._world_to_canvas(zone.x + zone.width, zone.y + zone.height, scale, x_offset, y_offset)
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=COLOR_NO_COM, outline="#8d5c1f", stipple="gray50")

        for obstacle in env.obstacles:
            x1, y1 = self._world_to_canvas(obstacle.x, obstacle.y, scale, x_offset, y_offset)
            x2, y2 = self._world_to_canvas(obstacle.x + obstacle.width, obstacle.y + obstacle.height, scale, x_offset, y_offset)
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=COLOR_WALL, outline=COLOR_GRID_LINE)

        radius = max(5, getattr(env, "agent_radius", 0.18) * scale)
        for victim in env.victims:
            if victim.rescued:
                continue
            cx, cy = self._world_to_canvas(victim.position[0], victim.position[1], scale, x_offset, y_offset)
            self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill=COLOR_VICTIM, outline="#7f2525")

        for agent in agents:
            x, y = env.get_agent_world_position(agent)
            cx, cy = self._world_to_canvas(x, y, scale, x_offset, y_offset)
            fill = COLOR_FAILED if agent.is_failed else COLOR_DRONE
            self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill=fill, outline="")
            self.canvas.create_text(cx, cy, text="*" if agent.is_failed else str(agent.id), fill="#ffffff", font=("Segoe UI", max(7, int(radius)), "bold"))

    def _world_to_canvas(self, x, y, scale, x_offset, y_offset):
        return x_offset + x * scale, y_offset + y * scale

    def _team_explored(self, agents):
        explored = set()
        for agent in agents:
            if agent.belief is not None:
                explored.update(agent.belief.explored)
        return explored

    def _team_sensed(self, agents):
        sensed = set()
        for agent in agents:
            packet = getattr(agent, "last_sensor_packet", {}) or {}
            for x, y, _value in packet.get("grid_observations", []):
                sensed.add((x, y))
        return sensed

    def destroy(self):
        if not self.closed:
            self.closed = True
            self.root.destroy()
