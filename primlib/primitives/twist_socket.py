"""TWIST SOCKET -- the female half of a twist lock: a revolved taper socket."""

from primlib.core import Builder, Param, Primitive, grouped

TAPER = (
    Param("mouth_d", "30", "socket mouth diameter, at the lip's sharp inner edge"),
    Param("depth", "3.5", "socket depth, face to floor"),
    Param("taper_angle", "60", "undercut flank's angle to the face, deg"),
    Param("radius", "0.8", "round on the socket's floor corner and the lugs' root; the "
                           "mouth and the lug tips take radius - tol"),
)
FIT = (
    Param("tol", "0.3", "clearance: radial at the shaft, the lug tips and the openings, "
                        "axial at the floor; also how much smaller the convex rounds are"),
    Param("preload", "0.2", "the lugs' flanks are this much too high (along the axis) when "
                            "the faces touch: the pull when locked"),
)
LUGS = (
    Param("lugs", "3", "number of lugs and openings"),
    Param("lug_angle", "40", "each lug's arc, deg"),
    Param("twist", "60", "turn from entry to locked, deg, clockwise seen from the plug"),
    Param("open_clr", "3", "openings' angular clearance past the lugs each side, deg"),
    Param("lead", "1", "each lug's flank lowered this much at its leading end, so it "
                       "starts under the lip clear"),
    Param("lead_angle", "12", "arc over which the lead runs out to the full flank, deg"),
)
BODY = (
    Param("body_d", "50", "socket boss and plug flange diameter"),
    Param("body_t", "5", "socket boss thickness, below the face"),
    Param("flange_t", "2", "plug flange thickness, above the face"),
)
DETENT = (
    Param("detent_r", "1", "detent bump's sphere radius"),
    Param("detent_h", "0.4", "detent bump's height above the socket face"),
    Param("detent_pos", "=(mouth_d + body_d) / 4", "detent's distance from the axis"),
    Param("detent_angle", "=lug_angle / 2", "detent's angle (one per lug), deg"),
)
SPAN = (
    Param("overlap", "1", "how far tools reach past a face, for clean booleans"),
)

DERIVED = (
    ("m", "mouth_d / 2", "mouth radius"),
    ("floor_r", "m + depth / tan(taper_angle)", "floor radius, at the flank's foot"),
    ("r_small", "radius - tol", "the convex rounds: socket mouth and lug tips"),
    ("mouth_t", "r_small / tan(taper_angle / 2)", "tangent length of the mouth round"),
    ("root_t", "radius / tan(taper_angle / 2)", "tangent length of the lug root round"),
    ("shaft_r", "m - tol", "plug shaft radius"),
    ("lug_z", "tol - depth", "lugs' underside, tol off the floor"),
)
CHECKS = (
    ("r_small", "radius must be more than tol"),
    ("body_t - depth", "body_t leaves no floor under the socket"),
    ("body_d / 2 - floor_r - tol - 1", "body_d leaves under 1 of wall round the socket"),
    ("twist - open_clr - lug_angle", "a locked lug still overlaps its opening (twist too small)"),
    ("360 / lugs - twist - lug_angle - open_clr",
     "a locked lug overlaps the next opening (twist or lug_angle too big)"),
    ("lug_angle - lead_angle", "lead_angle must be less than lug_angle"),
    ("lead - preload", "lead must be more than preload, or the lugs can't start under the lips"),
    ("detent_pos - detent_r - m - mouth_t", "the detent is inside the mouth"),
    ("body_d / 2 - detent_pos - detent_r", "the detent is off the boss"),
)


def socket_points():
    """The socket void, (r, z) from the axis on the floor anticlockwise,
    the face at z = 0, reaching overlap above it."""
    out = "m + mouth_t + overlap"
    return [("0", "-depth"), ("floor_r", "-depth", "radius"), ("m", "0", "r_small"),
            (out, "0"), (out, "overlap"), ("0", "overlap")]


def lug_points(shift):
    """A lug's section, (r, z), its flank the socket's flank raised
    `shift` along the axis, its root under the plug flange at z = 0 and
    reaching overlap into it, its inner side inside the shaft."""
    tip = f"m + ({shift} - lug_z) / tan(taper_angle)"
    root = f"m + ({shift}) / tan(taper_angle)"
    out = f"{root} + root_t + overlap"
    return [("shaft_r - overlap", "lug_z"), (tip, "lug_z", "r_small"), (root, "0", "radius"),
            (out, "0"), (out, "overlap"), ("shaft_r - overlap", "overlap")]


def detent(b, suffix, r, z):
    """The detents, a sphere of radius `r` centred `z` on the face per lug."""
    at = ("detent_pos * cos(detent_angle)", "detent_pos * sin(detent_angle)", z)
    return b.polar(f"{suffix}s", b.sphere(suffix, at, r), "lugs", "360")


class TwistSocket(Primitive):
    """The female half of a twist lock: a round boss `body_d` across and
    `body_t` deep under its face (z = 0), centred on the z axis, with a
    revolved taper socket in it. The socket's mouth is `mouth_d` across,
    its flank undercut at `taper_angle` to the face down to the floor
    `depth` below it, the floor corner rounded to `radius` and the mouth to
    `radius` - `tol`: a rail's dovetail, revolved, without the guide. `lugs` openings, each the lugs' `lug_angle` plus `open_clr`
    each side, cut the lip back to the floor radius so a `twist_plug`'s
    lugs drop in, `twist` anticlockwise of where they lock (the plug turns
    clockwise to lock, seen from above). A detent bump per lug stands
    `detent_h` proud of the face, for the plug flange's dimples.

    **`mouth_d` is the mouth's sharp diameter (the lip's sharp inner edge,
    no rounds), not what calipers read, unlike `rail15` and `topeak_rail`,
    so check a print against it with care.**

    The plug's lugs are lowered `lead` at their leading ends, so they
    start under the lips clear, and are `preload` too high along the
    rest: turning them home pulls the plug's flange down onto the face
    and centres it on the taper.
    """

    title = "Twist socket"
    params, groups = grouped(("Taper", TAPER), ("Fit", FIT), ("Lugs", LUGS), ("Body", BODY),
                             ("Detent", DETENT), ("Span", SPAN))
    derived = DERIVED
    checks = CHECKS

    @classmethod
    def build(cls, doc, name, sheet, env):
        b = Builder(doc, name, sheet, env)
        body = b.cylinder("body", "z", ("0", "0"), "body_d / 2", ("-body_t", "0"))
        bumps = detent(b, "bump", "detent_r", "detent_h - detent_r")
        void = b.revolve("socket", socket_points(), ("0", "360"))
        opening = b.revolve("opening", [("m - 1", "-depth"), ("floor_r + tol", "-depth"),
                                        ("floor_r + tol", "overlap"), ("m - 1", "overlap")],
                            ("twist - open_clr", "twist + lug_angle + open_clr"))
        if void is None or opening is None:
            return None
        openings = b.polar("openings", opening, "lugs", "360")
        return b.finish(b.cut(None, b.fuse("boss", [body, bumps]), [void, openings]))
