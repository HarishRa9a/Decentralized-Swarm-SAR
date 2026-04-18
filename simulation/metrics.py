# simulation/metrics.py

from utils.constants import VICTIM, WALL


def _safe_belief(agent):
    return getattr(agent, "belief", None)


def _all_explored_cells(agents):
    explored = set()
    for agent in agents:
        belief = _safe_belief(agent)
        if belief is not None:
            explored.update(belief.explored)
    return explored


def compute_coverage(env, agents):
    explored = _all_explored_cells(agents)
    explorable = _explorable_cells(env)
    return len(explored & explorable) / len(explorable) if explorable else 0.0


def compute_all_cell_coverage(env, agents):
    explored = _all_explored_cells(agents)
    total = env.grid_map.width * env.grid_map.height
    return len(explored) / total if total else 0.0


def _explorable_cells(env):
    cells = set()
    for x in range(env.grid_map.height):
        for y in range(env.grid_map.width):
            if env.get_cell(x, y) != WALL:
                cells.add((x, y))
    return cells


def compute_overlap_ratio(agents):
    details = compute_overlap_details(agents)
    return details["overlap_cell_ratio"]


def compute_overlap_details(agents):
    visit_counts = {}
    agent_presence = {}

    for agent in agents:
        counts = getattr(agent, "visit_counts", None)
        if not counts:
            belief = _safe_belief(agent)
            counts = getattr(belief, "visit_counts", None) if belief is not None else None

        if counts:
            for cell, count in counts.items():
                visit_counts[cell] = visit_counts.get(cell, 0) + count
                agent_presence.setdefault(cell, set()).add(agent.id)
            continue

        belief = _safe_belief(agent)
        if belief is None:
            continue
        for cell in belief.visited:
            visit_counts[cell] = visit_counts.get(cell, 0) + 1
            agent_presence.setdefault(cell, set()).add(agent.id)

    if not visit_counts:
        return {
            "overlap_cell_ratio": 0.0,
            "overlapped_cells": 0,
            "unique_visited_cells": 0,
            "total_visits": 0,
            "repeated_visits": 0,
            "redundant_visit_ratio": 0.0,
        }

    overlapped = sum(1 for agents_here in agent_presence.values() if len(agents_here) > 1)
    total_visits = sum(visit_counts.values())
    repeated_visits = sum(max(0, count - 1) for count in visit_counts.values())

    return {
        "overlap_cell_ratio": overlapped / len(visit_counts),
        "overlapped_cells": overlapped,
        "unique_visited_cells": len(visit_counts),
        "total_visits": total_visits,
        "repeated_visits": repeated_visits,
        "redundant_visit_ratio": repeated_visits / total_visits if total_visits else 0.0,
    }


def compute_detected_victims(env, agents):
    detected = set()

    for agent in agents:
        belief = _safe_belief(agent)
        if belief is None:
            continue
        detected.update(getattr(belief, "victims", set()))
        detected.update(getattr(belief, "suspected_victims", set()))

    live_detected = {cell for cell in detected if env.get_cell(*cell) == VICTIM}
    return len(live_detected)


def compute_suspected_victims(env, agents):
    suspected = set()

    for agent in agents:
        belief = _safe_belief(agent)
        if belief is None:
            continue
        suspected.update(getattr(belief, "suspected_victims", set()))

    live_suspected = {cell for cell in suspected if env.get_cell(*cell) == VICTIM}
    return len(live_suspected)


def compute_rescued_victims(env):
    if getattr(env, "mode", "grid") == "continuous":
        return sum(1 for victim in env.victims if victim.rescued)

    remaining = 0
    for x in range(env.grid_map.width):
        for y in range(env.grid_map.height):
            if env.get_cell(x, y) == VICTIM:
                remaining += 1
    return max(0, env.total_victims - remaining)


def _live_victim_cells(env):
    if getattr(env, "mode", "grid") == "continuous":
        return {
            tuple(victim.grid_position)
            for victim in env.victims
            if not victim.rescued
        }

    victims = set()
    for x in range(env.grid_map.width):
        for y in range(env.grid_map.height):
            if env.get_cell(x, y) == VICTIM:
                victims.add((x, y))
    return victims


def _predicted_victim_cells(agents):
    predicted = set()
    for agent in agents:
        belief = _safe_belief(agent)
        if belief is None:
            continue
        predicted.update(getattr(belief, "victims", set()))
        predicted.update(getattr(belief, "suspected_victims", set()))
    return predicted


def compute_detection_quality(env, agents):
    actual = _live_victim_cells(env)
    predicted = _predicted_victim_cells(agents)

    true_positives = len(predicted & actual)
    false_positives = len(predicted - actual)
    false_negatives = len(actual - predicted)

    precision_denominator = true_positives + false_positives
    recall_denominator = true_positives + false_negatives

    precision = (
        true_positives / precision_denominator
        if precision_denominator
        else 0.0
    )
    recall = true_positives / recall_denominator if recall_denominator else 0.0
    f1_score = (
        (2 * precision * recall) / (precision + recall)
        if precision + recall
        else 0.0
    )

    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
    }


class MetricsTracker:
    def __init__(self, env, agents):
        self.env = env
        self.agents = agents
        self.history = {
            "step": [],
            "coverage": [],
            "coverage_all_cells": [],
            "overlap": [],
            "overlapped_cells": [],
            "unique_visited_cells": [],
            "total_visits": [],
            "repeated_visits": [],
            "redundant_visit_ratio": [],
            "detected_victims": [],
            "suspected_victims": [],
            "rescued_victims": [],
            "true_positives": [],
            "false_positives": [],
            "false_negatives": [],
            "precision": [],
            "recall": [],
            "f1_score": [],
        }

    def update(self, step):
        detection_quality = compute_detection_quality(self.env, self.agents)
        overlap_details = compute_overlap_details(self.agents)
        self.history["step"].append(step)
        self.history["coverage"].append(compute_coverage(self.env, self.agents))
        self.history["coverage_all_cells"].append(compute_all_cell_coverage(self.env, self.agents))
        self.history["overlap"].append(overlap_details["overlap_cell_ratio"])
        self.history["overlapped_cells"].append(overlap_details["overlapped_cells"])
        self.history["unique_visited_cells"].append(overlap_details["unique_visited_cells"])
        self.history["total_visits"].append(overlap_details["total_visits"])
        self.history["repeated_visits"].append(overlap_details["repeated_visits"])
        self.history["redundant_visit_ratio"].append(overlap_details["redundant_visit_ratio"])
        self.history["detected_victims"].append(compute_detected_victims(self.env, self.agents))
        self.history["suspected_victims"].append(compute_suspected_victims(self.env, self.agents))
        self.history["rescued_victims"].append(compute_rescued_victims(self.env))
        self.history["true_positives"].append(detection_quality["true_positives"])
        self.history["false_positives"].append(detection_quality["false_positives"])
        self.history["false_negatives"].append(detection_quality["false_negatives"])
        self.history["precision"].append(detection_quality["precision"])
        self.history["recall"].append(detection_quality["recall"])
        self.history["f1_score"].append(detection_quality["f1_score"])

    def latest(self):
        if not self.history["step"]:
            return {
                "step": 0,
                "coverage": 0.0,
                "coverage_all_cells": 0.0,
                "overlap": 0.0,
                "overlapped_cells": 0,
                "unique_visited_cells": 0,
                "total_visits": 0,
                "repeated_visits": 0,
                "redundant_visit_ratio": 0.0,
                "detected_victims": 0,
                "suspected_victims": 0,
                "rescued_victims": 0,
                "true_positives": 0,
                "false_positives": 0,
                "false_negatives": 0,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
            }

        return {
            key: values[-1]
            for key, values in self.history.items()
        }
