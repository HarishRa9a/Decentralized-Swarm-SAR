import math
from perception.sensor_utils import wrap_angle

class LidarSensor:
    def __init__(self, lidar_range, num_rays):
        self.lidar_range = lidar_range
        self.num_rays = num_rays

    def read(self, agent, env):
        if self.num_rays <= 1:
            angles = [agent.heading]
        else:
            angles = [
                wrap_angle(agent.heading - math.pi + (2 * math.pi * index) / (self.num_rays - 1))
                for index in range(self.num_rays)
            ]

        lidar = []
        for angle in angles:
            distance = env.raycast_distance(agent.world_position, angle, self.lidar_range)
            lidar.append((angle, distance))
        return lidar
