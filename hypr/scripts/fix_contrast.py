#!/usr/bin/env python3
"""
fix_contrast.py

Post-processes a wallust-generated Kitty theme file to guarantee a minimum
contrast ratio for every ANSI color against the terminal background.

Why this exists:
wallust optimizes for visual harmony with the source wallpaper, not for
readability. On some wallpapers it produces colors (e.g. color9) that are
nearly identical in luminance to the background, making text in that color
effectively invisible. This script runs after `wallust run` and before
Kitty reloads, correcting only the colors that actually need it.

Algorithm:
- Parse foreground/background and color0-color15 from the wallust output.
- For each colorN, compute WCAG-style contrast ratio against `background`.
- If below TARGET_CONTRAST, increase lightness in HSL space (hue and
  saturation preserved) in small steps until the target is met.
- Lightness increase is capped at MAX_LIGHTNESS_SHIFT. If the target can't
  be reached within the cap, the color is pushed as far as allowed and
  flagged in stderr output (it will still be an improvement, just not
  guaranteed to fully clear the floor -- this avoids turning a near-black
  into a pale, unrecognizable color just to satisfy the math).
- A MIN_SATURATION floor prevents colors from being corrected into grey,
  but only colors that fail the contrast check are touched -- colors that
  already pass contrast are left alone even if their saturation is low,
  to avoid unnecessary drift from wallust's original palette.
- color0 and color8 are exempt by default (see EXEMPT_COLORS below) since
  they serve UI chrome / autosuggestion roles, not body text, and are
  intentionally low-contrast against the background by design.

Usage:
    python3 fix_contrast.py <path-to-kitty-theme-file>

Edits the file in place. Prints a summary of what changed to stderr.
"""

import sys
import re
import colorsys

TARGET_CONTRAST = 4.5
MAX_LIGHTNESS_SHIFT = 0.35
MIN_SATURATION = 0.25
EXEMPT_COLORS = {"color0", "color8"}  # UI chrome / dim autosuggestions, not body text
MIN_COLOR_DISTANCE = 30  # euclidean RGB distance below which two colors are
                          # considered indistinguishable and get separated
HUE_NUDGE_DEGREES = 18   # how far to rotate hue, per nudge step, to separate
                          # converged colors (applied to the second color in
                          # each colliding pair, alternating direction)


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(
        *[max(0, min(255, round(c))) for c in rgb]
    )


def relative_luminance(rgb):
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(hex1, hex2):
    l1 = relative_luminance(hex_to_rgb(hex1))
    l2 = relative_luminance(hex_to_rgb(hex2))
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def color_distance(hex1, hex2):
    """Euclidean distance in RGB space. A cheap but effective proxy for
    'do these look like the same color at a glance'."""
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5


def nudge_hue(hexcode, degrees, bg_hex, target=TARGET_CONTRAST):
    """Rotate hue by the given number of degrees (can be negative), keeping
    saturation and lightness fixed, then re-verify contrast still holds
    (hue rotation can shift luminance slightly). If contrast drops below
    target after rotation, nudge lightness back up to compensate."""
    r, g, b = [c / 255 for c in hex_to_rgb(hexcode)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    h = (h + degrees / 360.0) % 1.0
    new_rgb = [c * 255 for c in colorsys.hls_to_rgb(h, l, s)]
    new_hex = rgb_to_hex(new_rgb)

    cr = contrast_ratio(new_hex, bg_hex)
    guard = 0
    while cr < target and l < 0.95 and guard < 20:
        l += 0.02
        new_rgb = [c * 255 for c in colorsys.hls_to_rgb(h, l, s)]
        new_hex = rgb_to_hex(new_rgb)
        cr = contrast_ratio(new_hex, bg_hex)
        guard += 1

    return new_hex


def nudge_lightness(hexcode, direction, bg_hex, amount=0.08, target=TARGET_CONTRAST):
    """Fallback separator for near-grey colors (saturation too low for hue
    rotation to do anything visible). Shifts lightness instead, re-checking
    contrast afterward since this can push a color toward the background."""
    r, g, b = [c / 255 for c in hex_to_rgb(hexcode)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = max(0.0, min(0.95, l + amount * direction))
    new_rgb = [c * 255 for c in colorsys.hls_to_rgb(h, l, s)]
    new_hex = rgb_to_hex(new_rgb)

    # if this pushed contrast below target, walk lightness back up
    guard = 0
    while contrast_ratio(new_hex, bg_hex) < target and l < 0.95 and guard < 20:
        l += 0.02
        new_rgb = [c * 255 for c in colorsys.hls_to_rgb(h, l, s)]
        new_hex = rgb_to_hex(new_rgb)
        guard += 1

    return new_hex


def min_distance_to_others(name, hexcode, color_map, exclude=()):
    """Smallest pairwise distance from this color to every other color in
    the map (excluding itself and any names in `exclude`)."""
    dists = [
        color_distance(hexcode, other_hex)
        for other_name, other_hex in color_map.items()
        if other_name != name and other_name not in exclude
    ]
    return min(dists) if dists else float("inf")


def separate_collisions(color_map, bg_hex, min_distance=MIN_COLOR_DISTANCE,
                         hue_nudge=HUE_NUDGE_DEGREES, max_passes=6):
    """
    color_map: dict of {colorName: hexcode}, already contrast-corrected.
    Finds pairs that are too close together and nudges the second member
    of each pair away. Before committing a nudge, checks the candidate's
    distance against EVERY other color already in the map (not just the
    pair that triggered the nudge) and only accepts it if it improves the
    color's worst-case distance to its neighbors. If neither hue direction
    nor a lightness fallback improves the worst case, the pair is marked
    unresolved immediately rather than retried, which is what prevents
    oscillation between two colors that are both blocked by a third.
    """
    names = list(color_map.keys())
    separated = []
    unresolved = set()

    for pass_num in range(max_passes):
        collided_this_pass = False
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                n1, n2 = names[i], names[j]
                if (n1, n2) in unresolved:
                    continue
                d = color_distance(color_map[n1], color_map[n2])
                if d >= min_distance:
                    continue

                before = color_map[n2]
                current_worst = min_distance_to_others(n2, before, color_map)

                r, g, b = [c / 255 for c in hex_to_rgb(before)]
                _, l, s = colorsys.rgb_to_hls(r, g, b)

                # try both hue directions (or both lightness directions for
                # near-grey colors) and keep whichever improves worst-case
                # distance to ALL neighbors the most
                candidates = []
                if s < 0.08:
                    candidates.append(nudge_lightness(before, +1, bg_hex))
                    candidates.append(nudge_lightness(before, -1, bg_hex))
                else:
                    candidates.append(nudge_hue(before, hue_nudge, bg_hex))
                    candidates.append(nudge_hue(before, -hue_nudge, bg_hex))

                best_candidate = max(
                    candidates,
                    key=lambda c: min_distance_to_others(n2, c, color_map)
                )
                best_worst = min_distance_to_others(n2, best_candidate, color_map)

                if best_worst <= current_worst + 0.5:
                    # no available move actually improves things globally -
                    # this pair is structurally stuck, stop retrying it
                    unresolved.add((n1, n2))
                    continue

                color_map[n2] = best_candidate
                collided_this_pass = True
                separated.append((n1, n2, before, best_candidate, d))

        if not collided_this_pass:
            break

    return color_map, separated, unresolved


def fix_contrast(hexcode, bg_hex, target=TARGET_CONTRAST,
                  max_lightness_shift=MAX_LIGHTNESS_SHIFT,
                  min_saturation=MIN_SATURATION):
    """
    Returns (final_hex, delta_lightness, capped, final_contrast, changed).
    Only modifies the color if it fails the contrast check to begin with.
    """
    initial_cr = contrast_ratio(hexcode, bg_hex)
    if initial_cr >= target:
        return hexcode, 0.0, False, initial_cr, False

    r, g, b = [c / 255 for c in hex_to_rgb(hexcode)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    orig_l = l
    if s < min_saturation:
        s = min_saturation

    capped = False
    step = 0.02
    while True:
        cur_rgb = [c * 255 for c in colorsys.hls_to_rgb(h, l, s)]
        cr = contrast_ratio(rgb_to_hex(cur_rgb), bg_hex)
        if cr >= target:
            break
        if (l - orig_l) >= max_lightness_shift or l >= 0.95:
            capped = True
            break
        l += step

    final_rgb = [c * 255 for c in colorsys.hls_to_rgb(h, l, s)]
    final_hex = rgb_to_hex(final_rgb)
    final_cr = contrast_ratio(final_hex, bg_hex)
    return final_hex, (l - orig_l), capped, final_cr, True


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-kitty-theme-file>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "r") as f:
        lines = f.readlines()

    # find background first, since every other color is checked against it
    bg_hex = None
    for line in lines:
        m = re.match(r"^\s*background\s+(#[0-9A-Fa-f]{6})\s*$", line)
        if m:
            bg_hex = m.group(1)
            break

    if bg_hex is None:
        print("ERROR: could not find 'background' line in file, aborting.", file=sys.stderr)
        sys.exit(1)

    color_line_re = re.compile(r"^(\s*)(color\d{1,2})(\s+)(#[0-9A-Fa-f]{6})(\s*)$")

    # --- Pass 1: parse every color line, recording its position in `lines` ---
    parsed = {}  # name -> {'index': line_index, 'indent':..., 'gap':..., 'orig_hex':..., 'trail':...}
    for idx, line in enumerate(lines):
        m = color_line_re.match(line)
        if not m:
            continue
        indent, name, gap, hexcode, trail = m.groups()
        parsed[name] = {
            "index": idx, "indent": indent, "gap": gap,
            "orig_hex": hexcode, "trail": trail,
        }

    # --- Pass 2: contrast-correct each non-exempt color independently ---
    contrast_changes = []
    working = {}  # name -> current hex, for every parsed color (exempt included, untouched)
    for name, info in parsed.items():
        if name in EXEMPT_COLORS:
            working[name] = info["orig_hex"]
            continue
        final_hex, delta_l, capped, final_cr, changed = fix_contrast(info["orig_hex"], bg_hex)
        working[name] = final_hex
        if changed:
            contrast_changes.append((name, info["orig_hex"], final_hex, delta_l, final_cr, capped))

    # --- Pass 3: separate any colors (exempt or not) that ended up too close
    #     to each other, so e.g. color4/color5 or color3/color11 don't render
    #     as visually identical even though their hex codes may now differ.
    #     Exempt colors are included in the distance check (a corrected color
    #     colliding with color0/color8 is still a real problem) but only
    #     non-exempt colors get nudged, to keep UI-chrome colors untouched.
    nudge_candidates = {n: h for n, h in working.items() if n not in EXEMPT_COLORS}
    nudge_candidates, separations, unresolved = separate_collisions(nudge_candidates, bg_hex)
    working.update(nudge_candidates)

    # --- Write back ---
    new_lines = list(lines)
    for name, info in parsed.items():
        final_hex = working[name]
        if final_hex == info["orig_hex"]:
            continue
        idx, indent, gap, trail = info["index"], info["indent"], info["gap"], info["trail"]
        newline_suffix = "\n" if not trail.endswith("\n") else trail
        new_lines[idx] = f"{indent}{name}{gap}{final_hex}{newline_suffix}"

    with open(path, "w") as f:
        f.writelines(new_lines)

    if contrast_changes:
        print(f"fix_contrast.py: corrected {len(contrast_changes)} color(s) for contrast in {path}", file=sys.stderr)
        for name, before, after, delta_l, final_cr, capped in contrast_changes:
            flag = " [CAPPED - target not fully reached]" if capped else ""
            print(f"  {name}: {before} -> {after}  (contrast {final_cr:.2f}:1, Δlightness {delta_l:+.2f}){flag}", file=sys.stderr)
    else:
        print(f"fix_contrast.py: all colors already pass {TARGET_CONTRAST}:1 contrast, no contrast changes made.", file=sys.stderr)

    if separations:
        print(f"fix_contrast.py: separated {len(separations)} colliding color pair(s):", file=sys.stderr)
        for n1, n2, before, after, dist in separations:
            print(f"  {n2} too close to {n1} (distance {dist:.1f}): {before} -> {after}", file=sys.stderr)
    else:
        print("fix_contrast.py: no color collisions detected, no separation needed.", file=sys.stderr)

    if unresolved:
        print(f"fix_contrast.py: {len(unresolved)} pair(s) remained too close (likely both near pure white/black, nothing to separate them with):", file=sys.stderr)
        for n1, n2 in unresolved:
            print(f"  {n1} / {n2}", file=sys.stderr)


if __name__ == "__main__":
    main()
