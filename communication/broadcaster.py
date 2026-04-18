def _sorted_cells(cells):
    return sorted(cells, key=lambda cell: (cell[0], cell[1]))


def _serialize_grid_items(grid_items, limit):
    serialized = []
    for (x, y), value in sorted(grid_items, key=lambda item: (item[0][0], item[0][1])):
        serialized.append((x, y, value))
        if len(serialized) >= limit:
            break
    return serialized


def _serialize_evidence(evidence_items, limit):
    serialized = []
    for (x, y), count in sorted(evidence_items, key=lambda item: (item[0][0], item[0][1])):
        serialized.append((x, y, count))
        if len(serialized) >= limit:
            break
    return serialized


def create_message(agent):
    # MESSAGE TO BE SENT TO OTHER AGENTS

    # MAP AND MESSAGE CONSTRAINTS
    belief = agent.belief
    config = getattr(agent, "config", None)
    map_limit = getattr(config, "MESSAGE_MAP_LIMIT", 120)
    explored_limit = getattr(config, "MESSAGE_EXPLORED_LIMIT", 120)
    visited_limit = getattr(config, "MESSAGE_VISITED_LIMIT", 120)
    # GET VICTIMS IN RANGE AND ONLY SEND LIMITED MESSAGE
    victim_cells = _sorted_cells(belief.victims)
    suspected_victim_cells = _sorted_cells(belief.suspected_victims)
    map_cells = _serialize_grid_items(belief.grid.items(), map_limit)
    evidence_cells = _serialize_evidence(belief.victim_evidence.items(), map_limit)
    explored_cells = _sorted_cells(belief.explored)[:explored_limit]
    visited_cells = _sorted_cells(belief.visited)[:visited_limit]

    return {
        "id": agent.id,
        "message_type": "belief_update",
        "priority": 2 if victim_cells else 1,
        "position": agent.position,
        "payload": {
            "map_cells": map_cells,
            "victims": victim_cells,
            "suspected_victims": suspected_victim_cells,
            "victim_evidence": evidence_cells,
            "explored": explored_cells,
            "visited": visited_cells,
        },
    }
