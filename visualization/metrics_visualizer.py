import tkinter as tk
from tkinter import ttk

_metrics_window = None
_metrics_canvas = None
_metrics_title = None

def _ensure_metrics_figure():
    global _metrics_window, _metrics_canvas, _metrics_title

    if _metrics_window is None or not _metrics_window.winfo_exists():
        _metrics_window = tk.Toplevel()
        _metrics_window.title("Mission Metrics")
        _metrics_window.geometry("800x600")
        _metrics_window.configure(bg="#ffffff")

        _metrics_title = tk.StringVar()
        ttk.Label(
            _metrics_window, 
            textvariable=_metrics_title, 
            font=("Segoe UI", 11, "bold"),
            background="#ffffff"
        ).pack(pady=5)

        _metrics_canvas = tk.Canvas(_metrics_window, bg="#ffffff", highlightthickness=0)
        _metrics_canvas.pack(fill="both", expand=True, padx=10, pady=10)

        def on_close():
            global _metrics_window
            _metrics_window.destroy()
            _metrics_window = None

        _metrics_window.protocol("WM_DELETE_WINDOW", on_close)

    return _metrics_window, _metrics_canvas, _metrics_title


def _draw_chart(canvas, x0, y0, w, h, title, steps, values, color, ylabel):
    margin_left = 50
    margin_bottom = 30
    margin_top = 30
    margin_right = 20

    plot_x = x0 + margin_left
    plot_y = y0 + margin_top
    plot_w = w - margin_left - margin_right
    plot_h = h - margin_top - margin_bottom

    canvas.create_text(x0 + w / 2, y0 + 15, text=title, font=("Segoe UI", 10, "bold"), fill="black")
    canvas.create_text(x0 + 15, y0 + h / 2, text=ylabel, angle=90, font=("Segoe UI", 9), fill="black")
    canvas.create_text(x0 + w / 2, y0 + h - 10, text="Step", font=("Segoe UI", 9), fill="black")

    canvas.create_line(plot_x, plot_y, plot_x, plot_y + plot_h, fill="black")
    canvas.create_line(plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h, fill="black")

    if not steps: return

    min_x, max_x = 0, max(1, steps[-1])
    
    max_y = 1.0
    if "Count" in ylabel:
        max_y = max(5.0, max(values) * 1.2) if max(values) > 0 else 5.0

    grid_steps_y = 4
    for i in range(grid_steps_y + 1):
        gy = plot_y + plot_h - (i / grid_steps_y) * plot_h
        canvas.create_line(plot_x, gy, plot_x + plot_w, gy, fill="#e0e0e0", dash=(2, 2))
        val = max_y * (i / grid_steps_y)
        val_str = f"{val:.1f}" if "Ratio" in ylabel else f"{int(val)}"
        canvas.create_text(plot_x - 5, gy, text=val_str, anchor="e", font=("Segoe UI", 8))

    grid_steps_x = 4
    for i in range(grid_steps_x + 1):
        gx = plot_x + (i / grid_steps_x) * plot_w
        canvas.create_line(gx, plot_y, gx, plot_y + plot_h, fill="#e0e0e0", dash=(2, 2))
        val = max_x * (i / grid_steps_x)
        canvas.create_text(gx, plot_y + plot_h + 5, text=f"{int(val)}", anchor="n", font=("Segoe UI", 8))

    def to_px(sx, sy):
        px = plot_x + (sx / max_x) * plot_w
        py = plot_y + plot_h - (sy / max_y) * plot_h
        return px, py

    points = []
    for sx, sy in zip(steps, values):
        points.extend(to_px(sx, sy))

    if len(points) >= 4:
        canvas.create_line(*points, fill=color, width=2)
    elif len(points) == 2:
        px, py = points
        canvas.create_oval(px - 2, py - 2, px + 2, py + 2, fill=color, outline="")


def render_metrics(metrics_tracker, config=None):
    if metrics_tracker is None:
        return

    if not getattr(config, "SHOW_METRICS_DASHBOARD", True):
        return

    window, canvas, title_var = _ensure_metrics_figure()
    if window is None:
        return

    history = metrics_tracker.history
    steps = history["step"]
    if not steps:
        return

    series = [
        ("Coverage", steps, history["coverage"], "#1f77b4", "Ratio"),
        ("Overlap", steps, history["overlap"], "#ff7f0e", "Ratio"),
        ("Victims", steps, history["detected_victims"], "#2ca02c", "Count"),
        ("Rescued", steps, history["rescued_victims"], "#d62728", "Count"),
    ]

    canvas.delete("all")
    w = max(100, canvas.winfo_width())
    h = max(100, canvas.winfo_height())

    if w <= 100 or h <= 100:
        w = 800 - 20
        h = 600 - 40

    cw, ch = w / 2, h / 2

    _draw_chart(canvas, 0, 0, cw, ch, *series[0])
    _draw_chart(canvas, cw, 0, cw, ch, *series[1])
    _draw_chart(canvas, 0, ch, cw, ch, *series[2])
    _draw_chart(canvas, cw, ch, cw, ch, *series[3])

    latest = metrics_tracker.latest()
    title_var.set(
        f"Mission Metrics  "
        f"coverage={latest['coverage']:.1%}  "
        f"overlap={latest['overlap']:.1%}  "
        f"suspected={latest['suspected_victims']}  "
        f"detected={latest['detected_victims']}  "
        f"rescued={latest['rescued_victims']}"
    )

    window.update_idletasks()
    window.update()
