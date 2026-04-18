import random, heapq
from collections import deque
from utils.constants import FREE, WALL, VICTIM
from environment.grid_map import GridMap
from environment.entities import Obstacle
from environment.playground import CommunicationZone, ReferenceMap

class UrbanGenerator:
    def __init__(self, config, rng=None):
        self.width = config.GRID_WIDTH
        self.height = config.GRID_HEIGHT
        self.building_density = config.BUILDING_DENSITY
        self.gap_probability = config.GAP_PROBABILITY
        self.no_com_zone_count = getattr(config, "NO_COM_ZONE_COUNT", 0)
        self.no_com_zone_min_size = getattr(config, "NO_COM_ZONE_MIN_SIZE", 3)
        self.no_com_zone_max_size = getattr(config, "NO_COM_ZONE_MAX_SIZE", 7)
        self.rng = rng or random.Random(getattr(config, "MAP_RANDOM_SEED", 43))
    

    # ========= GENERATE REFERENCE MAP (GRID WRAPPER) ===========
    def generate_reference_map(self, layout_style, cell_size):
        grid_map = GridMap(self.width, self.height)

        # Generate grid based on style
        if layout_style == "floorplan":
            generated_grid = self.generate_floorplan_grid(grid_map)
        else:
            generated_grid = self.generate_grid(grid_map)

        
        return ReferenceMap(
            grid_map=generated_grid,
            layout_style=layout_style,
            cell_size=cell_size,
            obstacle_builder=self._merge_wall_rectangles,
            communication_zone_builder=self._build_communication_zones,
        )


    # ----------------------------------------
    def _merge_wall_rectangles(self, wall_cells, cell_size):
        if not wall_cells:
            return []

        wall_set = set(wall_cells)
        consumed = set()
        obstacles = []

        for i, j in sorted(wall_set):
            if (i, j) in consumed:
                continue

            width = 1
            while (i, j + width) in wall_set and (i, j + width) not in consumed:
                width += 1

            height = 1
            can_extend = True
            while can_extend:
                next_row = i + height
                row_cells = [(next_row, col) for col in range(j, j + width)]
                if all(cell in wall_set and cell not in consumed for cell in row_cells):
                    height += 1
                else:
                    can_extend = False

            for row in range(i, i + height):
                for col in range(j, j + width):
                    consumed.add((row, col))

            obstacles.append(Obstacle(j * cell_size,i * cell_size,width * cell_size,height * cell_size,))

        return obstacles


    # ----------------------------------------
    def _build_communication_zones(self, grid_map, cell_size):
        if self.no_com_zone_count <= 0:
            return []

        zones = []
        max_zone_width = max(self.no_com_zone_min_size, self.no_com_zone_max_size)
        max_zone_height = max(self.no_com_zone_min_size, self.no_com_zone_max_size)
        max_start_row = max(1, self.height - max_zone_height - 1)
        max_start_col = max(1, self.width - max_zone_width - 1)

        for index in range(self.no_com_zone_count):
            zone_width = self.rng.randint(self.no_com_zone_min_size, max_zone_width)
            zone_height = self.rng.randint(self.no_com_zone_min_size, max_zone_height)
            start_row = self.rng.randint(1, max_start_row)
            start_col = self.rng.randint(1, max_start_col)

            zones.append(
                CommunicationZone(
                    name=f"no-com-{index}",
                    x=start_col * cell_size,
                    y=start_row * cell_size,
                    width=zone_width * cell_size,
                    height=zone_height * cell_size,
                    blocks_communication=True,
                )
            )

        return zones

    # ==================================
    








    # ========= GENERATE GRID ===========
    def generate_grid(self, grid_map):
        # Fill everything with walls
        for i in range(self.height):
            for j in range(self.width):
                grid_map.set_cell(i, j, WALL)

        # Row 0 for drone spawn
        for j in range(self.width):
            grid_map.set_cell(0, j, FREE)

        # Maze carving and add blocks
        self._carve_paths(grid_map)
        self._add_buildings(grid_map)

        # Entry points
        self._add_gaps(grid_map)

        # Place victims and make sure path
        self._place_victims(grid_map)
        self._ensure_victim_paths(grid_map)

        return grid_map


    # ----------------------------------------
    def _carve_paths(self, grid_map):
        # Simple DFS maze (skip row 0)
        def carve(x, y):
            directions = [(2,0), (-2,0), (0,2), (0,-2)]
            self.rng.shuffle(directions)
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if 1 <= nx < self.height and 0 <= ny < self.width:
                    if grid_map.get_cell(nx, ny) == WALL:
                        grid_map.set_cell(x + dx//2, y + dy//2, FREE)
                        grid_map.set_cell(nx, ny, FREE)
                        carve(nx, ny)
        carve(1, 1)


    # ----------------------------------------
    def _add_buildings(self, grid_map):
        # Add wall based on density
        num_buildings = int(self.building_density * self.width)

        for _ in range(num_buildings):
            x = self.rng.randint(2, self.height - 5)
            y = self.rng.randint(0, self.width - 5)

            h = self.rng.randint(2, 4)
            w = self.rng.randint(2, 4)

            for i in range(x, min(x + h, self.height)):
                for j in range(y, min(y + w, self.width)):
                    grid_map.set_cell(i, j, WALL)


    # ----------------------------------------
    def _add_gaps(self, grid_map):
        # Make gaps for drone to move
        for i in range(1, self.height):
            for j in range(self.width):
                if grid_map.is_wall(i, j):
                    if self.rng.random() < self.gap_probability:
                        grid_map.set_cell(i, j, FREE)


    # ----------------------------------------
    def _place_victims(self, grid_map):
        # Place victim on free cell (Except row 0)
        count = (self.width * self.height) // 50
        while count:
            x = self.rng.randint(1, self.height - 1)
            y = self.rng.randint(0, self.width - 1)

            if grid_map.is_free(x, y):
                count-=1
                grid_map.set_cell(x, y, VICTIM)


    # ----------------------------------------
    def _ensure_victim_paths(self, grid_map):
        # Run DFS to connect victim to row 0 (PATH)
        victims = self._get_victim_positions(grid_map)

        for victim in victims:
            reachable = self._get_row_zero_reachable(grid_map)
            if victim in reachable:
                continue

            path = self._find_min_break_path(grid_map, victim, reachable)
            if path:
                self._carve_connection_path(grid_map, path)

    def _get_victim_positions(self, grid_map):
        victims = []
        for i in range(self.height):
            for j in range(self.width):
                if grid_map.get_cell(i, j) == VICTIM:
                    victims.append((i, j))
        return victims

    def _get_row_zero_reachable(self, grid_map):
        reachable = set()
        queue = deque()

        for j in range(self.width):
            start = (0, j)
            if grid_map.get_cell(*start) != WALL:
                reachable.add(start)
                queue.append(start)

        while queue:
            x, y = queue.popleft()
            for nx, ny in grid_map.get_neighbors(x, y):
                if (nx, ny) in reachable:
                    continue
                if grid_map.get_cell(nx, ny) == WALL:
                    continue
                reachable.add((nx, ny))
                queue.append((nx, ny))

        return reachable

    def _find_min_break_path(self, grid_map, start, targets):
        if not targets:
            return None

        inf = float("inf")
        dp = [[inf for _ in range(self.width)] for _ in range(self.height)]
        parent = {}
        heap = []

        sx, sy = start
        dp[sx][sy] = 0
        heapq.heappush(heap, (0, start))

        while heap:
            cost, (x, y) = heapq.heappop(heap)
            if cost != dp[x][y]:
                continue

            if (x, y) in targets:
                return self._reconstruct_path(parent, start, (x, y))

            for nx, ny in grid_map.get_neighbors(x, y):
                next_cost = cost + (1 if grid_map.get_cell(nx, ny) == WALL else 0)
                if next_cost < dp[nx][ny]:
                    dp[nx][ny] = next_cost
                    parent[(nx, ny)] = (x, y)
                    heapq.heappush(heap, (next_cost, (nx, ny)))

        return None

    def _reconstruct_path(self, parent, start, end):
        path = [end]
        current = end

        while current != start:
            current = parent[current]
            path.append(current)

        path.reverse()
        return path

    def _carve_connection_path(self, grid_map, path):
        for x, y in path:
            if grid_map.get_cell(x, y) == WALL:
                grid_map.set_cell(x, y, FREE)

    # ==================================










    # ========= GENERATE FLOORPLAN ===========
    def generate_floorplan_grid(self, grid_map):
        # Start with open floor
        for i in range(self.height):
            for j in range(self.width):
                grid_map.set_cell(i, j, FREE)

        # Add walls and region
        self._add_perimeter_walls(grid_map)
        self._split_region(grid_map, 1, 1, self.height - 2, self.width - 2, depth=0)
        
        # Place Victims
        self._place_floorplan_victims(grid_map)
        self._ensure_floorplan_connectivity(grid_map)
        return grid_map
    

    # ----------------------------------------
    def _add_perimeter_walls(self, grid_map):
        # Close perimeter (No Wander)
        for i in range(self.height):
            grid_map.set_cell(i, 0, WALL)
            grid_map.set_cell(i, self.width - 1, WALL)

        for j in range(self.width):
            grid_map.set_cell(0, j, WALL)
            grid_map.set_cell(self.height - 1, j, WALL)
    

    # ----------------------------------------
    # Recursive Division Algorithm (for maze / dungeon generation)
    def _split_region(self, grid_map, top, left, bottom, right, depth):
        min_room_span = 6
        room_height = bottom - top + 1
        room_width = right - left + 1

        if room_height < min_room_span * 2 and room_width < min_room_span * 2:
            return

        split_horizontal = room_height >= room_width
        if room_height < min_room_span * 2:
            split_horizontal = False
        if room_width < min_room_span * 2:
            split_horizontal = True

        if split_horizontal:
            candidates = [row for row in range(top + 3, bottom - 2) if row % 2 == 0]
            if not candidates:
                return

            wall_row = self.rng.choice(candidates)
            for col in range(left, right + 1):
                grid_map.set_cell(wall_row, col, WALL)

            self._open_doorways_on_wall(grid_map, wall_row, left, right, horizontal=True)
            self._split_region(grid_map, top, left, wall_row - 1, right, depth + 1)
            self._split_region(grid_map, wall_row + 1, left, bottom, right, depth + 1)
            return

        candidates = [col for col in range(left + 3, right - 2) if col % 2 == 0]
        if not candidates:
            return

        wall_col = self.rng.choice(candidates)
        for row in range(top, bottom + 1):
            grid_map.set_cell(row, wall_col, WALL)

        self._open_doorways_on_wall(grid_map, wall_col, top, bottom, horizontal=False)
        self._split_region(grid_map, top, left, bottom, wall_col - 1, depth + 1)
        self._split_region(grid_map, top, wall_col + 1, bottom, right, depth + 1)

    def _open_doorways_on_wall(self, grid_map, wall_index, start, end, horizontal):
        span = end - start + 1
        door_count = 2 if span > 14 else 1
        candidate_positions = [pos for pos in range(start + 1, end) if pos % 2 == 1]

        if not candidate_positions:
            return

        doors = self.rng.sample(candidate_positions, k=min(door_count, len(candidate_positions)))

        for door in doors:
            if horizontal:
                grid_map.set_cell(wall_index, door, FREE)
            else:
                grid_map.set_cell(door, wall_index, FREE)


    # ----------------------------------------
    def _place_floorplan_victims(self, grid_map):
        count = max(1, (self.width * self.height) // 65)
        attempts = 0
        max_attempts = count * 40

        while count and attempts < max_attempts:
            attempts += 1
            x = self.rng.randint(1, self.height - 2)
            y = self.rng.randint(1, self.width - 2)

            if not grid_map.is_free(x, y):
                continue

            neighbors = grid_map.get_neighbors(x, y)
            wall_neighbors = sum(1 for nx, ny in neighbors if grid_map.is_wall(nx, ny))
            if wall_neighbors >= 3:
                continue

            grid_map.set_cell(x, y, VICTIM)
            count -= 1

    def _ensure_floorplan_connectivity(self, grid_map):
        reachable = self._get_floorplan_reachable(grid_map)
        if not reachable:
            return

        movable = self._get_movable_cells(grid_map)
        while True:
            blocked = movable - reachable
            if not blocked:
                return

            start = min(blocked, key=lambda cell: (cell[0], cell[1]))
            path = self._find_min_break_path(grid_map, start, reachable)
            if not path:
                return

            self._carve_connection_path(grid_map, path)
            reachable = self._get_floorplan_reachable(grid_map)
            movable = self._get_movable_cells(grid_map)

    def _get_floorplan_reachable(self, grid_map):
        movable = self._get_movable_cells(grid_map)
        if not movable:
            return set()

        start = min(movable, key=lambda cell: (cell[0], cell[1]))
        reachable = {start}
        queue = deque([start])

        while queue:
            x, y = queue.popleft()
            for nx, ny in grid_map.get_neighbors(x, y):
                neighbor = (nx, ny)
                if neighbor in reachable:
                    continue
                if not grid_map.can_move(nx, ny):
                    continue
                reachable.add(neighbor)
                queue.append(neighbor)

        return reachable

    def _get_movable_cells(self, grid_map):
        cells = set()
        for i in range(self.height):
            for j in range(self.width):
                if grid_map.can_move(i, j):
                    cells.add((i, j))
        return cells
