import random

class GPSSensor:
    def __init__(self, noise_std, rng=None):
        self.noise_std = noise_std
        self.rng = rng or random.Random()
        self._bias = (0.0, 0.0)

    def read(self, agent):
        true_x, true_y = agent.world_position
        self._bias = (
            0.85 * self._bias[0] + self.rng.gauss(0.0, self.noise_std),
            0.85 * self._bias[1] + self.rng.gauss(0.0, self.noise_std),
        )
        return (true_x + self._bias[0], true_y + self._bias[1])
