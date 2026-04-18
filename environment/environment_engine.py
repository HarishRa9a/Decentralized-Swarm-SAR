import math
import random
from utils.constants import FREE, VICTIM
from environment.urban_generator import UrbanGenerator


class Environment:
    def __init__(self, config):
        self.config = config

        # GRID STYLE
        self.mode = getattr(config, "SIMULATION_MODE", "grid")
        self.layout_style = getattr(config, "LAYOUT_STYLE", "maze")
        
        # AGENT & ENVIRONMENT
        self.cell_size = getattr(config, "CELL_SIZE", 1.0)
        self.agent_radius = getattr(config, "AGENT_RADIUS", 0.18)
        self.rescue_radius = getattr(config, "RESCUE_RADIUS", 0.35)
        
        # COMMUNICATION 
        self.communication_range = getattr(config, "COMMUNICATION_RANGE", 5.0)
        self.communication_packet_loss = getattr(config,"COMMUNICATION_PACKET_LOSS",0.0,)
        self.communication_require_los = getattr(config,"COMMUNICATION_REQUIRE_LINE_OF_SIGHT",False,)
        self.communication_delay_steps = max(0,int(getattr(config, "COMMUNICATION_DELAY_STEPS", 0)),)

        # GENERATE THE GRID
        self.map_rng = random.Random(getattr(config, "MAP_RANDOM_SEED", getattr(config, "RANDOM_SEED", 42) + 1))
        self.communication_rng = random.Random(
            getattr(config, "COMMUNICATION_RANDOM_SEED", getattr(config, "RANDOM_SEED", 42) + 2)
        )
        self.generator = UrbanGenerator(config, self.map_rng)
        self.reference_map = self.generator.generate_reference_map(self.layout_style,self.cell_size,)
        self.grid_map = self.reference_map.grid_map

        # SET PLAYGROUND AND GET DETAILS
        self.agents = []
        self.playground = self.reference_map.build_playground()
        self.layout = self.playground
        self.obstacles = self.playground.obstacles
        self.victims = self.playground.victims
        self.world_width = self.playground.width
        self.world_height = self.playground.height
        self.total_victims = self.reference_map.count_victims()

    def add_agent(self, agent):
        # ADD AGENT TO LSIT
        self.agents.append(agent)
        agent.env = self

        # FOR CONTINUOUS MODE GET GLOBAL POS
        if self.mode == "continuous":
            agent.cell_size = self.cell_size
            agent.world_position = agent.grid_to_world(*agent.position)
            agent.heading = 0.0

    
    def _circle_intersects_rect(self, cx, cy, radius, bounds):
        min_x, min_y, max_x, max_y = bounds
        nearest_x = min(max(cx, min_x), max_x)
        nearest_y = min(max(cy, min_y), max_y)
        dx = cx - nearest_x
        dy = cy - nearest_y
        return dx * dx + dy * dy < radius * radius

    def resolve_message_delivery(self, sender, receivers, message):
        # RESOLVE WHETHER OR NOT RECIVER IS ABLE TO GET MESSAGE
        deliveries = []

        for receiver in receivers:
            if receiver.id == sender.id:
                continue
            if not self.can_agents_communicate(sender, receiver):
                continue
            if self.communication_packet_loss > 0.0:
                if self.communication_rng.random() < self.communication_packet_loss:
                    continue
            deliveries.append(
                {
                    "sender_id": sender.id,
                    "receiver_id": receiver.id,
                    "message": message,
                    "delay": self.communication_delay_steps,
                }
            )

        return deliveries

    def can_agents_communicate(self, sender, receiver):
        # RESOLVE NO COMM ZONE AND PACKET LOSS
        sender_position = self.get_agent_world_position(sender)
        receiver_position = self.get_agent_world_position(receiver)

        if self.is_in_no_com_zone(sender_position) or self.is_in_no_com_zone(receiver_position):
            return False

        dx = sender_position[0] - receiver_position[0]
        dy = sender_position[1] - receiver_position[1]
        if math.hypot(dx, dy) > self.communication_range:
            return False

        if self.communication_require_los and not self.line_of_sight_clear(sender_position, receiver_position):
            return False

        return True

    def move_agent_towards(self, agent, target_cell):
        if target_cell is None or not getattr(agent, "is_active", True):
            return

        target_x, target_y = agent.grid_to_world(*target_cell)
        current_x, current_y = agent.world_position

        dx = target_x - current_x
        dy = target_y - current_y
        distance = math.hypot(dx, dy)
        if distance < 1e-9:
            agent.position = target_cell
            return

        step = min(agent.max_speed, distance)
        scale = step / distance
        options = [
            (current_x + dx * scale, current_y + dy * scale),
            (current_x + dx * scale, current_y),
            (current_x, current_y + dy * scale),
        ]

        for candidate in options:
            if not self._is_world_position_free(candidate, self.agent_radius):
                continue

            agent.last_position = agent.position
            agent.world_position = candidate
            agent.heading = math.atan2(candidate[1] - current_y, candidate[0] - current_x)
            agent.position = agent.world_to_grid(*agent.world_position)
            if hasattr(agent, "record_visit"):
                agent.record_visit(agent.position)
            else:
                agent.visited.add(agent.position)
                if agent.belief:
                    agent.belief.visited.add(agent.position)
            travelled = math.hypot(candidate[0] - current_x, candidate[1] - current_y)
            agent.consume_battery(agent.continuous_move_cost * travelled)
            return

    def try_rescue(self, agent, agents, target_cell=None):
        # IF IN POSITION TO RESCUE
        # MARK RESCUED AND CLEAR H LEARNING
        if not getattr(agent, "is_active", True):
            return None

        if self.mode != "continuous":
            rescue_cell = target_cell or agent.position
            if rescue_cell is None:
                return None
            if not self.grid_map.in_bounds(*rescue_cell):
                return None
            if self.grid_map.get_cell(*rescue_cell) != VICTIM:
                return None

            if rescue_cell != agent.position:
                agent.last_position = agent.position
                agent.last_world_position = agent.world_position
                agent.position = rescue_cell
                agent.world_position = agent.grid_to_world(*agent.position)
                if hasattr(agent, "record_visit"):
                    agent.record_visit(agent.position)
                agent.consume_battery(agent.grid_move_cost)

            return self._complete_rescue(agent, agents, rescue_cell)

        for victim in self.victims:
            if victim.rescued:
                continue

            dx = victim.position[0] - agent.world_position[0]
            dy = victim.position[1] - agent.world_position[1]
            if math.hypot(dx, dy) > self.rescue_radius:
                continue

            return self._complete_rescue(agent, agents, victim.grid_position, victim)

        return None

    def _complete_rescue(self, agent, agents, victim_cell, victim_entity=None):
        if victim_entity is None:
            for victim in self.victims:
                if tuple(victim.grid_position) == tuple(victim_cell):
                    victim_entity = victim
                    break

        if victim_entity is not None:
            victim_entity.rescued = True

        self.grid_map.set_cell(victim_cell[0], victim_cell[1], FREE)

        for other in agents:
            if other.belief is None:
                continue
            other.belief.clear_victim(victim_cell)
            if victim_cell in other.belief.grid:
                other.belief.grid[victim_cell] = FREE
            other.H.clear()

        agent.consume_battery(agent.rescue_cost)
        return f"Agent {agent.id} rescued{victim_cell}"

    def raycast_distance(self, origin, angle, max_range, step=0.05):
        # GET HOW FAR SENSOR CAN VIEW
        x, y = origin
        distance = 0.0

        while distance <= max_range:
            sample_x = x + distance * math.cos(angle)
            sample_y = y + distance * math.sin(angle)

            if not self._is_point_in_world(sample_x, sample_y):
                return min(distance, max_range)

            if self._point_hits_obstacle(sample_x, sample_y):
                return distance

            distance += step

        return max_range

    def line_of_sight_clear(self, start, end, step=0.05):
        # CHECK IF CAMERA CAN VIEW COMPLETELY
        x0, y0 = start
        x1, y1 = end
        dx = x1 - x0
        dy = y1 - y0
        distance = math.hypot(dx, dy)

        if distance < 1e-9:
            return True

        samples = max(1, int(distance / step))
        for index in range(1, samples):
            t = index / samples
            sample_x = x0 + dx * t
            sample_y = y0 + dy * t
            if not self._is_point_in_world(sample_x, sample_y):
                return False
            if self._point_hits_obstacle(sample_x, sample_y):
                return False

        return True

    # ================= HELPER ====================
    def get_cell(self, x, y):
        return self.grid_map.get_cell(x, y)

    def is_free(self, x, y):
        return self.grid_map.is_free(x, y)

    def get_spawn_position(self, agent_index=0):
        return self.reference_map.get_spawn_position(agent_index)

    def _is_world_position_free(self, world_position, radius):
        x, y = world_position
        if x - radius < 0 or y - radius < 0:
            return False
        if x + radius > self.world_width or y + radius > self.world_height:
            return False

        for obstacle in self.obstacles:
            if self._circle_intersects_rect(x, y, radius, obstacle.bounds):
                return False

        return True

    def _is_point_in_world(self, x, y):
        return 0 <= x <= self.world_width and 0 <= y <= self.world_height

    def _point_hits_obstacle(self, x, y):
        for obstacle in self.obstacles:
            min_x, min_y, max_x, max_y = obstacle.bounds
            if min_x <= x <= max_x and min_y <= y <= max_y:
                return True
        return False
    
    def get_agent_world_position(self, agent):
        if getattr(self, "mode", "grid") == "continuous":
            return agent.measured_gps_position()
        return agent.grid_to_world(*agent.position)

    def is_in_no_com_zone(self, world_position):
        for zone in getattr(self.playground, "communication_zones", []):
            if zone.blocks_communication and zone.contains(world_position):
                return True
        return False
