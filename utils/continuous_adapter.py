def world_to_grid(x, y, cell_size):
    return int(y // cell_size), int(x // cell_size)


def grid_to_world(i, j, cell_size):
    return (j + 0.5) * cell_size, (i + 0.5) * cell_size
