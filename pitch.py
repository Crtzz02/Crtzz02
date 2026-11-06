"""Render the GitHub contribution graph as a football pitch SVG.

Usage: GITHUB_TOKEN=... python scripts/pitch.py Crtzz02 dist/pitch.svg
"""
import json
import math
import os
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


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={
            "Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
            "Content-Type": "application/json",
            "User-Agent": "pitch-generator",
        },
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


LEVEL_R = {
    "NONE": 0,
    "FIRST_QUARTILE": 3.2,
    "SECOND_QUARTILE": 4.6,
    "THIRD_QUARTILE": 5.8,
    "FOURTH_QUARTILE": 7.0,
}


def ball(cx, cy, r, delay):
    pent = []
    pr = r * 0.48
    for i in range(5):
        a = math.radians(-90 + i * 72)
        pent.append(f"{cx + pr * math.cos(a):.1f},{cy + pr * math.sin(a):.1f}")
    return (
        f'<g class="ball" style="animation-delay:{delay:.2f}s">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fff" stroke="#222" stroke-width="0.8"/>'
        f'<polygon points="{" ".join(pent)}" fill="#222"/>'
        f"</g>"
    )


def render(cal):
    weeks = cal["weeks"]
    cell, gap, pad = 14, 3, 22
    step = cell + gap
    w = len(weeks) * step + pad * 2
    h = 7 * step + pad * 2 + 22
    top = pad + 18
    pw, ph = len(weeks) * step, 7 * step

    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
        "<style>"
        ".ball{transform-box:fill-box;transform-origin:center;animation:pop 3.2s ease-in-out infinite}"
        "@keyframes pop{0%,100%{transform:scale(1)}50%{transform:scale(1.18)}}"
        "text{font-family:'Segoe UI',Arial,sans-serif}"
        "</style>",
        f'<rect width="{w}" height="{h}" rx="14" fill="#0b1f0b"/>',
        f'<text x="{pad}" y="{pad}" fill="#3ddc84" font-size="13" font-weight="700">'
        f'MATCHDAY · {cal["totalContributions"]} goals this season</text>',
    ]

    # mowed grass stripes
    for i in range(0, len(weeks), 4):
        color = "#1f7a1f" if (i // 4) % 2 == 0 else "#25892a"
        sw = min(4, len(weeks) - i) * step
        s.append(f'<rect x="{pad + i * step}" y="{top}" width="{sw}" height="{ph}" fill="{color}"/>')

    # pitch markings
    mx, my = pad + pw / 2, top + ph / 2
    line = 'fill="none" stroke="#fff" stroke-opacity="0.55" stroke-width="1.4"'
    s.append(f'<rect x="{pad}" y="{top}" width="{pw}" height="{ph}" {line}/>')
    s.append(f'<line x1="{mx}" y1="{top}" x2="{mx}" y2="{top + ph}" {line[line.index("stroke"):]}/>')
    s.append(f'<circle cx="{mx}" cy="{my}" r="{ph * 0.2}" {line}/>')
    s.append(f'<circle cx="{mx}" cy="{my}" r="2.5" fill="#fff" fill-opacity="0.7"/>')
    bw, bh = pw * 0.09, ph * 0.6
    sw_, sh_ = pw * 0.035, ph * 0.3
    for x, x2 in ((pad, pad), (pad + pw - bw, pad + pw - sw_)):
        s.append(f'<rect x="{x}" y="{my - bh / 2}" width="{bw}" height="{bh}" {line}/>')
        s.append(f'<rect x="{x2}" y="{my - sh_ / 2}" width="{sw_}" height="{sh_}" {line}/>')

    # contribution balls
    n = 0
    for wi, week in enumerate(weeks):
        for di, day in enumerate(week["contributionDays"]):
            r = LEVEL_R[day["contributionLevel"]]
            if r:
                cx = pad + wi * step + step / 2
                cy = top + di * step + step / 2
                s.append(ball(round(cx, 1), round(cy, 1), r, (n % 12) * 0.25))
                n += 1

    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(fetch()))
    print("wrote", OUT)
