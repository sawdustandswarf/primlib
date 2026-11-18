r"""
================================================================================
PIN_RETAINED -- retained pin: a shaft with a splayed flare at both ends
================================================================================

A retained pin is a solid of revolution: a straight cylindrical shaft of
diameter `diam` capped at each end by a conical flare that opens out to
`diam_end`. The flare traps a mating sleeve (or collar) axially once the
sleeve is snapped over the shaft -- hence "retained".

        |        /-- rd -->\         |
        |       /            \        |
        |      /              \       |
        |     |                |      |
   h    |     | pd             |      |
        |     |                |      |
        |      \              /       |
        |       \            /        |
        |        \          /         |
     Pin Diameter = pd (shaft)
     Retain Diameter = rd (flare, at each end face)
     Flank Angle = p_ang (degrees, to the end face)

Coordinate convention
---------------------
  Z runs along the pin axis. The pin spans exactly z = 0 .. height; the
  lowest boundary sits at z = 0 and the highest at z = height. Radii are
  measured from the axis (r = 0).

Parameters
----------
  height     h     overall pin height, end face to end face (mm)
  diam       pd    straight shaft diameter (mm)
  diam_end   rd    retain (flare) diameter at each end face (mm)
  angle      p_ang flare flank angle to the end face (degrees, default 45)
  clearance  c     optional envelope growth, mm added normal to every face

Derived geometry
----------------
  cone_height  (rd/2 - pd/2) * tan(p_ang)   visible frustum height per end
  shaft_len    height - 2 * cone_height     straight shaft between the flares
  cone_apex    (rd/2) * tan(p_ang)          end face -> complete-cone apex

Valid range / constraints
-------------------------
  * 0 < angle < 90
  * diam_end > diam            (the cone height must be positive)
  * height > 2 * cone_height   (the shaft length must be positive)
  Outside that range pin_retained() reports an error and builds nothing.

Clearance envelope
------------------
`clearance` (c, mm) pushes every face out along its own outward normal;
where two offset faces meet (the end rims) they are extended to a sharp
corner. The envelope is again a retained pin of the same flank angle, with

  h'  = height + 2c
  pd' = pd + 2c
  rd' = rd + 2c * cot(p_ang / 2)

so the single routine builds both the nominal pin and the overdimensioned
envelope the pin must clear in a bore.

Revolve profile (sketch in the XZ half-plane, y = 0)
-----------------------------------------------------
profile_points() computes the closed polyline below; revolved 360 degrees
about the z axis it sweeps exactly the same solid. The sketch lies in the
XZ half-plane (y = 0): x is the distance from the axis, z the height.
Each vertex as an (x, y, z) point:

                   P5 (0, 0, h') ----------------- P4 (rd'/2, 0, h')
                     |                                /
                     |                               /  p_ang flank
                     |                             P3 (pd'/2, 0, h'-c')
                     |                              |
                     |                              |  shaft (pd')
                     |                            P2 (pd'/2, 0, c')
                     |                              /
                     |                             /  p_ang flank
      axis           P0 (0, 0, 0) ---------------- P1 (rd'/2, 0, 0)
      (x = 0)         \____________________________/
                           bottom end face (rd')

  P0 = (0,          0, 0    )   axis, bottom
  P1 = (rd'/2,      0, 0    )   bottom end face -> flare rim
  P2 = (pd'/2,      0, c'   )   flare flank -> shaft
  P3 = (pd'/2,      0, h'-c')   shaft -> top flare
  P4 = (rd'/2,      0, h'   )   flare flank -> top rim
  P5 = (0,          0, h'   )   top end face -> axis

with the clearance-grown values (equal to the plain ones when c = 0):

  h'  = h + 2c
  pd' = pd + 2c
  rd' = rd + 2c / tan(p_ang / 2)
  c'  = (rd'/2 - pd'/2) * tan(p_ang)

The polyline closes along the axis (P5 -> P0), so the revolved solid is
closed: the profile touches the axis and nothing else does.

API
----
  pin_retained(doc, name, height, diam, diam_end,
               angle=45.0, clearance=0.0)
      Build the pin into `doc`. Returns the Part::MultiFuse result, or
      None (with a console error) if the parameters are outside the valid
      range above.

  derived_geometry(height, diam, diam_end, angle=45.0)
      Return the derived dimensions as a dict: cone_height, shaft_len,
      cone_apex.

  profile_points(height, diam, diam_end, angle=45.0, clearance=0.0)
      The revolve profile P0..P5 above as six App.Vector (x, 0, z),
      ready for the sketch; None (with a console error) on invalid
      parameters.

  profile_sketch(doc, name, height, diam, diam_end,
                 angle=45.0, clearance=0.0)
      Build the profile as a Sketcher sketch in the XZ half-plane: the
      six profile segments, each tied to the next by a coincidence
      constraint so the wire stays closed when dragged in the GUI. The
      closing segment P5 -> P0 lies on the axis, so the sketch needs no
      separate axis line. Local (u, v) of the sketch plane maps to
      global (u, 0, v). Returns the sketch, or None on invalid
      parameters.

  pin_retained_revolved(doc, name, height, diam, diam_end,
                        angle=45.0, clearance=0.0)
      pin_retained() as a solid of revolution: profile_sketch() named
      `{name}_sketch` revolves 360 degrees about the z axis through a
      Part::Revolution. Same parameters, identical solid, same
      None-on-invalid behaviour; the sketch is hidden as construction.

Run this file directly (freecadcmd pin_retained.py) to build an inspection
document: a solid block spanning x = +/- 3 * rd and z = +/- 2 * h, but only
on the +y side (y = 0 .. 3 * rd), hollowed by the clearance envelope, with
the complete nominal pin in the cavity. The block's y = 0 face reads as a
section of the clearance pin around the main pin. The envelope is built
from z = 0 like any pin, so it is dropped by c before the cut to centre it
on the nominal pin.
================================================================================
"""

import math
import os
import sys

import FreeCAD as App
import Part
import Sketcher


def _hide(obj):
    """Hide a construction object when a GUI is present (headless has no ViewObject)."""
    view = getattr(obj, "ViewObject", None)
    if view is not None:
        view.Visibility = False


def derived_geometry(height, diam, diam_end, angle=45.0):
    """Derived pin dimensions: cone_height, shaft_len, cone_apex (all mm)."""
    shaft_rad = float(diam) / 2.0
    flare_rad = float(diam_end) / 2.0
    tan_a = math.tan(math.radians(angle))
    cone_height = (flare_rad - shaft_rad) * tan_a
    return {
        "cone_height": cone_height,                              # c
        "shaft_len": float(height) - (2.0 * cone_height),        # ls
        "cone_apex": flare_rad * tan_a,                          # ca
    }


def _resolve(height, diam, diam_end, angle, clearance):
    """Clearance-grown pin dimensions after validation.

    Returns (h, shaft_rad, flare_rad, cone_height, shaft_height), or None
    after reporting which constraint failed (see the module docstring).
    Shared by pin_retained(), profile_points() and pin_retained_revolved()
    so every construction route agrees on the same solid.
    """
    h = float(height)
    ang = float(angle)
    clr = float(clearance)

    if not 0.0 < ang < 90.0:
        App.Console.PrintError(
            "Error: `angle` must lie strictly between 0 and 90 degrees.\n")
        return None

    # Clearance envelope: grow every dimension, then build as a plain pin.
    half_a = math.radians(ang / 2.0)
    diam = float(diam) + 2.0 * clr
    diam_end = float(diam_end) + (2.0 * clr / math.tan(half_a))
    h = h + 2.0 * clr

    inner_rad = diam / 2.0
    outer_rad = diam_end / 2.0

    cone_height = (outer_rad - inner_rad) * math.tan(math.radians(ang))
    if cone_height <= 0:
        App.Console.PrintError("Error: diam_end must be larger than diam.\n")
        return None

    shaft_height = h - (2.0 * cone_height)
    if shaft_height <= 0:
        App.Console.PrintError(
            "Error: the requested `height` is too small to accommodate "
            "the end flares.\n")
        return None

    return h, inner_rad, outer_rad, cone_height, shaft_height


def pin_retained(doc, name, height, diam, diam_end,
                 angle=45.0, clearance=0.0):
    """
    Retained pin: a shaft `diam` with an `angle`-degree flare `diam_end` at
    each end, `height` tall (z = 0 .. height).

    `angle` is the flare flank angle (p_ang, degrees). `clearance` (mm,
    optional) pushes every face out along its own outward normal, giving
    the overdimensioned envelope the pin must clear in a bore.

    The lowest boundary sits at z = 0 and the highest at z = height. Built
    from a bottom cone, a shaft cylinder and a top cone, unioned together
    (the small overlaps are irrelevant in the union).

    Returns the Part::MultiFuse result, or None (with a console error) if
    the parameters are outside the valid range documented above.
    """
    resolved = _resolve(height, diam, diam_end, angle, clearance)
    if resolved is None:
        return None
    h, inner_rad, outer_rad, cone_height, shaft_height = resolved

    bottom_cone = doc.addObject("Part::Cone", f"{name}_bottom")
    bottom_cone.Radius1 = outer_rad
    bottom_cone.Radius2 = inner_rad
    bottom_cone.Height = cone_height
    bottom_cone.Placement.Base = App.Vector(0, 0, 0)

    shaft = doc.addObject("Part::Cylinder", f"{name}_shaft")
    shaft.Radius = inner_rad
    shaft.Height = shaft_height
    shaft.Placement.Base = App.Vector(0, 0, cone_height)

    top_cone = doc.addObject("Part::Cone", f"{name}_top")
    top_cone.Radius1 = inner_rad
    top_cone.Radius2 = outer_rad
    top_cone.Height = cone_height
    top_cone.Placement.Base = App.Vector(0, 0, cone_height + shaft_height)

    fusion = doc.addObject("Part::MultiFuse", name)
    fusion.Shapes = [shaft, bottom_cone, top_cone]

    _hide(shaft)
    _hide(bottom_cone)
    _hide(top_cone)
    return fusion


def profile_points(height, diam, diam_end, angle=45.0, clearance=0.0):
    """The revolve profile P0..P5 as six App.Vector (x, 0, z).

    Vertices follow the module docstring: axis -> bottom flare rim ->
    shaft bottom -> shaft top -> top flare rim -> axis. Returns None
    (with a console error) on invalid parameters, like pin_retained().
    """
    resolved = _resolve(height, diam, diam_end, angle, clearance)
    if resolved is None:
        return None
    h, shaft_rad, flare_rad, cone_height, shaft_height = resolved
    return [
        App.Vector(0.0, 0.0, 0.0),                    # P0  axis, bottom
        App.Vector(flare_rad, 0.0, 0.0),              # P1  bottom flare rim
        App.Vector(shaft_rad, 0.0, cone_height),      # P2  shaft, bottom
        App.Vector(shaft_rad, 0.0, h - cone_height),  # P3  shaft, top
        App.Vector(flare_rad, 0.0, h),                # P4  top flare rim
        App.Vector(0.0, 0.0, h),                      # P5  axis, top
    ]


def profile_sketch(doc, name, height, diam, diam_end,
                   angle=45.0, clearance=0.0):
    """The revolve profile as a Sketcher sketch in the XZ half-plane (y = 0).

    GeoIds 0..5 are the profile segments P0->P1->...->P5->P0, each tied
    to the next by a coincidence constraint so the wire stays closed when
    dragged. The closing segment P5->P0 lies on the axis, so no separate
    construction line is needed (a duplicate collinear edge would leave
    the solver over-determined). The sketch's local (u, v) maps to global
    (u, 0, v): u is the distance from the axis, v the height. Returns the
    sketch, or None when the parameters are invalid.
    """
    pts = profile_points(height, diam, diam_end, angle=angle,
                         clearance=clearance)
    if pts is None:
        return None

    sketch = doc.addObject("Sketcher::SketchObject", name)
    # Local (u, v) -> global (u, 0, v): rotate the local XY plane onto XZ.
    sketch.Placement = App.Placement(
        App.Vector(0.0, 0.0, 0.0), App.Rotation(App.Vector(1, 0, 0), 90.0))

    # Profile segments in local (u, v) = (radius, z) coordinates.
    count = len(pts)
    for i, pt in enumerate(pts):
        nxt = pts[(i + 1) % count]
        sketch.addGeometry(
            Part.LineSegment(App.Vector(pt.x, pt.z, 0.0),
                             App.Vector(nxt.x, nxt.z, 0.0)), False)

    # Close the wire: end of segment i to the start of segment i + 1.
    # (Added after all geometry exists: constraints need valid GeoIds.)
    for i in range(count):
        sketch.addConstraint(
            Sketcher.Constraint("Coincident", i, 2, (i + 1) % count, 1))
    return sketch


def pin_retained_revolved(doc, name, height, diam, diam_end,
                          angle=45.0, clearance=0.0):
    """pin_retained() as a solid of revolution (Part::Revolution).

    Builds profile_sketch() as `{name}_sketch` and revolves it a full
    360 degrees about the z axis. Same parameters, identical solid and
    the same None-on-invalid behaviour as pin_retained(); the sketch is
    hidden as construction.
    """
    if profile_points(height, diam, diam_end,
                      angle=angle, clearance=clearance) is None:
        return None
    sketch = profile_sketch(doc, f"{name}_sketch", height, diam, diam_end,
                            angle=angle, clearance=clearance)

    rev = doc.addObject("Part::Revolution", name)
    rev.Source = sketch
    rev.Axis = App.Vector(0.0, 0.0, 1.0)
    rev.Angle = 360.0
    _hide(sketch)
    return rev


# ==========================================
# MODULE TESTING AND EXECUTION ENTRY POINT
# ==========================================
def _is_main():
    """True when this file is the one FreeCAD was asked to run.

    freecadcmd executes a file with __name__ set to the script's basename
    (not '__main__'), so compare the file against sys.argv as well; that
    way importing the module never fires the entry point.
    """
    if __name__ == "__main__":
        return True
    try:
        return (len(sys.argv) > 1
                and os.path.samefile(__file__, os.path.abspath(sys.argv[1])))
    except OSError:
        return False


if _is_main():
    HEIGHT = 10.0        # h    overall pin height                (mm)
    PIN_DIAM = 6.0       # pd   shaft diameter                    (mm)
    FLARE_DIAM = 10.0    # rd   retain (flare) diameter           (mm)
    ANGLE = 45.0         # p_ang flare flank angle                (deg)
    CLEARANCE = 0.1      # c    envelope growth normal to faces   (mm)

    doc = App.activeDocument()
    if not doc:
        doc = App.newDocument("PinRetainedDoc")

    # Inspection block: x = +/- 3 * rd, z = +/- 2 * h, but material on the
    # +y side only (y = 0 .. 3 * rd), so the y = 0 face is the section.
    block_base = doc.addObject("Part::Box", "Block_base")
    block_base.Length = 6.0 * FLARE_DIAM
    block_base.Width = 3.0 * FLARE_DIAM
    block_base.Height = 4.0 * HEIGHT
    block_base.Placement.Base = App.Vector(-3.0 * FLARE_DIAM, 0.0,
                                           -2.0 * HEIGHT)

    # The clearance envelope hollows the pin-shaped cavity out of it.
    # pin_retained() starts every pin at z = 0, so the envelope is built
    # flush against the nominal one; drop it by c to centre it on the
    # pin, then every face of the section shows the gap.
    env = pin_retained(doc, "ClearancePin", HEIGHT, PIN_DIAM, FLARE_DIAM,
                       angle=ANGLE, clearance=CLEARANCE)
    env.Placement.Base.z = -CLEARANCE
    block = doc.addObject("Part::Cut", "Block")
    block.Base = block_base
    block.Tool = env
    _hide(block_base)
    _hide(env)

    # The complete nominal pin sits in the cavity; the y = 0 face shows
    # the clearance sectioned around it.
    pin = pin_retained(doc, "Pin", HEIGHT, PIN_DIAM, FLARE_DIAM, angle=ANGLE)

    d = derived_geometry(HEIGHT, PIN_DIAM, FLARE_DIAM, angle=ANGLE)
    App.Console.PrintMessage(
        f"cone_height = {d['cone_height']:.3f} mm\n"
        f"shaft_len   = {d['shaft_len']:.3f} mm\n"
        f"cone_apex   = {d['cone_apex']:.3f} mm\n")

    doc.recompute()
