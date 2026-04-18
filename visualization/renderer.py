from visualization import matplotlib_renderer


def render_environment(env, agents, step=None, config=None):
    matplotlib_renderer.render_environment(env, agents, step, config)
