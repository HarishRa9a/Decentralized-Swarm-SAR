from utils.constants import VICTIM

class BeliefState:
    def __init__(self, config=None):
        self.grid = {}    
        self.victims = set()
        self.suspected_victims = set()
        self.victim_evidence = {}
        self.explored = set()
        self.visited = set()
        self.visit_counts = {}
        self.confirmation_steps = max(1,int(getattr(config, "VICTIM_CONFIRMATION_STEPS", 2)),)

    # ------------------------------

    def update_from_observation(self, observations):
        for x, y, value in observations:
            self.grid[(x, y)] = value
            self.explored.add((x, y))

            # victim detection
            if value == VICTIM:
                self.register_victim_evidence((x, y))
            else:
                self.clear_victim((x, y))

    def register_victim_evidence(self, pos, increment=1):
        evidence = self.victim_evidence.get(pos, 0) + increment
        self._set_victim_evidence(pos, evidence)

    def merge_victim_evidence(self, pos, evidence):
        self._set_victim_evidence(pos, max(self.victim_evidence.get(pos, 0), evidence))

    def _set_victim_evidence(self, pos, evidence):
        self.victim_evidence[pos] = evidence

        if evidence >= self.confirmation_steps:
            self.victims.add(pos)
            self.suspected_victims.discard(pos)
        else:
            self.suspected_victims.add(pos)

    def clear_victim(self, pos):
        self.victims.discard(pos)
        self.suspected_victims.discard(pos)
        self.victim_evidence.pop(pos, None)

    # ------------------------------

    def record_visit(self, pos):
        self.visited.add(pos)
        self.visit_counts[pos] = self.visit_counts.get(pos, 0) + 1

    # ------------------------------

    def merge(self, other_map):
        for key, value in other_map.items():
            if key not in self.grid:
                self.grid[key] = value
