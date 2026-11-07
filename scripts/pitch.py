"""Render the GitHub contribution calendar as an animated football pitch SVG.

Usage: GITHUB_TOKEN=... python scripts/pitch.py Crtzz02 dist/pitch.svg

With GITHUB_TOKEN set, data comes from the GraphQL API. Without it, the public
contributions page is parsed instead (handy for local previews).
"""
import datetime as dt
import json
import math
import os
import re
import sys
import urllib.request

USER = sys.argv[1] if len(sys.argv) > 1 else "Crtzz02"
OUT = sys.argv[2] if len(sys.argv) > 2 else "dist/pitch.svg"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount contributionLevel date } }
      }
    }
  }
}
"""

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
RADIUS = [0, 3.2, 4.6, 5.8, 7.0]

PANEL, EDGE = "#07150b", "#1f3a24"
G2, G3, TXT, MUTED, GOLD, RED = "#1f7a1f", "#3ddc84", "#e6ffe6", "#8fbf9a", "#f5c518", "#ff4d4d"
MONTHS = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()


def fetch_graphql(token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "pitch-generator",
        },
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [
        [{"date": d["date"], "count": d["contributionCount"], "level": LEVELS[d["contributionLevel"]]}
         for d in w["contributionDays"]]
        for w in cal["weeks"]
    ]
    return {"total": cal["totalContributions"], "weeks": weeks}


def fetch_public():
    req = urllib.request.Request(
        f"https://github.com/users/{USER}/contributions", headers={"User-Agent": "pitch-generator"}
    )
    with urllib.request.urlopen(req) as r:
        page = r.read().decode("utf-8")
    counts = {}
    for m in re.finditer(r'<tool-tip\b[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
        n = re.match(r"\s*(\d+)", m.group(2))
        counts[m.group(1)] = int(n.group(1)) if n else 0
    weeks = {}
    for m in re.finditer(r"<td\b[^>]*\bdata-date=[^>]*>", page):
        tag = m.group(0)
        attr = lambda a: re.search(rf'\b{a}="([^"]*)"', tag).group(1)
        cid = attr("id")
        weekday, week = map(int, cid.rsplit("-", 2)[1:])
        weeks.setdefault(week, []).append(
            (weekday, {"date": attr("data-date"), "count": counts.get(cid, 0), "level": int(attr("data-level"))})
        )
    weeks = [[d for _, d in sorted(weeks[k], key=lambda t: t[0])] for k in sorted(weeks)]
    return {"total": sum(d["count"] for w in weeks for d in w), "weeks": weeks}


def season_stats(weeks):
    today = dt.date.today().isoformat()
    days = sorted((d for w in weeks for d in w if d["date"] <= today), key=lambda d: d["date"])
    best = max(days, key=lambda d: d["count"], default=None)
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] else 0
        longest = max(longest, run)
    tail = days[:-1] if days and not days[-1]["count"] else days  # today isn't over yet
    current = 0
    for d in reversed(tail):
        if not d["count"]:
            break
        current += 1
    return {
        "active": sum(1 for d in days if d["count"]),
        "best": best if best and best["count"] else None,
        "longest": longest,
        "current": current,
    }


def ball(cx, cy, r, delay, golden=False):
    pent = []
    pr = r * 0.48
    for i in range(5):
        a = math.radians(-90 + i * 72)
        pent.append(f"{cx + pr * math.cos(a):.1f},{cy + pr * math.sin(a):.1f}")
    halo = ""
    if golden:
        halo = (
            f'<circle cx="{cx}" cy="{cy}" r="{r + 3}" fill="{GOLD}" fill-opacity=".35" stroke="{GOLD}" stroke-width="1.5">'
            f'<animate attributeName="r" values="{r + 2};{r + 6};{r + 2}" dur="1.8s" repeatCount="indefinite"/></circle>'
        )
    return (
        f'{halo}<g class="ball" style="animation-delay:{delay:.2f}s">'
        f'<circle cx="{cx}" cy="{cy + 1.2}" r="{r}" fill="#000" fill-opacity=".3"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{"#ffe27a" if golden else "#fff"}" stroke="#222" stroke-width="0.8"/>'
        f'<polygon points="{" ".join(pent)}" fill="#222"/>'
        f"</g>"
    )


def render(cal):
    weeks = cal["weeks"]
    stats = season_stats(weeks)
    n = len(weeks)
    step, pad = 17, 36
    pw, ph = n * step, 7 * step
    w = pw + pad * 2
    top = 80
    sy = top + ph + 20
    h = sy + 56 + 18

    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
        "<style>"
        ".ball{transform-box:fill-box;transform-origin:center;animation:pop 3.2s ease-in-out infinite}"
        "@keyframes pop{0%,100%{transform:scale(1)}50%{transform:scale(1.18)}}"
        "text{font-family:'Segoe UI',Ubuntu,'Helvetica Neue',Arial,sans-serif}"
        ".mono{font-family:Consolas,'DejaVu Sans Mono',Menlo,monospace}"
        "</style>",
        '<defs><pattern id="net" width="4" height="4" patternUnits="userSpaceOnUse">'
        '<path d="M0,0 L4,4 M4,0 L0,4" stroke="#fff" stroke-opacity=".45" stroke-width=".7"/></pattern></defs>',
        f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="14" fill="{PANEL}" stroke="{EDGE}"/>',
        f'<text x="{pad}" y="33" fill="{G3}" font-size="13" font-weight="800" letter-spacing="4">THE PITCH</text>',
        f'<text x="{pad}" y="50" fill="{MUTED}" font-size="11" letter-spacing="1.5">CONTRIBUTION SEASON  ·  LAST 12 MONTHS</text>',
    ]

    # TV-style scorebug
    bx = w - pad - 208
    s.append(
        f'<circle cx="{bx - 14}" cy="31" r="5" fill="{RED}"><animate attributeName="opacity" values="1;.2;1" dur="1.4s" repeatCount="indefinite"/></circle>'
        f'<clipPath id="bug"><rect x="{bx}" y="16" width="208" height="30" rx="6"/></clipPath><g clip-path="url(#bug)">'
        f'<rect x="{bx}" y="16" width="62" height="30" fill="{G2}"/><rect x="{bx + 62}" y="16" width="84" height="30" fill="#030b06"/>'
        f'<rect x="{bx + 146}" y="16" width="62" height="30" fill="#4a1414"/></g>'
        f'<text x="{bx + 31}" y="36" text-anchor="middle" fill="#fff" font-size="14" font-weight="900" letter-spacing="1">OMK</text>'
        f'<text x="{bx + 104}" y="37" text-anchor="middle" fill="{GOLD}" font-size="16" font-weight="800" class="mono">{cal["total"]} – 0</text>'
        f'<text x="{bx + 177}" y="36" text-anchor="middle" fill="#ffd6d6" font-size="14" font-weight="900" letter-spacing="1">BUGS</text>'
    )

    # month labels
    last = -9
    prev = None
    for wi, week in enumerate(weeks):
        m = int(week[0]["date"][5:7])
        if m != prev and wi - last >= 3 and wi < n - 1:
            s.append(f'<text x="{pad + wi * step}" y="{top - 9}" fill="{MUTED}" font-size="10" font-weight="700" letter-spacing="1">{MONTHS[m - 1]}</text>')
            last = wi
        prev = m

    # mowed grass stripes
    for i in range(0, n, 4):
        color = "#1a6e22" if (i // 4) % 2 == 0 else "#1f7d28"
        sw = min(4, n - i) * step
        s.append(f'<rect x="{pad + i * step}" y="{top}" width="{sw}" height="{ph}" fill="{color}"/>')

    # pitch markings
    mx, my = pad + pw / 2, top + ph / 2
    line = 'fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="1.4"'
    s.append(f'<rect x="{pad}" y="{top}" width="{pw}" height="{ph}" {line}/>')
    s.append(f'<line x1="{mx}" y1="{top}" x2="{mx}" y2="{top + ph}" {line}/>')
    s.append(f'<circle cx="{mx}" cy="{my}" r="{ph * 0.2:.1f}" {line}/>')
    s.append(f'<circle cx="{mx}" cy="{my}" r="2.5" fill="#fff" fill-opacity=".7"/>')
    bw, bh = pw * 0.09, ph * 0.6
    sw_, sh_ = pw * 0.035, ph * 0.3
    spot, ar = pw * 0.065, ph * 0.2
    dx = bw - spot
    dy = math.sqrt(max(ar * ar - dx * dx, 0))
    for side in (0, 1):
        x = pad if side == 0 else pad + pw - bw
        x2 = pad if side == 0 else pad + pw - sw_
        px = pad + spot if side == 0 else pad + pw - spot
        ex = pad + bw if side == 0 else pad + pw - bw
        s.append(f'<rect x="{x:.1f}" y="{my - bh / 2:.1f}" width="{bw:.1f}" height="{bh:.1f}" {line}/>')
        s.append(f'<rect x="{x2:.1f}" y="{my - sh_ / 2:.1f}" width="{sw_:.1f}" height="{sh_:.1f}" {line}/>')
        s.append(f'<circle cx="{px:.1f}" cy="{my}" r="2" fill="#fff" fill-opacity=".7"/>')
        if dy:
            s.append(f'<path d="M{ex:.1f},{my - dy:.1f} A{ar:.1f},{ar:.1f} 0 0 {1 - side} {ex:.1f},{my + dy:.1f}" {line}/>')
    c = 6
    x0, y0, x1, y1 = pad, top, pad + pw, top + ph
    s.append(
        f'<path d="M{x0},{y0 + c} A{c},{c} 0 0 0 {x0 + c},{y0} M{x1 - c},{y0} A{c},{c} 0 0 0 {x1},{y0 + c} '
        f'M{x1},{y1 - c} A{c},{c} 0 0 0 {x1 - c},{y1} M{x0 + c},{y1} A{c},{c} 0 0 0 {x0},{y1 - c}" {line}/>'
    )
    gh = ph * 0.22
    for gx in (pad - 12, pad + pw):
        s.append(f'<rect x="{gx}" y="{my - gh / 2:.1f}" width="12" height="{gh:.1f}" fill="url(#net)" stroke="#fff" stroke-opacity=".8" stroke-width="1.5"/>')

    # contribution balls
    best_date = stats["best"]["date"] if stats["best"] else None
    k = 0
    for wi, week in enumerate(weeks):
        for day in week:
            r = RADIUS[day["level"]]
            if r:
                di = dt.date.fromisoformat(day["date"]).isoweekday() % 7  # Sunday = 0
                cx = round(pad + wi * step + step / 2, 1)
                cy = round(top + di * step + step / 2, 1)
                s.append(ball(cx, cy, r, (k % 12) * 0.25, golden=day["date"] == best_date))
                k += 1

    # season stats strip
    best = stats["best"]
    best_txt = f'{best["count"]} · {MONTHS[int(best["date"][5:7]) - 1]} {int(best["date"][8:])}' if best else "—"
    boxes = [
        (str(cal["total"]), "GOALS SCORED"),
        (str(stats["active"]), "MATCHDAYS PLAYED"),
        (f'{stats["longest"]}d', "LONGEST UNBEATEN RUN"),
        (f'{stats["current"]}d', "CURRENT FORM"),
        (best_txt, "GOLDEN BALL · BEST DAY"),
    ]
    gap = 10
    bwid = (pw - gap * (len(boxes) - 1)) / len(boxes)
    for i, (val, lab) in enumerate(boxes):
        x = pad + i * (bwid + gap)
        accent = GOLD if i == len(boxes) - 1 else G3
        s.append(
            f'<rect x="{x:.1f}" y="{sy}" width="{bwid:.1f}" height="56" rx="10" fill="#0b1f0b" stroke="{EDGE}"/>'
            f'<rect x="{x:.1f}" y="{sy + 12}" width="3" height="32" rx="1.5" fill="{accent}"/>'
            f'<text x="{x + 16:.1f}" y="{sy + 29}" fill="{accent}" font-size="20" font-weight="800" class="mono">{val}</text>'
            f'<text x="{x + 16:.1f}" y="{sy + 46}" fill="{MUTED}" font-size="9.5" font-weight="700" letter-spacing="1.2">{lab}</text>'
        )

    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN")
    cal = fetch_graphql(token) if token else fetch_public()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(cal))
    print("wrote", OUT)
