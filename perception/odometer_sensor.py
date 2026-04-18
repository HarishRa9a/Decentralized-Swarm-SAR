import math
import random

from perception.sensor_utils import wrap_angle


class OdometerSensor:
    def __init__(self, noise_std, rng=None):
        self.noise_std = noise_std
        self.rng = rng or random.Random()

    def read(self, agent):
        previous = getattr(agent, "last_world_position", agent.world_position)
        dx = agent.world_position[0] - previous[0]
        dy = agent.world_position[1] - previous[1]
        distance = math.hypot(dx, dy) + self.rng.gauss(0.0, self.noise_std)
        alpha = wrap_angle(math.atan2(dy, dx) if abs(dx) + abs(dy) > 1e-9 else agent.heading)
        theta = wrap_angle(agent.heading - getattr(agent, "last_heading", agent.heading))

        return {
            "dist_travel": max(0.0, distance),
            "alpha": alpha,
            "theta": theta + self.rng.gauss(0.0, self.noise_std),
        }
