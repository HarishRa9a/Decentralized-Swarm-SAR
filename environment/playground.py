from dataclasses import dataclass, field
from utils.constants import VICTIM, WALL
from environment.entities import Obstacle, Victim


@dataclass
class CommunicationZone:
    name: str
    x: float
    y: float
    width: float
    height: float
    blocks_communication: bool = True

    @property
    def bounds(self):
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def contains(self, position):
        px, py = position
        min_x, min_y, max_x, max_y = self.bounds
        return min_x <= px <= max_x and min_y <= py <= max_y


@dataclass
class Playground:
    width: float
    height: float
    cell_size: float
    obstacles: list[Obstacle] = field(default_factory=list)
    victims: list[Victim] = field(default_factory=list)
    spawn_cells: list[tuple[int, int]] = field(default_factory=list)
    communication_zones: list[CommunicationZone] = field(default_factory=list)


class ReferenceMap:
    def __init__(self,grid_map,layout_style,cell_size,obstacle_builder,communication_zone_builder=None,):
        self.grid_map = grid_map
        self.layout_style = layout_style
        self.cell_size = cell_size
        self._obstacle_builder = obstacle_builder
        self._communication_zone_builder = communication_zone_builder
        self.playground = None

    def build_playground(self):
        # List of all walls (obstacles) and victims
        wall_cells = []
        victims = []

        for i in range(self.grid_map.height):
            for j in range(self.grid_map.width):
                cell = self.grid_map.get_cell(i, j)
                if cell == WALL:
                    wall_cells.append((i, j))
                elif cell == VICTIM:
                    victims.append(
                        Victim(
                            (i, j),
                            ((j + 0.5) * self.cell_size, (i + 0.5) * self.cell_size),
                        )
                    )

        self.playground = Playground(
            width=self.grid_map.width * self.cell_size,
            height=self.grid_map.height * self.cell_size,
            cell_size=self.cell_size,
            obstacles=self._obstacle_builder(wall_cells, self.cell_size),
            victims=victims,
            spawn_cells=self._collect_spawn_cells(),
            communication_zones=self._build_communication_zones(),
        )
        return self.playground

    def count_victims(self):
        total = 0
        for i in range(self.grid_map.height):
            for j in range(self.grid_map.width):
                if self.grid_map.get_cell(i, j) == VICTIM:
                    total += 1
        return total

    def get_spawn_position(self, agent_index=0):
        spawn_cells = self._collect_spawn_cells()
        if not spawn_cells:
            return (0, 0)
        return spawn_cells[agent_index % len(spawn_cells)]

    def _collect_spawn_cells(self):
        # cell to spawn drones
        free_cells = []

        for i in range(self.grid_map.height):
            for j in range(self.grid_map.width):
                if self.grid_map.can_move(i, j):
                    free_cells.append((i, j))

        free_cells.sort(key=lambda cell: (cell[0], cell[1]))
        preferred_cells = [cell for cell in free_cells if cell[0] <= 2]
        return preferred_cells if preferred_cells else free_cells

    def _build_communication_zones(self):
        # Build no communication zone
        if self._communication_zone_builder is None:
            return []
        return self._communication_zone_builder(self.grid_map, self.cell_size)
