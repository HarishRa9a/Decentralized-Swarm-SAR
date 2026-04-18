import math

class UtilityModel:
    def __init__(self, config):
        self.alpha = config.ALPHA
        self.beta = config.BETA
        self.gamma = config.GAMMA
        self.delta = config.DELTA
        self.epsilon = config.MU
        self.lmbda = config.LAMBDA  # victim weight

    # ------------------------------

    def evaluate(self, agent, action, belief):
        x, y = action

        exploration = self.exploration_gain(action, belief)
        distance = self.distance_cost(agent.position, action)
        risk = self.collision_risk(action, belief)
        overlap = self.overlap_penalty(action, belief)
        battery = self.battery_cost(agent)

        victim_reward = self.victim_reward(action, belief)

        return (
            self.alpha * exploration
            + self.lmbda * victim_reward
            - self.beta * distance
            - self.gamma * risk
            - self.delta * overlap
            - self.epsilon * battery
        )

    # ------------------------------

    def exploration_gain(self, action, belief):
        return 1 if action not in belief.explored else 0

    def distance_cost(self, current, action):
        return abs(current[0] - action[0]) + abs(current[1] - action[1])

    def collision_risk(self, action, belief):
        return 1 if belief.grid.get(action) == 1 else 0  # WALL

    def overlap_penalty(self, action, belief):
        return 1 if action in belief.explored else 0

    def battery_cost(self, agent):
        return (100 - agent.battery) / 100

    def victim_reward(self, action, belief):
        if action in belief.victims:
            return 10
        return 0