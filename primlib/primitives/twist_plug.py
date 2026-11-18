"""TWIST PLUG -- the male half of a twist lock: a flange with taper lugs."""

from primlib.core import Builder, Primitive
from primlib.primitives.twist_socket import CHECKS, DERIVED, TwistSocket, detent, lug_points

LEAD_SECTIONS = 4  # lofted sections over each lug's lead, plus the start


class TwistPlug(Primitive):
    """The male half of a twist lock, built locked in a `twist_socket`
    with the same parameters at the same origin: a flange `body_d` across
    and `flange_t` thick on the socket's face (z = 0 to `flange_t`), a
    shaft `tol` inside the mouth down to `tol` off the floor, and `lugs`
    lugs, each `lug_angle` of arc from 0 deg anticlockwise (then every
    360 / `lugs`), whose upper flank is the socket's flank raised
    `preload`, rounded `radius` at the root and `radius` - `tol` at the
    tip. Each lug's leading end (at 0 deg: the plug turns clockwise to
    lock) is lowered `lead`, running out over `lead_angle` (a smooth loft
    through a few sections; its angles are fixed when the plug is built).
    The flange's underside has a dimple over each detent bump, `tol` over.

    **`mouth_d` is the mouth's sharp diameter (the lip's sharp inner edge,
    no rounds), not what calipers read, unlike `rail15` and `topeak_rail`,
    so check a print against it with care.**

    To fit it, turn the plug `twist` anticlockwise of this, drop it in
    and turn it clockwise `twist`.
    """

    title = "Twist plug"
    params, groups = TwistSocket.params, TwistSocket.groups
    derived = DERIVED
    checks = CHECKS

    @classmethod
    def build(cls, doc, name, sheet, env):
        b = Builder(doc, name, sheet, env)
        flange = b.cylinder("flange", "z", ("0", "0"), "body_d / 2", ("0", "flange_t"))
        shaft = b.cylinder("shaft", "z", ("0", "0"), "shaft_r", ("lug_z", "flange_t"))
        n = LEAD_SECTIONS
        lead = b.loft_about("lead", [
            (lug_points(f"preload - lead * {n - k} / {n}"), f"lead_angle * {k} / {n}")
            for k in range(n + 1)])
        rest = b.revolve("lug_rest", lug_points("preload"), ("lead_angle", "lug_angle"))
        if lead is None or rest is None:
            return None
        lugs = b.polar("lugs", b.fuse("lug", [lead, rest]), "lugs", "360")
        dimples = detent(b, "dimple", "detent_r + tol", "detent_h - detent_r")
        return b.finish(b.cut(None, b.fuse("body", [flange, shaft, lugs]), [dimples]))
