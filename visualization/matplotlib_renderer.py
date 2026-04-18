import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle

from utils.constants import FREE, VICTIM, WALL


fig = None
ax = None
_continuous_cache = {}


def _ensure_figure():
    global fig, ax
    if fig is None or ax is None:
        plt.ion()
        fig, ax = plt.subplots()
    return fig, ax


def render_environment(env, agents, step=None, config=None):
    if getattr(config, "SIMULATION_MODE", "grid") == "continuous":
        render_continuous(env, agents, step)
    else:
        render_grid(env, agents, step, config)


def render_grid(env, agents, step=None, config=None):
    _, axis = _ensure_figure()
    axis.clear()
    grid = env.grid_map.grid
    height = len(grid)
    width = len(grid[0])
    base = np.zeros((height, width))

    for i in range(height):
        for j in range(width):
            cell = grid[i][j]
            if cell == WALL:
                base[i][j] = -1
            elif cell == FREE:
                base[i][j] = 0.2
            elif cell == VICTIM:
                base[i][j] = 0.8
            else:
                base[i][j] = 0.5

    num_colors = 3 + len(agents)
    cmap = plt.cm.get_cmap("tab20", num_colors)
    axis.imshow(base, cmap=cmap, vmin=-1, vmax=1)

    colors = plt.cm.get_cmap("tab10", max(len(agents), 1))
    for agent in agents:
        x, y = agent.position
        facecolor = "#7a7a7a" if agent.is_failed else colors(agent.id % 10)
        axis.add_patch(
            Circle(
                (y, x),
                radius=0.33,
                facecolor=facecolor,
                edgecolor="black",
                linewidth=1.4,
                zorder=3,
            )
        )
        axis.text(
            y,
            x,
            "*" if agent.is_failed else str(agent.id),
            color="white",
            ha="center",
            va="center",
            fontsize=8,
            zorder=4,
        )

    if step is not None:
        axis.set_title(f"Swarm SAR Simulation - Step {step}")

    axis.set_xticks([])
    axis.set_yticks([])
    plt.pause(0.0000001)


def render_continuous(env, agents, step=None):
    _, axis = _ensure_figure()
    cache_key = (id(env), len(env.obstacles), len(env.victims), len(agents))
    cache = _continuous_cache.get("scene")

    if cache is None or cache.get("key") != cache_key:
        axis.clear()
        axis.set_xlim(0, env.world_width)
        axis.set_ylim(env.world_height, 0)
        axis.set_aspect("equal")
        axis.set_facecolor("#f7f4ed")
        axis.set_xticks([])
        axis.set_yticks([])

        for zone in getattr(env.playground, "communication_zones", []):
            axis.add_patch(
                Rectangle(
                    (zone.x, zone.y),
                    zone.width,
                    zone.height,
                    facecolor="#f2b56b",
                    edgecolor="#8a4f08",
                    linewidth=1.0,
                    alpha=0.28,
                    zorder=2,
                )
            )

        for obstacle in env.obstacles:
            axis.add_patch(
                Rectangle(
                    (obstacle.x, obstacle.y),
                    obstacle.width,
                    obstacle.height,
                    facecolor="#2f2f2f",
                    edgecolor="#1a1a1a",
                    linewidth=0.4,
                )
            )

        colors = plt.cm.get_cmap("tab10", max(len(agents), 1))
        radius = getattr(env, "agent_radius", 0.18)

        victim_artists = []
        for victim in env.victims:
            patch = Circle(
                (victim.position[0], victim.position[1]),
                radius=radius,
                facecolor="#d84a4a",
                edgecolor="#7a1717",
                linewidth=1.0,
                zorder=4,
            )
            axis.add_patch(patch)
            victim_artists.append(patch)

        agent_artists = []
        heading_artists = []
        label_artists = []
        for agent in agents:
            x, y = agent.measured_gps_position()
            facecolor = "#7a7a7a" if agent.is_failed else colors(agent.id % 10)
            body = Circle(
                (x, y),
                radius=radius,
                facecolor=facecolor,
                edgecolor="black",
                linewidth=1.0,
                zorder=5,
            )
            axis.add_patch(body)

            heading_len = radius * 2.2
            hx = x + heading_len * np.cos(agent.heading)
            hy = y + heading_len * np.sin(agent.heading)
            (heading_line,) = axis.plot([x, hx], [y, hy], color="black", linewidth=1.0, zorder=6)
            label = axis.text(
                x,
                y,
                "*" if agent.is_failed else str(agent.id),
                color="white",
                ha="center",
                va="center",
                fontsize=7,
                fontweight="bold",
                zorder=7,
            )
            agent_artists.append(body)
            heading_artists.append(heading_line)
            label_artists.append(label)

        title = axis.set_title("")
        cache = {
            "key": cache_key,
            "victims": victim_artists,
            "agents": agent_artists,
            "headings": heading_artists,
            "labels": label_artists,
            "title": title,
            "radius": radius,
        }
        _continuous_cache["scene"] = cache

    radius = cache["radius"]

    for patch, victim in zip(cache["victims"], env.victims):
        patch.center = victim.position
        patch.set_visible(not victim.rescued)

    for body, heading_line, label, agent in zip(
        cache["agents"],
        cache["headings"],
        cache["labels"],
        agents,
    ):
        x, y = agent.measured_gps_position()
        body.center = (x, y)
        body.set_facecolor("#7a7a7a" if agent.is_failed else plt.cm.get_cmap("tab10", max(len(agents), 1))(agent.id % 10))
        heading_len = radius * 2.2
        hx = x + heading_len * np.cos(agent.heading)
        hy = y + heading_len * np.sin(agent.heading)
        heading_line.set_data([x, hx], [y, hy])
        label.set_position((x, y))
        label.set_text("*" if agent.is_failed else str(agent.id))

    if step is not None:
        cache["title"].set_text(f"Continuous Swarm SAR - Step {step}")

    fig.canvas.draw_idle()
    plt.pause(0.0000001)
