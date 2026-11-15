"""Draw a StatsBomb-sized pitch (120 x 80) to use as a Tableau background image."""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Rectangle, Circle

out = sys.argv[1]
LINE, GRASS = "#B9C4CA", "#FFFFFF"

fig = plt.figure(figsize=(12, 8), dpi=150)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 120); ax.set_ylim(80, 0)   # StatsBomb y runs top to bottom
ax.axis("off"); fig.patch.set_facecolor(GRASS)
kw = dict(fill=False, ec=LINE, lw=2)

ax.add_patch(Rectangle((0, 0), 120, 80, **kw))
ax.plot([60, 60], [0, 80], color=LINE, lw=2)
ax.add_patch(Circle((60, 40), 10, **kw))
for x0, sign in ((0, 1), (120, -1)):
    ax.add_patch(Rectangle((x0 if sign == 1 else 102, 18), 18, 44, **kw))   # penalty box
    ax.add_patch(Rectangle((x0 if sign == 1 else 114, 30), 6, 20, **kw))    # six-yard box
    ax.add_patch(Circle((x0 + sign * 12, 40), 0.5, color=LINE))             # penalty spot
    ax.add_patch(Arc((x0 + sign * 12, 40), 20, 20, theta1=-53 if sign == 1 else 127,
                     theta2=53 if sign == 1 else 233, ec=LINE, lw=2))
fig.savefig(out, facecolor=GRASS)
print("saved", out)
