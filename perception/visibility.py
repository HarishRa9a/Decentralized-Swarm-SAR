def is_visible(start, end, grid_map):
    x1, y1 = start
    x2, y2 = end

    dx = abs(x2 - x1)
    dy = abs(y2 - y1)

    sx = 1 if x2 > x1 else -1
    sy = 1 if y2 > y1 else -1

    err = dx - dy

    x, y = x1, y1

    while (x, y) != (x2, y2):

        # move first (so we skip checking start cell)
        e2 = 2 * err

        nx, ny = x, y

        if e2 > -dy:
            err -= dy
            nx += sx

        if e2 < dx:
            err += dx
            ny += sy

        # corner cutting prevention
        if nx != x and ny != y:
            if grid_map.is_wall(x + sx, y) or grid_map.is_wall(x, y + sy):
                return False

        x, y = nx, ny

        if not grid_map.in_bounds(x, y):
            return False

        # block BEFORE reaching target
        if (x, y) != (x2, y2) and grid_map.is_wall(x, y):
            return False

    return True