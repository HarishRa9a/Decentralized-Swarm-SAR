import math
import random

from perception.compass_sensor import CompassSensor
from perception.gps_sensor import GPSSensor
from perception.lidar_sensor import LidarSensor
from perception.odometer_sensor import OdometerSensor
from perception.semantic_sensor import SemanticSensor
from perception.sensor_utils import raytrace_cells
from perception.visibility import is_visible
from utils.constants import FREE, VICTIM, WALL


class SensorSuite:
    def __init__(self, config, agent_id=0):
        self.range = config.SENSOR_RANGE
        if self._uses_floorplan_sensors(config):
            self.lidar_range = getattr(config, "FLOORPLAN_LIDAR_RANGE", 3.5)
            self.lidar_num_rays = getattr(config, "FLOORPLAN_LIDAR_NUM_RAYS", 41)
            self.semantic_range = getattr(config, "FLOORPLAN_SEMANTIC_RANGE", 2.0)
        else:
            self.lidar_range = getattr(config, "LIDAR_RANGE", 6.0)
            self.lidar_num_rays = getattr(config, "LIDAR_NUM_RAYS", 61)
            self.semantic_range = getattr(config, "SEMANTIC_RANGE", 4.0)
        self.gps_noise_std = getattr(config, "GPS_NOISE_STD", 0.04)
        self.compass_noise_std = getattr(config, "COMPASS_NOISE_STD", 0.03)
        self.odometer_noise_std = getattr(config, "ODOMETER_NOISE_STD", 0.02)
        self.false_positive_rate = getattr(config, "FALSE_POSITIVE_RATE", 0.0)
        self.false_negative_rate = getattr(config, "FALSE_NEGATIVE_RATE", 0.0)
        sensor_seed = getattr(config, "SENSOR_RANDOM_SEED", getattr(config, "RANDOM_SEED", 42) + 3)
        seed_offset = int(agent_id) * 1000
        self.gps_sensor = GPSSensor(self.gps_noise_std, random.Random(sensor_seed + seed_offset + 1))
        self.compass_sensor = CompassSensor(self.compass_noise_std, random.Random(sensor_seed + seed_offset + 2))
        self.odometer_sensor = OdometerSensor(self.odometer_noise_std, random.Random(sensor_seed + seed_offset + 3))
        self.lidar_sensor = LidarSensor(self.lidar_range, self.lidar_num_rays)
        self.semantic_sensor = SemanticSensor(
            self.semantic_range,
            self.false_positive_rate,
            self.false_negative_rate,
            random.Random(sensor_seed + seed_offset + 4),
        )

    def _uses_floorplan_sensors(self, config):
        return (
            getattr(config, "SIMULATION_MODE", "grid") == "continuous"
            and getattr(config, "LAYOUT_STYLE", "maze") == "floorplan"
        )

    def scan(self, agent, env):
        if getattr(env, "mode", "grid") == "continuous":
            return self._scan_continuous(agent, env)
        return self._scan_grid(agent.position, env.grid_map, agent)

    def _scan_grid(self, position, grid_map, agent):
        x, y = position
        observations = []

        for dx in range(-self.range, self.range + 1):
            for dy in range(-self.range, self.range + 1):
                nx, ny = x + dx, y + dy

                if not grid_map.in_bounds(nx, ny):
                    continue

                if is_visible((x, y), (nx, ny), grid_map):
                    observations.append((nx, ny, grid_map.get_cell(nx, ny)))

        return {
            "grid_observations": observations,
            "gps_position": agent.grid_to_world(*position),
            "compass_heading": getattr(agent, "heading", 0.0),
            "odometer": {"dist_travel": 0.0, "alpha": 0.0, "theta": 0.0},
            "lidar": [],
            "semantic": [],
        }

    def _scan_continuous(self, agent, env):
        gps_position = self.gps_sensor.read(agent)
        compass_heading = self.compass_sensor.read(agent)
        odometer = self.odometer_sensor.read(agent)
        lidar = self.lidar_sensor.read(agent, env)
        semantic = self.semantic_sensor.read(agent, env)
        grid_observations = self._project_to_grid(agent, env, gps_position, lidar, semantic)

        return {
            "grid_observations": grid_observations,
            "gps_position": gps_position,
            "compass_heading": compass_heading,
            "odometer": odometer,
            "lidar": lidar,
            "semantic": semantic,
        }

    def _project_to_grid(self, agent, env, gps_position, lidar, semantic):
        observations = []
        measured_cell = agent.world_to_grid(*gps_position)
        observations.append((measured_cell[0], measured_cell[1], FREE))

        for angle, distance in lidar:
            obstacle_x = gps_position[0] + distance * math.cos(angle)
            obstacle_y = gps_position[1] + distance * math.sin(angle)
            obstacle_cell = agent.world_to_grid(obstacle_x, obstacle_y)
            ray_cells = raytrace_cells(measured_cell, obstacle_cell)

            if distance >= self.lidar_range - 1e-6:
                for cell in ray_cells:
                    observations.append((cell[0], cell[1], FREE))
            else:
                for cell in ray_cells[:-1]:
                    observations.append((cell[0], cell[1], FREE))
                observations.append((ray_cells[-1][0], ray_cells[-1][1], WALL))

        for item in semantic:
            cell = agent.world_to_grid(*item["position"])
            value = VICTIM if item["entity_type"] == "victim" else FREE
            observations.append((cell[0], cell[1], value))

        dedup = {}
        for x, y, value in observations:
            if not env.grid_map.in_bounds(x, y):
                continue
            dedup[(x, y)] = value

        return [(x, y, value) for (x, y), value in dedup.items()]
