import math


def world_to_grid(x, y, cell_size):
    return int(y // cell_size), int(x // cell_size)


def grid_to_world(i, j, cell_size):
    return (j + 0.5) * cell_size, (i + 0.5) * cell_size


def raytrace_cells(start_cell, end_cell):
    x0, y0 = start_cell
    x1, y1 = end_cell

    cells = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        cells.append((x0, y0))
        if (x0, y0) == (x1, y1):
            break

        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy

    return cells


def obstacle_world_position(origin_x, origin_y, angle, distance):
    return (
        origin_x + distance * math.cos(angle),
        origin_y + distance * math.sin(angle),
    )
