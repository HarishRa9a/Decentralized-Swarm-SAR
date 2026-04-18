import random
from perception.sensor_utils import wrap_angle

class CompassSensor:
    def __init__(self, noise_std, rng=None):
        self.noise_std = noise_std
        self.rng = rng or random.Random()

    def read(self, agent):
        return wrap_angle(agent.heading + self.rng.gauss(0.0, self.noise_std))
