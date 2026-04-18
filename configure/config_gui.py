import tkinter as tk
from tkinter import messagebox, ttk


FIELD_GROUPS = [
    (
        "Simulation",
        [
            (
                "Simulation mode",
                "SIMULATION_PRESET",
                "choice",
                ["Floorplan (continuous)", "Grid (maze)"],
            ),
            ("Random seed", "RANDOM_SEED", "int"),
            ("Max steps", "MAX_STEPS", "int"),
            ("Show metrics dashboard", "SHOW_METRICS_DASHBOARD", "bool"),
        ],
    ),
    (
        "Environment",
        [
            ("Grid width", "GRID_WIDTH", "int"),
            ("Grid height", "GRID_HEIGHT", "int"),
            ("Cell size", "CELL_SIZE", "float"),
            ("Building density", "BUILDING_DENSITY", "float"),
            ("Gap probability", "GAP_PROBABILITY", "float"),
            ("No-com zones", "NO_COM_ZONE_COUNT", "int"),
        ],
    ),
    (
        "Drones",
        [
            ("Number of drones", "NUM_DRONES", "int"),
            ("Sensor range", "SENSOR_RANGE", "int"),
            ("Communication range", "COMMUNICATION_RANGE", "float"),
            ("Require comm line-of-sight", "COMMUNICATION_REQUIRE_LINE_OF_SIGHT", "bool"),
            ("Communication packet loss", "COMMUNICATION_PACKET_LOSS", "float"),
            ("Communication delay steps", "COMMUNICATION_DELAY_STEPS", "int"),
            ("Max battery", "MAX_BATTERY", "float"),
            ("Low battery threshold", "LOW_BATTERY_THRESHOLD", "float"),
        ],
    ),
    (
        "Sensors",
        [
            ("Lidar range", "LIDAR_RANGE", "float"),
            ("Lidar rays", "LIDAR_NUM_RAYS", "int"),
            ("Semantic range", "SEMANTIC_RANGE", "float"),
            ("Floorplan lidar range", "FLOORPLAN_LIDAR_RANGE", "float"),
            ("Floorplan lidar rays", "FLOORPLAN_LIDAR_NUM_RAYS", "int"),
            ("Floorplan semantic range", "FLOORPLAN_SEMANTIC_RANGE", "float"),
            ("GPS noise", "GPS_NOISE_STD", "float"),
            ("Compass noise", "COMPASS_NOISE_STD", "float"),
            ("Odometer noise", "ODOMETER_NOISE_STD", "float"),
            ("False positive rate", "FALSE_POSITIVE_RATE", "float"),
            ("False negative rate", "FALSE_NEGATIVE_RATE", "float"),
            ("Victim confirmation steps", "VICTIM_CONFIRMATION_STEPS", "int"),
        ],
    ),
    (
        "Drone Failures",
        [
            ("Enable drone failures", "ENABLE_DRONE_FAILURES", "bool"),
            ("Failed drone count", "FAILED_DRONE_COUNT", "int"),
            ("Failure start step", "FAILURE_START_STEP", "int"),
            ("Failure end step", "FAILURE_END_STEP", "int"),
        ],
    ),
]


RATE_FIELDS = {
    "BUILDING_DENSITY",
    "GAP_PROBABILITY",
    "COMMUNICATION_PACKET_LOSS",
    "FALSE_POSITIVE_RATE",
    "FALSE_NEGATIVE_RATE",
}


NON_NEGATIVE_FIELDS = {
    "GRID_WIDTH",
    "GRID_HEIGHT",
    "CELL_SIZE",
    "MAX_STEPS",
    "RANDOM_SEED",
    "NUM_DRONES",
    "SENSOR_RANGE",
    "COMMUNICATION_RANGE",
    "COMMUNICATION_DELAY_STEPS",
    "MAX_BATTERY",
    "LOW_BATTERY_THRESHOLD",
    "LIDAR_RANGE",
    "LIDAR_NUM_RAYS",
    "SEMANTIC_RANGE",
    "FLOORPLAN_LIDAR_RANGE",
    "FLOORPLAN_LIDAR_NUM_RAYS",
    "FLOORPLAN_SEMANTIC_RANGE",
    "GPS_NOISE_STD",
    "COMPASS_NOISE_STD",
    "ODOMETER_NOISE_STD",
    "VICTIM_CONFIRMATION_STEPS",
    "NO_COM_ZONE_COUNT",
    "FAILED_DRONE_COUNT",
    "FAILURE_START_STEP",
    "FAILURE_END_STEP",
}


def configure_with_gui(config):
    root = tk.Tk()
    root.title("Swarm SAR Configuration")
    root.geometry("620x760")

    variables = {}
    result = {"started": False}

    container = ttk.Frame(root, padding=12)
    container.pack(fill="both", expand=True)

    canvas = tk.Canvas(container, highlightthickness=0)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)

    scroll_frame.bind(
        "<Configure>",
        lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    for group_name, fields in FIELD_GROUPS:
        group = ttk.LabelFrame(scroll_frame, text=group_name, padding=10)
        group.pack(fill="x", expand=True, padx=4, pady=6)

        for row, (label, attr, field_type, *options) in enumerate(fields):
            ttk.Label(group, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=4)
            value = _default_value(config, attr)

            if field_type == "bool":
                variable = tk.BooleanVar(value=bool(value))
                widget = ttk.Checkbutton(group, variable=variable)
            elif field_type == "choice":
                choices = options[0]
                variable = tk.StringVar(value=str(value))
                widget = ttk.Combobox(
                    group,
                    textvariable=variable,
                    values=choices,
                    state="readonly",
                    width=22,
                )
            else:
                variable = tk.StringVar(value=str(value))
                widget = ttk.Entry(group, textvariable=variable, width=25)

            widget.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
            variables[attr] = (variable, field_type)

        group.columnconfigure(1, weight=1)

    button_bar = ttk.Frame(root, padding=12)
    button_bar.pack(fill="x")

    def apply_values():
        try:
            parsed = _parse_values(variables)
            _apply_simulation_preset(parsed)
            _apply_derived_random_seeds(parsed)
            _validate_values(parsed)
        except ValueError as error:
            messagebox.showerror("Invalid configuration", str(error))
            return

        for attr, value in parsed.items():
            if attr == "SIMULATION_PRESET":
                continue
            setattr(config, attr, value)

        result["started"] = True
        root.destroy()

    def cancel():
        result["started"] = False
        root.destroy()

    ttk.Button(button_bar, text="Start Simulation", command=apply_values).pack(
        side="right",
        padx=4,
    )
    ttk.Button(button_bar, text="Cancel", command=cancel).pack(side="right", padx=4)

    root.protocol("WM_DELETE_WINDOW", cancel)
    root.mainloop()

    return config if result["started"] else None


def _default_value(config, attr):
    if attr == "SIMULATION_PRESET":
        if getattr(config, "SIMULATION_MODE", "grid") == "continuous":
            return "Floorplan (continuous)"
        return "Grid (maze)"
    return getattr(config, attr)


def _parse_values(variables):
    parsed = {}

    for attr, (variable, field_type) in variables.items():
        raw_value = variable.get()

        if field_type == "bool":
            parsed[attr] = bool(raw_value)
        elif field_type == "int":
            parsed[attr] = int(raw_value)
        elif field_type == "float":
            parsed[attr] = float(raw_value)
        else:
            parsed[attr] = raw_value

    return parsed


def _apply_simulation_preset(values):
    preset = values.get("SIMULATION_PRESET", "Grid (maze)")
    if preset == "Floorplan (continuous)":
        values["SIMULATION_MODE"] = "continuous"
        values["LAYOUT_STYLE"] = "floorplan"
        return

    values["SIMULATION_MODE"] = "grid"
    values["LAYOUT_STYLE"] = "maze"


def _apply_derived_random_seeds(values):
    seed = values.get("RANDOM_SEED", 0)
    values["MAP_RANDOM_SEED"] = seed + 1
    values["COMMUNICATION_RANDOM_SEED"] = seed + 2
    values["SENSOR_RANDOM_SEED"] = seed + 3
    values["FAILURE_RANDOM_SEED"] = seed + 4


def _validate_values(values):
    for attr in NON_NEGATIVE_FIELDS:
        if attr in values and values[attr] < 0:
            raise ValueError(f"{attr} must be zero or greater.")

    for attr in RATE_FIELDS:
        if attr in values and not 0.0 <= values[attr] <= 1.0:
            raise ValueError(f"{attr} must be between 0 and 1.")

    if values["NUM_DRONES"] < 1:
        raise ValueError("NUM_DRONES must be at least 1.")

    if values["FAILED_DRONE_COUNT"] > values["NUM_DRONES"]:
        raise ValueError("FAILED_DRONE_COUNT cannot be greater than NUM_DRONES.")

    if values["FAILURE_END_STEP"] < values["FAILURE_START_STEP"]:
        raise ValueError("FAILURE_END_STEP must be greater than or equal to FAILURE_START_STEP.")

    if values["LOW_BATTERY_THRESHOLD"] > values["MAX_BATTERY"]:
        raise ValueError("LOW_BATTERY_THRESHOLD cannot be greater than MAX_BATTERY.")

    if values["SIMULATION_MODE"] == "grid":
        max_spawn_column = (values["NUM_DRONES"] - 1) * 2
        if max_spawn_column >= values["GRID_HEIGHT"]:
            raise ValueError(
                "Grid mode needs GRID_HEIGHT greater than (NUM_DRONES - 1) * 2."
            )
