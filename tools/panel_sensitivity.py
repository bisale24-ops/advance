"""Does the "stands out for this act" order depend on which five acts form the comparison panel?

    python3 tools/panel_sensitivity.py docs/PANEL_SENSITIVITY.md      # needs a Qloo key

Three disjoint panels of unlike acts are tried on the same 15 briefs (5 headliners x 3 cities). Reported: how
often the first room is the same as under the default panel, how many of the top 3 rooms are shared, and how
often the first room differs from plain Qloo affinity order (no panel).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from advance import brief  # noqa: E402
from advance.qloo import Qloo  # noqa: E402

ARTISTS = ["Phoebe Bridgers", "Mitski", "Fontaines D.C.", "Chappell Roan", "Noah Kahan"]
CITIES = ["Chicago", "Denver", "Nashville"]
PANELS = {"default": brief.PANEL,
          "B": ("Drake", "Coldplay", "Morgan Wallen", "Bad Bunny", "Foo Fighters"),
          "C": ("Beyoncé", "Ed Sheeran", "Zach Bryan", "Travis Scott", "Dua Lipa")}


def rooms(q, head, city, panel):
    brief.PANEL = panel
    return [l.name for l in brief.which_room(q, head, city).lines]


def main(out):
    q = Qloo.from_env()
    first = {k: [] for k in PANELS}
    top3 = {k: [] for k in PANELS}
    plain = []
    for artist in ARTISTS:
        head = q.find(artist, "artist")
        for city in CITIES:
            for k, panel in PANELS.items():
                got = rooms(q, head, city, panel)
                first[k].append(got[0])
                top3[k].append(set(got[:3]))
            plain.append(rooms(q, head, city, ())[0])
    n = len(plain)
    lines = ["# Panel sensitivity", "", "15 briefs (5 headliners x 3 cities), three disjoint comparison panels.", "",
             "| panel | acts | same first room as default | top 3 shared with default (avg of 3) | first room differs from plain affinity |",
             "|---|---|---|---|---|"]
    for k, panel in PANELS.items():
        same = sum(a == b for a, b in zip(first[k], first["default"]))
        share = sum(len(a & b) for a, b in zip(top3[k], top3["default"])) / n
        diff = sum(a != b for a, b in zip(first[k], plain))
        lines.append(f"| {k} | {', '.join(panel)} | {same}/{n} | {share:.1f} | {diff}/{n} |")
    pathlib.Path(out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/PANEL_SENSITIVITY.md")
