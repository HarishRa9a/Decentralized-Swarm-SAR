from communication.map_merger import merge_maps
from simulation.metrics import MetricsTracker
from simulation.metrics_logger import MetricsLogger
from simulation.trace_logger import TraceLogger
import random
import time

class Simulator:
    def __init__(self, env, agents, config):
        self.env = env
        self.agents = agents
        self.config = config
        self.step_count = 0
        self.pending_deliveries = []
        self.metrics = MetricsTracker(env, agents)
        self.metrics_logger = MetricsLogger(config)
        self.trace_logger = TraceLogger(config)
        self.failure_schedule = self._build_failure_schedule()
        self.control_panel = self._build_control_panel()

    def run(self):
        rescued = []
        target_victims = self.env.total_victims
        self.metrics.update(self.step_count)
        self.metrics_logger.log_step(self._build_metrics_record())
        self._update_control_panel()

        while self.step_count < self.config.MAX_STEPS and len(rescued) < target_victims:
            if not self._wait_for_control_panel():
                break
            if not any(agent.is_active for agent in self.agents):
                break
            self.env.current_timestep = self.step_count
            self.env.frontier_assignments = {}
            self._apply_scheduled_failures()
            deliveries = []
            traces = []

            # --- agent steps ---
            for agent in self.agents:
                msg,rescue = agent.step(self.env,self.agents)
                agent_deliveries = []
                if msg:
                    agent_deliveries = self.env.resolve_message_delivery(agent, self.agents, msg)
                    deliveries.extend(agent_deliveries)
                if rescue:
                    rescued.append("At step ("+str(len(rescued)+1)+") \t"+str(self.step_count)+"\t"+rescue)
                traces.append(agent.finalize_trace(agent_deliveries, rescue))

            # --- communication ---
            self.pending_deliveries.extend(deliveries)
            self._deliver_messages()
            for trace in traces:
                if trace is not None:
                    self.trace_logger.log_agent_step(trace)

            # --- increment ---
            self.step_count += 1
            self.metrics.update(self.step_count)
            self.metrics_logger.log_step(self._build_metrics_record())

            # --- render ---
            self.render()
            self._update_control_panel()

        summary = self._build_mission_summary(rescued, target_victims)
        self.trace_logger.log_summary(summary)

        for i in rescued:
            print(i)

        self._update_control_panel()
        self._wait_for_close()

    def render(self):
        if getattr(self.config, "SHOW_METRICS_DASHBOARD", False):
            from visualization.metrics_visualizer import render_metrics
            render_metrics(self.metrics, self.config)

        if self.control_panel is not None:
            self._update_control_panel()
            return

        from visualization.renderer import render_environment
        render_environment(
            self.env,
            self.agents,
            self.step_count,
            self.config,
        )

    def _build_control_panel(self):
        if not bool(getattr(self.config, "SHOW_CONTROL_PANEL", False)):
            return None
        try:
            from visualization.control_panel import SimulationControlPanel
            return SimulationControlPanel()
        except Exception as error:
            print(f"Control panel disabled: {error}")
            return None

    def _wait_for_control_panel(self):
        if self.control_panel is None:
            return True

        while not self.control_panel.should_advance():
            self._update_control_panel()
            if self.control_panel.stop_requested:
                return False
            time.sleep(0.05)

        return not self.control_panel.stop_requested

    def _update_control_panel(self):
        if self.control_panel is not None:
            self.control_panel.update(self)

    def _wait_for_close(self):
        """Keep tkinter windows open until the user closes them."""
        import tkinter as tk

        # Update control panel status to show simulation is complete
        if self.control_panel is not None and not self.control_panel.closed:
            self.control_panel._stat_vars["Status"].set("Completed")
            self.control_panel.running = False
            try:
                self.control_panel.root.mainloop()
            except Exception:
                pass
            return

        # If no control panel, check for metrics window
        from visualization.metrics_visualizer import _metrics_window
        if _metrics_window is not None:
            try:
                _metrics_window.mainloop()
            except Exception:
                pass

    def _deliver_messages(self):
        inbox_by_agent = {agent.id: [] for agent in self.agents}
        remaining_deliveries = []

        for delivery in self.pending_deliveries:
            delay = delivery.get("delay", 0)
            if delay > 0:
                delivery["delay"] = delay - 1
                remaining_deliveries.append(delivery)
                continue

            receiver_id = delivery["receiver_id"]
            inbox_by_agent.setdefault(receiver_id, []).append(delivery["message"])

        self.pending_deliveries = remaining_deliveries

        for agent in self.agents:
            inbox = inbox_by_agent.get(agent.id, [])
            if inbox:
                merge_maps(agent, inbox, self.env)

    def _build_failure_schedule(self):
        if not bool(getattr(self.config, "ENABLE_DRONE_FAILURES", False)):
            return {}

        requested_count = max(0, int(getattr(self.config, "FAILED_DRONE_COUNT", 0)))
        if requested_count <= 0:
            return {}

        active_agents = [agent for agent in self.agents]
        failure_count = min(requested_count, len(active_agents))
        if failure_count <= 0:
            return {}

        seed = int(getattr(self.config, "FAILURE_RANDOM_SEED", 7))
        rng = random.Random(seed)
        start_step = max(0, int(getattr(self.config, "FAILURE_START_STEP", 1)))
        end_step = max(start_step, int(getattr(self.config, "FAILURE_END_STEP", start_step)))

        chosen_agents = rng.sample(active_agents, failure_count)
        failure_steps = sorted(rng.randint(start_step, end_step) for _ in range(failure_count))

        schedule = {}
        for agent, failure_step in zip(chosen_agents, failure_steps):
            schedule.setdefault(failure_step, []).append(agent.id)
        return schedule

    def _apply_scheduled_failures(self):
        failing_ids = self.failure_schedule.pop(self.step_count, [])
        if not failing_ids:
            return

        for agent in self.agents:
            if agent.id not in failing_ids or agent.failed:
                continue

            agent.fail(self.step_count, reason="configured_failure")
            if agent.belief is not None:
                agent.H.clear()

    def _build_mission_summary(self, rescued, target_victims):
        latest = self.metrics.latest()
        coverage_target = 0.95
        coverage_reached = latest["coverage"] >= coverage_target
        rescued_all = latest["rescued_victims"] >= target_victims

        if rescued_all:
            completion_reason = "all_victims_rescued"
        elif coverage_reached:
            completion_reason = "coverage_threshold_reached"
        elif not any(agent.is_active for agent in self.agents):
            completion_reason = "all_drones_inactive"
        elif self.step_count >= self.config.MAX_STEPS:
            completion_reason = "max_steps_reached"
        else:
            completion_reason = "simulation_stopped"

        return {
            "record_type": "mission_summary",
            "final_timestep": self.step_count,
            "completion_reason": completion_reason,
            "mission_complete": rescued_all or coverage_reached,
            "area_covered_ratio": latest["coverage"],
            "area_covered_percent": round(latest["coverage"] * 100, 2),
            "all_cell_covered_ratio": latest["coverage_all_cells"],
            "all_cell_covered_percent": round(latest["coverage_all_cells"] * 100, 2),
            "overlap_ratio": latest["overlap"],
            "overlap_percent": round(latest["overlap"] * 100, 2),
            "overlapped_cells": latest["overlapped_cells"],
            "unique_visited_cells": latest["unique_visited_cells"],
            "total_visits": latest["total_visits"],
            "repeated_visits": latest["repeated_visits"],
            "redundant_visit_ratio": latest["redundant_visit_ratio"],
            "redundant_visit_percent": round(latest["redundant_visit_ratio"] * 100, 2),
            "victims_total": target_victims,
            "victims_rescued": latest["rescued_victims"],
            "victims_detected": latest["detected_victims"],
            "victims_suspected": latest["suspected_victims"],
            "victim_detection_true_positives": latest["true_positives"],
            "victim_detection_false_positives": latest["false_positives"],
            "victim_detection_false_negatives": latest["false_negatives"],
            "victim_detection_precision": round(latest["precision"] * 100, 2),
            "victim_detection_recall": round(latest["recall"] * 100, 2),
            "victim_detection_f1": round(latest["f1_score"] * 100, 2),
            "failed_drones": sum(1 for agent in self.agents if agent.failed),
            "rescue_events": rescued,
            "pending_message_deliveries": len(self.pending_deliveries),
            "agents": [
                {
                    "agent_id": agent.id,
                    "position": agent.position,
                    "battery": agent.battery,
                    "active": agent.is_active,
                    "failed": agent.failed,
                    "failure_reason": agent.failure_reason,
                    "failed_at_step": agent.failed_at_step,
                    "known_victims": len(agent.belief.victims) if agent.belief else 0,
                    "suspected_victims": len(agent.belief.suspected_victims) if agent.belief else 0,
                    "explored_cells": len(agent.belief.explored) if agent.belief else 0,
                    "visited_cells": len(agent.belief.visited) if agent.belief else 0,
                }
                for agent in self.agents
            ],
            "metric_history_points": len(self.metrics.history["step"]),
        }

    def _build_metrics_record(self):
        latest = self.metrics.latest()
        return {
            "record_type": "current_metrics",
            "timestep": latest["step"],
            "current_explored_ratio": latest["coverage"],
            "current_explored_percent": round(latest["coverage"] * 100, 2),
            "current_all_cell_explored_ratio": latest["coverage_all_cells"],
            "current_all_cell_explored_percent": round(latest["coverage_all_cells"] * 100, 2),
            "current_overlap_ratio": latest["overlap"],
            "current_overlap_percent": round(latest["overlap"] * 100, 2),
            "overlapped_cells": latest["overlapped_cells"],
            "unique_visited_cells": latest["unique_visited_cells"],
            "total_visits": latest["total_visits"],
            "repeated_visits": latest["repeated_visits"],
            "redundant_visit_ratio": latest["redundant_visit_ratio"],
            "redundant_visit_percent": round(latest["redundant_visit_ratio"] * 100, 2),
            "victims_found": latest["detected_victims"],
            "victims_detected": latest["detected_victims"],
            "victims_suspected": latest["suspected_victims"],
            "victims_rescued": latest["rescued_victims"],
        }
