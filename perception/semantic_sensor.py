import math
import random


class SemanticSensor:
    def __init__(self, sensor_range, false_positive_rate=0.0, false_negative_rate=0.0, rng=None):
        self.sensor_range = sensor_range
        self.false_positive_rate = false_positive_rate
        self.false_negative_rate = false_negative_rate
        self.rng = rng or random.Random()

    def read(self, agent, env):
        detections = []

        for victim in env.victims:
            if victim.rescued:
                continue
            detection = self._detect(agent.world_position, victim.position, "victim", env)
            if detection is not None:
                if self.rng.random() < self.false_negative_rate:
                    continue
                detections.append(detection)

        for other in env.agents:
            if other.id == agent.id:
                continue
            detection = self._detect(agent.world_position, other.world_position, "drone", env)
            if detection is not None:
                detection["id"] = other.id
                detections.append(detection)

        false_detection = self._false_positive(agent, env, detections)
        if false_detection is not None:
            detections.append(false_detection)

        return detections

    def _detect(self, origin, target, entity_type, env):
        dx = target[0] - origin[0]
        dy = target[1] - origin[1]
        distance = math.hypot(dx, dy)
        if distance > self.sensor_range:
            return None
        if not env.line_of_sight_clear(origin, target):
            return None

        return {
            "entity_type": entity_type,
            "distance": distance,
            "angle": math.atan2(dy, dx),
            "position": target,
        }

    def _false_positive(self, agent, env, detections):
        if self.false_positive_rate <= 0.0:
            return None
        if self.rng.random() >= self.false_positive_rate:
            return None

        seen_positions = {
            tuple(item["position"])
            for item in detections
            if item["entity_type"] == "victim"
        }
        candidates = []
        origin = agent.world_position

        for x in range(env.grid_map.height):
            for y in range(env.grid_map.width):
                if not env.grid_map.is_free(x, y):
                    continue

                world_position = agent.grid_to_world(x, y)
                dx = world_position[0] - origin[0]
                dy = world_position[1] - origin[1]
                distance = math.hypot(dx, dy)
                if distance > self.sensor_range:
                    continue
                if not env.line_of_sight_clear(origin, world_position):
                    continue
                if world_position in seen_positions:
                    continue

                candidates.append((world_position, distance, math.atan2(dy, dx)))

        if not candidates:
            return None

        world_position, distance, angle = self.rng.choice(candidates)
        return {
            "entity_type": "victim",
            "distance": distance,
            "angle": angle,
            "position": world_position,
            "false_positive": True,
        }
