from visualization import matplotlib_renderer


def render_environment(env, agents, step=None, config=None, metrics_tracker=None):
    matplotlib_renderer.render_environment(env, agents, step, config)
    if metrics_tracker is not None:
        from visualization.metrics_visualizer import render_metrics
        render_metrics(metrics_tracker, config)
