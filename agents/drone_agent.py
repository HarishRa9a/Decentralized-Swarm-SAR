from utils.constants import VICTIM
from utils.continuous_adapter import (
    grid_to_world as adapter_grid_to_world,
    world_to_grid as adapter_world_to_grid,
)
from communication.broadcaster import create_message
from agents.drone_planner import DronePlanner
from agents.drone_state import DroneState
from perception.sensors import SensorSuite


class DroneAgent:
    def __init__(self, agent_id, start_pos, config):
        self.id = agent_id
        self.config = config
        self.position = start_pos

        self.alpha = config.ALPHA
        self.beta = config.BETA
        self.lambda_ = config.LAMBDA
        self.mu = config.MU
        self.gamma = config.GAMMA
        self.delta = config.DELTA

        self.sensor = SensorSuite(config, agent_id)
        self.belief = None

        self.visited = {self.position}
        self.visit_counts = {self.position: 1}

        self.inbox = []
        self.state = DroneState(config)
        self.last_position = None
        self.cell_size = getattr(config, "CELL_SIZE", 1.0)
        self.max_speed = getattr(config, "MAX_SPEED", 1.0)
        self.agent_radius = getattr(config, "AGENT_RADIUS", 0.18)
        self.planner = DronePlanner(self)
        self.env = None
        self.world_position = self.grid_to_world(*self.position)
        self.heading = 0.0
        self.last_world_position = self.world_position
        self.last_heading = self.heading
        self.last_sensor_packet = {}
        self.last_lidar = []
        self.last_semantic = []
        self.last_gps_position = self.world_position
        self.last_compass_heading = self.heading
        self.last_odometer = {"dist_travel": 0.0, "alpha": 0.0, "theta": 0.0}
        self.last_decision_details = {}
        self._trace = None

    @property
    def is_active(self):
        return self.state.is_active

    @property
    def is_failed(self):
        return self.state.is_failed

    @property
    def battery(self):
        return self.state.battery

    @battery.setter
    def battery(self, value):
        self.state.battery = value

    @property
    def max_battery(self):
        return self.state.max_battery

    @property
    def low_battery_threshold(self):
        return self.state.low_battery_threshold

    @property
    def grid_move_cost(self):
        return self.state.grid_move_cost

    @property
    def continuous_move_cost(self):
        return self.state.continuous_move_cost

    @property
    def idle_cost(self):
        return self.state.idle_cost

    @property
    def communication_cost(self):
        return self.state.communication_cost

    @property
    def rescue_cost(self):
        return self.state.rescue_cost

    @property
    def failed(self):
        return self.state.failed

    @failed.setter
    def failed(self, value):
        self.state.failed = value

    @property
    def failure_reason(self):
        return self.state.failure_reason

    @failure_reason.setter
    def failure_reason(self, value):
        self.state.failure_reason = value

    @property
    def failed_at_step(self):
        return self.state.failed_at_step

    @failed_at_step.setter
    def failed_at_step(self, value):
        self.state.failed_at_step = value

    @property
    def H(self):
        return self.planner.H

    def battery_ratio(self):
        return self.state.battery_ratio()

    def is_low_battery(self):
        return self.state.is_low_battery()

    def consume_battery(self, amount):
        self.state.consume_battery(amount)

    def record_visit(self, cell):
        self.visited.add(cell)
        self.visit_counts[cell] = self.visit_counts.get(cell, 0) + 1
        if self.belief:
            self.belief.record_visit(cell)

    def fail(self, timestep=None, reason="forced_failure"):
        self.state.fail(timestep, reason)

    def _start_trace(self, timestep):
        self._trace = {
            "agent_id": self.id,
            "timestep": timestep,
            "position_start": self.position,
            "tools": [],
            "decision_summary": "",
            "communication_events": [],
            "executed_action": None,
            "result": {},
        }

    def _record_tool(self, name, output):
        if self._trace is None:
            return
        self._trace["tools"].append({"tool": name, "output": output})

    def _record_communication(self, event):
        if self._trace is None:
            return
        self._trace["communication_events"].append(event)

    def _set_decision_summary(self, summary):
        if self._trace is None:
            return
        self._trace["decision_summary"] = summary

    def _set_executed_action(self, action):
        if self._trace is None:
            return
        self._trace["executed_action"] = action

    def finalize_trace(self, deliveries=None, rescue=None):
        if self._trace is None:
            return None

        receiver_ids = []
        if deliveries:
            receiver_ids = [delivery["receiver_id"] for delivery in deliveries]

        if receiver_ids:
            self._record_communication(
                {
                    "event": "broadcast",
                    "message_type": "belief_update",
                    "receivers": receiver_ids,
                }
            )

        self._trace["result"] = {
            "rescue": rescue,
            "battery": self.battery,
            "active": self.is_active,
            "failed": self.failed,
            "failure_reason": self.failure_reason,
            "position_end": self.position,
            "known_victims": len(self.belief.victims) if self.belief else 0,
            "suspected_victims": len(self.belief.suspected_victims) if self.belief else 0,
        }

        record = self._trace
        self._trace = None
        return record

    def perceive(self, env):
        if not self.is_active:
            return self.last_sensor_packet or {
                "grid_observations": [],
                "gps_position": self.world_position,
                "compass_heading": self.heading,
                "odometer": self.last_odometer,
                "lidar": [],
                "semantic": [],
            }
        if getattr(env, "mode", "grid") == "continuous":
            self.position = self.world_to_grid(*self.world_position)
        packet = self.sensor.scan(self, env)
        self.last_sensor_packet = packet
        self.last_lidar = packet.get("lidar", [])
        self.last_semantic = packet.get("semantic", [])
        self.last_gps_position = packet.get("gps_position", self.world_position)
        self.last_compass_heading = packet.get("compass_heading", self.heading)
        self.last_odometer = packet.get("odometer", self.last_odometer)
        return packet

    def update_belief(self, observations):
        if self.belief:
            if isinstance(observations, dict):
                self.belief.update_from_observation(observations.get("grid_observations", []))
            else:
                self.belief.update_from_observation(observations)

    def world_to_grid(self, x, y, cell_size=None):
        size = self.cell_size if cell_size is None else cell_size
        return adapter_world_to_grid(x, y, size)

    def grid_to_world(self, i, j, cell_size=None):
        size = self.cell_size if cell_size is None else cell_size
        return adapter_grid_to_world(i, j, size)

    def measured_gps_position(self):
        if self.last_gps_position is not None:
            return self.last_gps_position
        if self.world_position is not None:
            return self.world_position
        return self.grid_to_world(*self.position)

    def act(self, action, env):
        if not self.is_active or not action:
            return

        if getattr(env, "mode", "grid") == "continuous":
            self.last_world_position = self.world_position
            self.last_heading = self.heading
            env.move_agent_towards(self, action)
            return

        nx, ny = action
        if env.is_free(nx, ny):
            self.last_position = self.position
            self.last_world_position = self.world_position
            self.position = (nx, ny)
            self.world_position = self.grid_to_world(*self.position)
            self.record_visit(self.position)
            self.consume_battery(self.grid_move_cost)

    def communicate(self):
        if not self.is_active:
            return None
        self.consume_battery(self.communication_cost)
        return create_message(self)

    def step(self, env, agents):
        timestep = getattr(env, "current_timestep", None)
        self._start_trace(timestep)
        self.last_decision_details = {}

        if not self.is_active:
            reason = "failed" if self.failed else "battery is depleted"
            self._set_decision_summary(f"Inactive because drone {reason}")
            self._set_executed_action(
                {
                    "move_to": None,
                    "mode": getattr(env, "mode", "grid"),
                    "status": "failed" if self.failed else "inactive",
                }
            )
            return (None, None)

        self.consume_battery(self.idle_cost)

        obs = self.perceive(env)
        self.update_belief(obs)
        observed_cells = []
        if isinstance(obs, dict):
            observed_cells = obs.get("grid_observations", [])
        else:
            observed_cells = obs or []
        self._record_tool(
            "sense_environment",
            {
                "observed_cells": len(observed_cells),
                "victims_detected_now": sum(1 for _, _, value in observed_cells if value == VICTIM),
                "explored_total": len(self.belief.explored) if self.belief else 0,
            },
        )

        action = self.decide(env, agents)
        details = self.last_decision_details or {}
        self._record_tool(
            "identify_frontiers",
            {
                "candidate_moves": details.get("candidate_moves", []),
                "frontier_moves": details.get("frontier_moves", []),
            },
        )
        self._record_tool(
            "evaluate_utility",
            {
                "scored_moves": details.get("scored_moves", []),
                "selected_move": details.get("selected_move"),
            },
        )

        self.act(action, env)
        rescue = env.try_rescue(self, agents, action)
        explored_count = len(self.belief.explored) if self.belief else 0
        self.state.record_progress(self.position, explored_count)
        summary = f"Selected {action} from {len(details.get('candidate_moves', []))} legal moves"
        if details.get("frontier_moves"):
            summary += f"; prioritized {len(details['frontier_moves'])} frontier candidates"
        if self.is_low_battery():
            summary += "; low-battery mode"
        if rescue:
            summary += f"; {rescue}"
        self._set_decision_summary(summary)
        self._set_executed_action({"move_to": action, "mode": getattr(env, "mode", "grid")})

        message = self.communicate()
        payload = message.get("payload", {}) if message else {}
        self._record_tool(
            "broadcast_detection",
            {
                "victims_shared": len(payload.get("victims", [])),
                "suspected_shared": len(payload.get("suspected_victims", [])),
                "explored_shared": len(payload.get("explored", [])),
            },
        )
        return (message, rescue)

    def decide(self, env, agents):
        return self.planner.decide(env, agents)
