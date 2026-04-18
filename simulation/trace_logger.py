from pathlib import Path


class TraceLogger:
    def __init__(self, config=None):
        self.enabled = bool(getattr(config, "TRACE_LOGGING_ENABLED", False))
        self.log_to_console = bool(getattr(config, "TRACE_LOG_TO_CONSOLE", False))
        self.path = None
        self.current_step = None
        self.current_records = []

        if self.enabled:
            log_path = getattr(config, "TRACE_LOG_PATH", "logs/agent_trace.jsonl")
            self.path = Path(log_path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("", encoding="utf-8")

    def log_agent_step(self, record):
        if not self.enabled or self.path is None:
            return

        timestep = record.get("timestep")
        if self.current_step is None:
            self.current_step = timestep

        if timestep != self.current_step:
            self._flush_current_step()
            self.current_step = timestep

        self.current_records.append(record)

    def log_summary(self, summary):
        if not self.enabled or self.path is None:
            return

        self._flush_current_step()
        text = self._format_summary(summary)
        self._append_text(text)

    def _flush_current_step(self):
        if not self.current_records:
            return

        text = self._format_step(self.current_step, self.current_records)
        self._append_text(text)
        self.current_records = []

    def _append_text(self, text):
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(text)

        if self.log_to_console:
            print(text, end="")

    def _format_step(self, step, records):
        lines = [f"Step {step}", ""]

        for record in sorted(records, key=lambda item: item.get("agent_id", -1)):
            lines.extend(self._format_agent_block(record))
            lines.append("")

        return "\n".join(lines)

    def _format_agent_block(self, record):
        agent_id = record.get("agent_id")
        position = tuple(record.get("position_start", ()))
        thought = self._short_thought(record)
        action = self._action_name(record)
        observation = self._observation_text(record)
        why_move = self._why_move_text(record)
        final_action = self._final_action_text(record)

        return [
            f"Agent {agent_id}",
            f"- Thought: {thought}",
            f"- Position: {position}",
            f"- Action: {action}",
            f"- Observation: {observation}",
            f"- Why move: {why_move}",
            f"- Final Action: {final_action}",
        ]

    def _tool_output(self, record, tool_name):
        for tool in record.get("tools", []):
            if tool.get("tool") == tool_name:
                return tool.get("output", {})
        return {}

    def _short_thought(self, record):
        result = record.get("result", {})
        if result.get("failed", False):
            return "Drone failure"
        if not result.get("active", True):
            return "Battery depleted"

        decision = (record.get("decision_summary") or "").lower()
        if "low-battery mode" in decision:
            return "Stay local on low battery"

        sense = self._tool_output(record, "sense_environment")
        if sense.get("victims_detected_now", 0) > 0:
            return "Check victim area"

        frontier = self._tool_output(record, "identify_frontiers")
        if frontier.get("frontier_moves"):
            return "Explore nearby frontier"

        evaluate = self._tool_output(record, "evaluate_utility")
        if evaluate.get("selected_move") is not None:
            return "Take best local move"

        return "Hold position"

    def _action_name(self, record):
        result = record.get("result", {})
        if not result.get("active", True):
            return "inactive"
        return "evaluate_frontiers"

    def _observation_text(self, record):
        frontier = self._tool_output(record, "identify_frontiers")
        evaluate = self._tool_output(record, "evaluate_utility")
        sense = self._tool_output(record, "sense_environment")

        parts = []
        candidate_moves = frontier.get("candidate_moves", [])
        selected_move = evaluate.get("selected_move")
        if candidate_moves:
            parts.append(f"candidate_moves={candidate_moves}")
        if selected_move is not None:
            parts.append(f"selected={selected_move}")
        if sense.get("victims_detected_now", 0):
            parts.append(f"victims_detected={sense['victims_detected_now']}")
        if not parts:
            parts.append("no new observations")
        return ", ".join(parts)

    def _why_move_text(self, record):
        decision = record.get("decision_summary") or ""
        lowered = decision.lower()
        if "low-battery mode" in lowered:
            return "save battery and keep progress"
        if "prioritized" in lowered:
            return "better coverage with lower overlap"

        evaluate = self._tool_output(record, "evaluate_utility")
        scored_moves = evaluate.get("scored_moves", [])
        if scored_moves:
            return "best utility among candidate moves"

        result = record.get("result", {})
        if not result.get("active", True):
            return "no battery remaining"
        return "continue exploration"

    def _final_action_text(self, record):
        action = record.get("executed_action", {})
        move_to = action.get("move_to")
        status = action.get("status")
        if status == "failed":
            return "Failed"
        if status == "inactive":
            return "Inactive"
        if move_to is None:
            return "Hold position"
        return f"Move to {tuple(move_to)}"

    def _format_summary(self, summary):
        lines = [
            "Mission Summary",
            f"- Final timestep: {summary.get('final_timestep')}",
            f"- Completion reason: {summary.get('completion_reason')}",
            f"- Area covered: {summary.get('area_covered_percent')}%",
            f"- All-cell coverage: {summary.get('all_cell_covered_percent')}%",
            f"- Overlap: {summary.get('overlap_percent')}%",
            f"- Repeated visits: {summary.get('repeated_visits')}",
            f"- Redundant visit ratio: {summary.get('redundant_visit_percent')}%",
            f"- Victims rescued: {summary.get('victims_rescued')}/{summary.get('victims_total')}",
            f"- Victims detected: {summary.get('victims_detected')}",
            f"- Victims suspected: {summary.get('victims_suspected')}",
            f"- Detection precision: {summary.get('victim_detection_precision')}%",
            f"- Detection recall: {summary.get('victim_detection_recall')}%",
            f"- Detection F1: {summary.get('victim_detection_f1')}%",
            f"- Failed drones: {summary.get('failed_drones')}",
        ]
        return "\n".join(lines) + "\n"
