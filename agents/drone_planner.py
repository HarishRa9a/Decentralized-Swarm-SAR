def _sample_cells(cells, limit=4):
    ordered = sorted(cells, key=lambda cell: (cell[0], cell[1]))
    return ordered[:limit]


class DronePlanner:
    def __init__(self, agent):
        self.agent = agent
        self.H = {}

    def heuristic(self, pos):
        return 0

    def repulsion(self, pos, agents):
        val = 0
        for other in agents:
            if other.id != self.agent.id and other.is_active:
                d = abs(pos[0] - other.position[0]) + abs(pos[1] - other.position[1])
                val += 1 / (d + 1e-5)
        return val

    def coordination_penalty(self, pos, agents):
        for other in agents:
            if other.id != self.agent.id and other.is_active and other.position == pos:
                return 1
        return 0

    def backtrack_penalty(self, pos):
        if self.agent.last_position is not None and pos == self.agent.last_position:
            return 1
        return 0

    def utility_(self, pos):
        score = 0

        # Highest reward for cells the team has not explored yet.
        if pos not in self.agent.belief.explored:
            score += 3

        # Small extra reward for cells this specific agent has not visited.
        if pos not in self.agent.visited:
            score += 1

        return score

    def team_visited_penalty(self, pos):
        if pos in self.agent.belief.visited and pos not in self.agent.visited:
            return 1
        return 0

    def victim_score(self, pos):
        if not self.agent.belief.victims:
            return 0

        # Closer to a known victim is better.
        return max(
            1 / ((abs(pos[0] - victim[0]) + abs(pos[1] - victim[1]) + 1))
            for victim in self.agent.belief.victims
        )

    def compute_f(self, current, pos, agents):
        cost = 1
        h_val = self.H.get(pos, self.heuristic(pos))
        rep = self.repulsion(pos, agents)
        coord = self.coordination_penalty(pos, agents)
        backtrack = self.backtrack_penalty(pos)
        team_visited = self.team_visited_penalty(pos)
        util = self.utility_(pos)
        victim = self.victim_score(pos)

        low_battery_penalty = 0.0
        if self.agent.is_low_battery():
            low_battery_penalty = (1.0 - self.agent.battery_ratio()) * (
                abs(pos[0] - current[0]) + abs(pos[1] - current[1]) + 1
            )

        return (
            self.agent.alpha * cost
            + self.agent.beta * h_val
            + self.agent.lambda_ * rep
            + self.agent.mu * (coord + backtrack + team_visited)
            - self.agent.gamma * util
            - self.agent.delta * victim
            + low_battery_penalty
        )

    def update_heuristic(self, current, best_f):
        self.H[current] = best_f

    def decide(self, env, agents):
        return self._greedy_decide(env, agents)

    def _greedy_decide(self, env, agents):
        x, y = self.agent.position
        moves = [(x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)]

        valid_moves = [
            move
            for move in moves
            if env.grid_map.in_bounds(*move) and env.grid_map.can_move(*move)
        ]

        if not valid_moves:
            self.agent.last_decision_details = {
                "candidate_moves": [],
                "frontier_moves": [],
                "scored_moves": [],
                "selected_move": None,
            }
            return None

        # Prefer cells the team has not explored yet whenever such moves exist.
        unknown_moves = [
            move
            for move in valid_moves
            if move not in self.agent.belief.explored
        ]
        if unknown_moves:
            valid_moves = unknown_moves

        best_f = float("inf")
        best_move = None
        scored_moves = []

        for move in valid_moves:
            f_score = self.compute_f(self.agent.position, move, agents)
            scored_moves.append((move, round(f_score, 3)))
            if f_score < best_f:
                best_f = f_score
                best_move = move

        self.update_heuristic(self.agent.position, best_f)
        self.agent.last_decision_details = {
            "candidate_moves": _sample_cells(valid_moves),
            "frontier_moves": _sample_cells(unknown_moves),
            "scored_moves": [
                {"move": move, "score": score}
                for move, score in sorted(scored_moves, key=lambda item: item[1])[:4]
            ],
            "selected_move": best_move,
        }

        return best_move
