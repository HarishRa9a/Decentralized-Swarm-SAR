from utils.constants import FREE, VICTIM

def _extract_payload(msg):
    map_cells = None

    if "payload" in msg:
        msg = msg["payload"]
        map_cells = msg.get("map_cells", [])
    else:
        legacy_map = msg.get("map", {})
        map_cells = [(x, y, value) for (x, y), value in legacy_map.items()]
    
    victims = msg.get("victims", [])
    suspected_victims = msg.get("suspected_victims", [])
    victim_evidence = msg.get("victim_evidence", [])
    explored = msg.get("explored", [])
    visited = msg.get("visited", [])
    
    return map_cells, victims, suspected_victims, victim_evidence, explored, visited


def merge_maps(agent, messages, env):
    for msg in messages:
        if msg["id"] == agent.id:
            continue

        map_cells, victims, suspected_victims, victim_evidence, explored, visited = _extract_payload(msg)

        # merge grid
        for x, y, value in map_cells:
            key = (x, y)
            current_value = env.get_cell(*key)
            if current_value is not None:
                agent.belief.grid[key] = current_value
            else:
                agent.belief.grid[key] = value

        # =======merge victims=======
        for v in victims:
            victim_pos = tuple(v)
            if env.get_cell(*victim_pos) == VICTIM:
                agent.belief.victims.add(victim_pos)
                agent.belief.suspected_victims.discard(victim_pos)
                agent.belief.victim_evidence[victim_pos] = max(
                    agent.belief.confirmation_steps,
                    agent.belief.victim_evidence.get(victim_pos, 0),
                )
            else:
                agent.belief.clear_victim(victim_pos)

        for v in suspected_victims:
            victim_pos = tuple(v)
            if env.get_cell(*victim_pos) == VICTIM and victim_pos not in agent.belief.victims:
                agent.belief.suspected_victims.add(victim_pos)
            elif env.get_cell(*victim_pos) != VICTIM:
                agent.belief.clear_victim(victim_pos)

        for x, y, count in victim_evidence:
            victim_pos = (x, y)
            if env.get_cell(*victim_pos) == VICTIM:
                agent.belief.merge_victim_evidence(victim_pos, max(1, count))
            else:
                agent.belief.clear_victim(victim_pos)
        # =====================

        # merge shared explored cells
        for pos in explored:
            agent.belief.explored.add(tuple(pos))

        # merge shared visited cells
        for pos in visited:
            agent.belief.visited.add(tuple(pos))

        # prune any stale victims that no longer exist in the environment
        stale_victims = {
            victim for victim in agent.belief.victims
            if env.get_cell(*victim) != VICTIM
        }
        for victim in stale_victims:
            agent.belief.clear_victim(victim)
            agent.belief.grid[victim] = FREE
