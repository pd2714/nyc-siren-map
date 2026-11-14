"""Turn raw NYC Open Data downloads into data embedded in index.html.

Real: dispatch / on-scene / to-hospital / hospital-arrival times, ZIP code,
severity and call type of every FDNY EMS incident in one week.
Simulated: exact scene point inside the ZIP, where the ambulance starts,
the street path, which hospital it goes to, and whether the siren is on.
"""
import csv, json, math, random
from datetime import datetime

random.seed(7)
LON0, LAT0 = -73.95, 40.70
KX = math.cos(math.radians(LAT0)) * 111320.0
KY = 110540.0
Q = 10.0  # 1 unit = 10 m
WEEK0 = datetime(2026, 9, 21)


def proj(lon, lat):
    return ((lon - LON0) * KX, (lat - LAT0) * KY)


# ---------- geometry ----------
def dp(pts, tol):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]; bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy) or 1e-9
        best, bi = -1, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            d = abs(dy * (px - ax) - dx * (py - ay)) / L
            if d > best:
                best, bi = d, i
        if best > tol:
            keep[bi] = True
            stack += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]


def dp_ring(r, tol):
    # closed ring: split at the vertex farthest from the first so DP has a real baseline
    x0, y0 = r[0]
    k = max(range(len(r)), key=lambda i: (r[i][0] - x0) ** 2 + (r[i][1] - y0) ** 2)
    if k == 0:
        return r
    return dp(r[:k + 1], tol)[:-1] + dp(r[k:], tol)


def ring_area(r):
    return 0.5 * sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))


def pip(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]; xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


gj = json.load(open("raw/modzcta.geojson"))
zips = []          # list of dicts
zip_of = {}        # any 5-digit zip -> index
for f in gj["features"]:
    p = f["properties"]
    if p["modzcta"] == "99999":
        continue
    polys = []  # list of polygons, each list of rings in metres
    for poly in f["geometry"]["coordinates"]:
        rings = [[proj(lon, lat) for lon, lat in r] for r in poly]
        polys.append(rings)
    outer_full = [poly[0] for poly in polys]
    area = sum(abs(ring_area(r)) for r in outer_full)
    simp = []
    for poly in polys:
        for k, r in enumerate(poly):
            s = dp_ring(r, 18.0)
            if len(s) >= 4 and abs(ring_area(s)) > 4000:
                simp.append((k > 0, s))
    xs = [x for r in outer_full for x, _ in r]; ys = [y for r in outer_full for _, y in r]
    idx = len(zips)
    zips.append(dict(code=p["modzcta"], label=p["label"], pop=int(float(p.get("pop_est") or 0)),
                     area=area, polys=polys, simp=simp, bbox=(min(xs), min(ys), max(xs), max(ys))))
    for z in [p["modzcta"]] + [s.strip() for s in (p.get("zcta") or "").split(",")] + \
             [s.strip() for s in (p.get("label") or "").split(",")]:
        if z:
            zip_of.setdefault(z, idx)


def in_zip(zi, x, y):
    for rings in zips[zi]["polys"]:
        if pip(x, y, rings[0]) and not any(pip(x, y, h) for h in rings[1:]):
            return True
    return False


def on_land(x, y):
    for zi, z in enumerate(zips):
        b = z["bbox"]
        if b[0] <= x <= b[2] and b[1] <= y <= b[3] and in_zip(zi, x, y):
            return True
    return False


def rand_in_zip(zi):
    b = zips[zi]["bbox"]
    for _ in range(400):
        x = random.uniform(b[0], b[2]); y = random.uniform(b[1], b[3])
        if in_zip(zi, x, y):
            return x, y
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


# ---------- hospitals ----------
SKIP = ["CALVARY", "CANCER", "KOCH", "SPECIAL SURGERY", "ORTHOPEDIC", "EYE AND EAR", "BEHAVIORAL",
        "ROCKEFELLER", "CARTER SPECIALTY", "AMBULATORY", "KINGSBROOK"]
hosp = []
for r in csv.DictReader(open("raw/hospitals.csv")):
    name = r["facname"]
    if any(s in name for s in SKIP) or not r["latitude"]:
        continue
    x, y = proj(float(r["longitude"]), float(r["latitude"]))
    if any(math.hypot(x - h[1], y - h[2]) < 250 for h in hosp):
        continue
    hosp.append((name.title(), x, y))


# ---------- incidents -> movement legs ----------
def ts(s):
    if not s:
        return None
    return (datetime.fromisoformat(s[:19]) - WEEK0).total_seconds()


GRID_ROT = {"MANHATTAN": math.radians(29)}  # Manhattan street grid is ~29 deg off north
call_types = []
ct_idx = {}
legs = []          # [t0, dur, x0,y0, xc,yc, x1,y1, meta]
zip_inc = [0] * len(zips)


def l_path(x0, y0, x1, y1, rot):
    c, s = math.cos(rot), math.sin(rot)
    # coordinates in grid frame
    u0, v0 = x0 * c - y0 * s, x0 * s + y0 * c
    u1, v1 = x1 * c - y1 * s, x1 * s + y1 * c
    uc, vc = (u1, v0) if random.random() < 0.5 else (u0, v1)
    # back to map frame
    return uc * c + vc * s, -uc * s + vc * c


for r in csv.DictReader(open("raw/ems_week.csv")):
    zi = zip_of.get(r["zipcode"])
    if zi is None:
        continue
    ct = r["final_call_type"]
    if ct in ("STNDBY", "SPEVNT"):
        continue
    sev = int(r["final_severity_level_code"] or 8)
    if ct not in ct_idx:
        ct_idx[ct] = len(call_types); call_types.append(ct)
    zip_inc[zi] += 1
    sx, sy = rand_in_zip(zi)
    rot = GRID_ROT.get(r["borough"], 0.0)
    zmeta = (zi << 14) | (ct_idx[ct] << 6) | (sev << 2)

    # leg 1: unit activation -> on scene (lights & sirens for severity 1-4)
    ta, tsn = ts(r["first_activation_datetime"]), ts(r["first_on_scene_datetime"])
    if ta is not None and tsn is not None and 45 <= tsn - ta <= 2400:
        dur = tsn - ta
        dist = min(4500.0, max(350.0, dur * random.uniform(4.0, 6.5)))
        for k in range(12):
            ang = random.uniform(0, 2 * math.pi)
            d = dist * (1 - k / 14)
            ox, oy = sx + d * math.cos(ang), sy + d * math.sin(ang)
            if on_land(ox, oy):
                break
        cx, cy = l_path(ox, oy, sx, sy, rot)
        siren = 1 if sev <= 4 else 0
        legs.append([ta, dur, ox, oy, cx, cy, sx, sy, zmeta | siren])

    # leg 2: leave scene -> arrive hospital (sirens for severity 1-2)
    th, tha = ts(r["first_to_hosp_datetime"]), ts(r["first_hosp_arrival_datetime"])
    if th is not None and tha is not None and 60 <= tha - th <= 3600:
        # Patients often go to a trauma / stroke / cardiac centre rather than the nearest ER.
        # Use the real transport time: assume 18-30 km/h along the street grid and pick the
        # hospital whose grid distance best matches (capped at 12 km).
        target = min(12000.0, (tha - th) * random.uniform(5.0, 8.3))
        c_, s_ = math.cos(rot), math.sin(rot)

        def grid_len(h):
            dx, dy = h[1] - sx, h[2] - sy
            return abs(dx * c_ - dy * s_) + abs(dx * s_ + dy * c_)
        h = min(hosp, key=lambda h: abs(grid_len(h) - target))
        cx, cy = l_path(sx, sy, h[1], h[2], rot)
        siren = 1 if sev <= 2 else 0
        legs.append([th, tha - th, sx, sy, cx, cy, h[1], h[2], zmeta | 2 | siren])

legs.sort(key=lambda l: l[0])

# pack legs as flat ints (positions in 10 m units, times in s, t0 delta-coded)
flat, prev = [], 0
for l in legs:
    t0 = int(round(l[0]))
    flat += [t0 - prev, int(round(l[1]))] + [int(round(v / Q)) for v in l[2:8]] + [l[8]]
    prev = t0

geo = []
for z in zips:
    rings = []
    for hole, r in z["simp"]:
        pts, px, py = [], 0, 0
        for x, y in r:
            ix, iy = int(round(x / Q)), int(round(y / Q))
            pts += [ix - px, iy - py]; px, py = ix, iy
        rings.append([1 if hole else 0, pts])
    geo.append(dict(c=z["code"], l=z["label"], p=z["pop"], a=round(z["area"] / 1e6, 3), r=rings))

data = dict(
    week="2026-09-21", proj=[LON0, LAT0, KX, KY, Q],
    zips=geo, zipInc=zip_inc,
    hosp=[[n, int(round(x / Q)), int(round(y / Q))] for n, x, y in hosp],
    ct=call_types, legs=flat,
)
js = json.dumps(data, separators=(",", ":"))
tpl = open("template.html").read()
page = tpl.replace("/*__DATA__*/null", js)
open("index.html", "w").write(page)

# standalone site (GitHub Pages): full document, no Google Fonts (blocked in mainland China)
import os, re
standalone = re.sub(r'<link rel="(?:preconnect|stylesheet)" href="https://fonts\.(?:googleapis|gstatic)\.com[^>]*>\n', "", page)
cut = standalone.index("</style>") + len("</style>")
DESC = "回放 2026 年 9 月一周的 FDNY 救护车派车记录，在地图上选一个点，听附近经过的救护车警笛声。"
os.makedirs("docs", exist_ok=True)
open("docs/index.html", "w").write(
    '<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    f'<meta name="description" content="{DESC}">\n'
    '<meta property="og:title" content="纽约警笛听诊器">\n'
    f'<meta property="og:description" content="{DESC}">\n'
    '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}</style>\n'
    + standalone[:cut] + "\n</head>\n<body>\n" + standalone[cut:] + "\n</body>\n</html>\n")
n_siren = sum(1 for l in legs if l[8] & 1)
print(f"zips {len(zips)}  hospitals {len(hosp)}  legs {len(legs)}  siren legs {n_siren}  data {len(js)/1e6:.2f} MB")
