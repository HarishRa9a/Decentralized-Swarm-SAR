class DroneState:
    def __init__(self, config):
        self.max_battery = float(getattr(config, "MAX_BATTERY", 100.0))
        self.low_battery_threshold = float(getattr(config, "LOW_BATTERY_THRESHOLD", 20.0))
        self.grid_move_cost = float(getattr(config, "BATTERY_GRID_MOVE_COST", 1.0))
        self.continuous_move_cost = float(getattr(config, "BATTERY_CONTINUOUS_MOVE_COST", 2.0))
        self.idle_cost = float(getattr(config, "BATTERY_IDLE_COST", 0.02))
        self.communication_cost = float(getattr(config, "BATTERY_COMMUNICATION_COST", 0.05))
        self.rescue_cost = float(getattr(config, "BATTERY_RESCUE_COST", 0.5))
        self.battery = self.max_battery
        self.failed = False
        self.failure_reason = None
        self.failed_at_step = None
        self.stuck_window_steps = max(2, int(getattr(config, "STUCK_WINDOW_STEPS", 12)))
        self.stuck_min_unique_cells = max(1, int(getattr(config, "STUCK_MIN_UNIQUE_CELLS", 3)))
        self.stuck_progress_steps = max(1, int(getattr(config, "STUCK_PROGRESS_STEPS", 10)))
        self.recent_positions = []
        self.last_explored_count = 0
        self.steps_without_progress = 0
        self.is_stuck = False
        self.stuck_reason = None

    @property
    def is_active(self):
        return (not self.failed) and self.battery > 0.0

    @property
    def is_failed(self):
        return self.failed

    def battery_ratio(self):
        if self.max_battery <= 0.0:
            return 0.0
        return max(0.0, self.battery) / self.max_battery

    def is_low_battery(self):
        return self.battery <= self.low_battery_threshold

    def consume_battery(self, amount):
        if amount <= 0:
            return
        self.battery = max(0.0, self.battery - amount)

    def fail(self, timestep=None, reason="forced_failure"):
        self.failed = True
        self.failure_reason = reason
        self.failed_at_step = timestep

    def record_progress(self, position, explored_count):
        self.recent_positions.append(position)
        if len(self.recent_positions) > self.stuck_window_steps:
            self.recent_positions.pop(0)

        if explored_count > self.last_explored_count:
            self.steps_without_progress = 0
            self.last_explored_count = explored_count
        else:
            self.steps_without_progress += 1

        unique_positions = len(set(self.recent_positions))
        position_stuck = (
            len(self.recent_positions) >= self.stuck_window_steps
            and unique_positions < self.stuck_min_unique_cells
        )
        progress_stuck = self.steps_without_progress >= self.stuck_progress_steps

        self.is_stuck = position_stuck or progress_stuck
        if position_stuck:
            self.stuck_reason = "low_position_diversity"
        elif progress_stuck:
            self.stuck_reason = "no_exploration_progress"
        else:
            self.stuck_reason = None

        return self.is_stuck
