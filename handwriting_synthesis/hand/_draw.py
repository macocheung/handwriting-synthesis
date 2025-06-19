import numpy as np
import svgwrite

from handwriting_synthesis import drawing


def _draw(strokes, lines, filename, stroke_colors=None, stroke_widths=None):
    stroke_colors = stroke_colors or ['black'] * len(lines)
    stroke_widths = stroke_widths or [2] * len(lines)

    line_height = 60

    # store processed coordinates so we can compute final bounds
    processed = []
    path_params = []

    initial_coord = np.array([0, -(3 * line_height / 4)])
    for offsets, line, color, width in zip(strokes, lines, stroke_colors, stroke_widths):

        if not line:
            initial_coord[1] -= line_height
            continue

        offsets[:, :2] *= 1.5
        pts = drawing.offsets_to_coords(offsets)
        pts = drawing.denoise(pts)
        pts[:, :2] = drawing.align(pts[:, :2])

        pts[:, 1] *= -1
        pts[:, :2] -= pts[:, :2].min() + initial_coord

        processed.append(pts)
        path_params.append((pts, color, width))

        initial_coord[1] -= line_height

    if not processed:
        svgwrite.Drawing(filename=filename).save()
        return

    all_pts = np.vstack([p[:, :2] for p in processed])
    min_x, min_y = all_pts.min(axis=0)
    max_x, max_y = all_pts.max(axis=0)

    width = max_x - min_x
    height = max_y - min_y

    dwg = svgwrite.Drawing(
        filename=filename,
        size=(f"{width}px", f"{height}px")
    )
    dwg.viewbox(width=width, height=height)
    dwg.add(dwg.rect(insert=(0, 0), size=(width, height), fill='white'))

    for pts, color, w in path_params:
        pts[:, 0] -= min_x
        pts[:, 1] -= min_y
        prev_eos = 1.0
        p = []
        for x, y, eos in pts:
            p.append('{}{},{}'.format('M' if prev_eos == 1.0 else 'L', x, y))
            prev_eos = eos
        path = svgwrite.path.Path(' '.join(p))
        path = path.stroke(color=color, width=w, linecap='round').fill("none")
        dwg.add(path)

    dwg.save()
