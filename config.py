import time

class Config:
    def __init__(self):
        # =========================
        # SIMULATION MODE
        # =========================
        self.SIMULATION_MODE = "grid"
        self.LAYOUT_STYLE = "maze"

        # =========================
        # ENVIRONMENT SETTINGS
        # =========================
        self.GRID_WIDTH = 30
        self.GRID_HEIGHT = 30
        self.CELL_SIZE = 1.0

        # Urban map parameters
        self.BUILDING_DENSITY = 0.3
        self.GAP_PROBABILITY = 0.1

        # =========================
        # AGENT SETTINGS
        # =========================
        self.NUM_DRONES = 10
        self.SENSOR_RANGE = 3

        # COMMUNICATION
        self.COMMUNICATION_RANGE = 5
        self.COMMUNICATION_REQUIRE_LINE_OF_SIGHT = False
        self.COMMUNICATION_PACKET_LOSS = 0.0
        self.COMMUNICATION_DELAY_STEPS = 0
        self.MESSAGE_MAP_LIMIT = 120
        self.MESSAGE_EXPLORED_LIMIT = 120
        self.MESSAGE_VISITED_LIMIT = 120
        self.STUCK_WINDOW_STEPS = 12
        self.STUCK_MIN_UNIQUE_CELLS = 3
        self.STUCK_PROGRESS_STEPS = 10
        
        # MOTION AND ENV
        self.MAX_SPEED = 0.45
        self.AGENT_RADIUS = 0.18
        self.RESCUE_RADIUS = 0.35

        # BATTERY
        self.MAX_BATTERY = 100.0
        self.LOW_BATTERY_THRESHOLD = 20.0
        self.BATTERY_GRID_MOVE_COST = 0.1 #0.25
        self.BATTERY_CONTINUOUS_MOVE_COST = 0.1 #0.6
        self.BATTERY_IDLE_COST = 0.002
        self.BATTERY_COMMUNICATION_COST = 0.01
        self.BATTERY_RESCUE_COST = 0.15

        # SENSOR
        self.LIDAR_RANGE = 6.0
        self.LIDAR_NUM_RAYS = 61
        self.SEMANTIC_RANGE = 4.0
        self.FLOORPLAN_LIDAR_RANGE = 3.5
        self.FLOORPLAN_LIDAR_NUM_RAYS = 41
        self.FLOORPLAN_SEMANTIC_RANGE = 2.0
        self.GPS_NOISE_STD = 0.04
        self.COMPASS_NOISE_STD = 0.03
        self.ODOMETER_NOISE_STD = 0.02

        # =========================
        # UTILITY WEIGHTS
        # =========================
        self.ALPHA = 1.0   # movement
        self.BETA = 1.2    # distance cost
        self.GAMMA = 2.5   # exploration
        self.DELTA = 3.0   # victim
        self.MU = 1.5 # coordinate
        self.LAMBDA = 2.0  # collision risk

        # =========================
        # SIMULATION SETTINGS
        # =========================
        self.RANDOM_SEED = int(time.time())%1234
        self.MAP_RANDOM_SEED = self.RANDOM_SEED + 1
        self.COMMUNICATION_RANDOM_SEED = self.RANDOM_SEED + 2
        self.SENSOR_RANDOM_SEED = self.RANDOM_SEED + 3
        self.MAX_STEPS = 1000
        self.SHOW_METRICS_DASHBOARD = False
        self.SHOW_CONTROL_PANEL = True
        self.TRACE_LOGGING_ENABLED = True
        self.TRACE_LOG_PATH = "logs/agent_trace.jsonl"
        self.TRACE_LOG_TO_CONSOLE = False
        self.METRICS_LOGGING_ENABLED = True
        self.METRICS_LOG_PATH = "logs/mission_metrics.jsonl"

        # =========================
        # SENSOR NOISE (optional)
        # =========================
        self.FALSE_POSITIVE_RATE = 0.05
        self.FALSE_NEGATIVE_RATE = 0.1
        self.VICTIM_CONFIRMATION_STEPS = 2

        # =========================
        # SPECIAL ZONES
        # =========================
        self.NO_COM_ZONE_COUNT = 2
        self.NO_COM_ZONE_MIN_SIZE = 3
        self.NO_COM_ZONE_MAX_SIZE = 7

        # =========================
        # DRONE FAILURE SETTINGS
        # =========================
        self.ENABLE_DRONE_FAILURES = True
        self.FAILED_DRONE_COUNT = 2
        self.FAILURE_START_STEP = 20
        self.FAILURE_END_STEP = 120
        self.FAILURE_RANDOM_SEED = self.RANDOM_SEED + 4
