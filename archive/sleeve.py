r"""
================================================================================
SLEEVE -- hollow barrel that rides the retained pin
================================================================================

The sleeve is a hollow barrel that wraps a retained pin (see
`pin_retained.py` in this library) with a running clearance. Its exterior is
a cylinder capped by 45-degree cone flanks that meet at a sharp "ridge" ring;
its interior is the retained pin grown by `tolerance` on every face.

        /\             /\
      /   \          /    \
    /      \        /      \
   |        |      |        |
   |   kt   |      |        |
->|            kd             |<-
   |        |      |        |
   |        |      |        |
    \      /        \      /
      \   /          \   /
        \/              \/

Coordinate convention
---------------------
  Z runs along the pin axis. A sleeve spans exactly z = 0 .. height, matching
  one pin segment. Radii are measured from the axis (r = 0).

End faces
---------
The exterior flanks are 45 degrees, so each end face follows |r - ridge|:

  bottom face:  z = |r - a|              (W  -- valley ring at r = a)
  top face:     z = height - |r - a|     (inverted W -- ridge ring at r = a)

Two stacked sleeves therefore touch only along the ring r = a ("kiss at a
ring"); everywhere else the gap is 2 * |r - a|.

Interior
--------
The retained pin plus a running clearance (tolerance) is subtracted from the
profiled body, leaving an annular wall between the bore and the sleeve's
outside diameter:

  outer_rad  = diam_outer / 2                   sleeve outside radius (kd/2)
  flare_rad  = diam_end / 2 + tolerance         bore radius at the end faces
  throat_rad = diam / 2 + tolerance             bore radius at the waist
  ridge      = (flare_rad + outer_rad) / 2      default ridge ring (auto)

Near the end faces the toleranced pin's flares lie inside the valleys the
cut tools have already opened, so only its throat cylinder does any
cutting: the bore the sleeve presents is the valley cones (r = a - z)
opening into the throat cylinder. The pin's flares ride in the valleys
with a radial gap of outer_rad - a = rim_h (the two 45-degree cones are
parallel), and retention is flare-vs-throat -- the flare
(diam_end + 2 * tolerance) cannot pass the throat (diam + 2 * tolerance).

Parameters
----------
  height         h      sleeve height, one pin segment (mm)
  diam           pd     pin shaft diameter (mm)
  diam_end       rd     pin retain (flare) diameter (mm)
  diam_outer     kd     sleeve outside diameter (mm, default 13.0)
  tolerance      tol    radial running clearance, pin -> bore (mm, default 0.1)
  ridge_radius   a      contact ring radius (mm); defaults to the midpoint
                        between the bore flare and the outer wall

The sleeve wall thickness is therefore derived, not a parameter:
kt = diam_outer / 2 - (diam_end / 2 + tolerance).

Library defaults: h = 10, pd = 6, rd = 10, kd = 13, tol = 0.1.

Derived geometry
----------------
  outer_rad   d_outer/2                 sleeve outside radius (kd/2)
  flare_rad   rd/2 + tol                bore radius at the end faces
  throat_rad  pd/2 + tol                bore radius at the waist
  ridge       (flare_rad + outer_rad)/2 default contact ring radius
  rim_h       outer_rad - a             wedge height of each 45-degree flank
  bore_flare  (rd - pd) / 2             bore cone height (end face -> waist)

Revolve profile (sketch in the XZ half-plane, y = 0)
-----------------------------------------------------
profile_points() computes the closed polyline below; revolved 360 degrees
about the z axis it sweeps the whole sleeve -- the W-shaped outer wall
and the bore -- in one operation. The sketch lies in the XZ half-plane
(y = 0): x is the distance from the axis, z the height. Each vertex as
an (x, y, z) point, in path order:

    outer wall        Q2 (outer_rad, 0, h-rim_h) -- Q3 (ridge, 0, h)
      at r=outer:        |                          /
                         |  outer wall              /  W flank
                         |                         /
    valley apex         |                  Q1 (outer_rad, 0, rim_h)
      at r=ridge:        |                          |
                         |                          |  outer wall
                         |                  Q0 (ridge, 0, 0)
   (axis at x = 0, to the left; bore valley cones r = ridge - z and
    r = ridge - (h - z) meet the throat cylinder at z = valley_z and
    z = h - valley_z)

  Q0 = (ridge,      0, 0              )   valley apex, bottom (bore vee)
  Q1 = (outer_rad,  0, rim_h          )   bottom flank -> outer wall
  Q2 = (outer_rad,  0, h - rim_h      )   outer wall -> top flank
  Q3 = (ridge,      0, h              )   top flank -> valley apex, top
  Q4 = (throat_rad, 0, h - valley_z   )   top valley cone -> throat
  Q5 = (throat_rad, 0, valley_z       )   throat -> bottom valley cone
  close: Q5 -> Q0 along the bottom valley cone (r = ridge - z)

where valley_z = ridge - throat_rad is the height at which each valley
cone meets the throat cylinder. The bore therefore presents the two
45-degree valley cones (r = ridge - z at the bottom, r = ridge - (h - z)
at the top) opening into the throat cylinder -- exactly the surfaces the
cut tools leave. The pin's own flares are parallel to these cones and
ride in them with a radial gap of outer_rad - ridge = rim_h.

The path is Q0 -> Q1 -> Q2 -> Q3 -> Q4 -> Q5 and closes back to Q0.
Nothing touches the axis, so the revolved solid is hollow; the wire runs
counter-clockwise in the (r, z) half-plane.

Note the ridge ring (r = ridge) sits at *both* extreme heights z = 0 and
z = h, where the W wedges pinch to a sharp edge.

Valid range / constraints
-------------------------
  * diam_outer > diam_end + 2 * tolerance  (the sleeve needs a wall)
  * ridge > flare_rad      (the contact ring must clear the bore)
  * ridge <= outer_rad     (the ridge cannot stick out past the wall)
  * outer_rad - ridge < height / 2   (the W flanks must fit in the height)
  * height > 2 * bore_flare          (the bore flares must fit)
  Outside that range sleeve() reports an error and builds nothing.

API
----
  sleeve(doc, name, height, diam, diam_end,
         diam_outer=13.0, tolerance=0.1, ridge_radius=None)
      Build the sleeve into `doc`. Returns the Part::Cut result, or None
      (with a console error) if the parameters violate the constraints
      above. The internal void is built by `pin_retained()` from
      `pin_retained.py` in this library, grown by `tolerance`.

  derived_geometry(height, diam, diam_end, diam_outer=13.0,
                   tolerance=0.1, ridge_radius=None)
      Return the derived dimensions as a dict: outer_rad, flare_rad,
      throat_rad, ridge, rim_h, bore_flare.

  profile_points(height, diam, diam_end, diam_outer=13.0,
                 tolerance=0.1, ridge_radius=None)
      The revolve profile Q0..Q5 above as six App.Vector (x, 0, z);
      None (with a console error) when the parameters are invalid.

  profile_sketch(doc, name, height, diam, diam_end, diam_outer=13.0,
                 tolerance=0.1, ridge_radius=None)
      Build the profile as a Sketcher sketch in the XZ half-plane: a
      construction line on the axis (GeoId 0), then the six profile
      segments, each tied to the next by a coincidence constraint so the
      wire stays closed when dragged in the GUI. The profile never
      touches the axis, so the axis line is separate construction
      geometry. Local (u, v) of the sketch plane maps to global
      (u, 0, v). Returns the sketch, or None on invalid parameters.

  sleeve_revolved(doc, name, height, diam, diam_end, diam_outer=13.0,
                  tolerance=0.1, ridge_radius=None)
      sleeve() as a solid of revolution: profile_sketch() named
      `{name}_sketch` revolves 360 degrees about the z axis through a
      Part::Revolution. Same parameters, identical solid, same
      None-on-invalid behaviour; the sketch is hidden as construction.

  inspection_section(doc, pin_obj, sleeve_obj, height, diam_outer)
      Cut both objects with the same box to expose a meridian section for
      visual inspection. Returns the two Part::Cut results.

Run this file directly (freecadcmd sleeve.py) to build an inspection model:
one retained pin plus one sleeve sliced down the centre axis.
================================================================================
"""

import os
import sys

import FreeCAD as App
import Part
import Sketcher

from pin_retained import pin_retained


def _hide(obj):
    """Hide a construction object when a GUI is present (headless has no ViewObject)."""
    view = getattr(obj, "ViewObject", None)
    if view is not None:
        view.Visibility = False


def _set_color(obj, rgb):
    view = getattr(obj, "ViewObject", None)
    if view is not None:
        view.ShapeColor = rgb


def derived_geometry(height, diam, diam_end, diam_outer=13.0,
                     tolerance=0.1, ridge_radius=None):
    """Derived sleeve dimensions (all mm); see the module docstring."""
    outer_rad = float(diam_outer) / 2.0
    flare_rad = float(diam_end) / 2.0 + float(tolerance)
    if ridge_radius is None:
        ridge_radius = (flare_rad + outer_rad) / 2.0
    ridge = float(ridge_radius)
    return {
        "outer_rad": outer_rad,                                # kd/2
        "flare_rad": flare_rad,                                # bore, end faces
        "throat_rad": float(diam) / 2.0 + float(tolerance),    # bore, waist
        "ridge": ridge,                                        # a
        "rim_h": outer_rad - ridge,                            # fl
        "bore_flare": (float(diam_end) - float(diam)) / 2.0,   # c_b
    }


def _resolve(height, diam, diam_end, diam_outer, tolerance,
             ridge_radius):
    """Resolve and validate every sleeve dimension.

    Returns a dict of floats -- h, d, d_end, d_outer, tol, outer_rad,
    flare_rad, throat_rad, ridge, rim_h, bore_flare -- or None after
    reporting which constraint failed (see the module docstring). Shared
    by sleeve(), profile_points() and sleeve_revolved() so every
    construction route agrees on the same solid.
    """
    p = derived_geometry(height, diam, diam_end, diam_outer=diam_outer,
                         tolerance=tolerance, ridge_radius=ridge_radius)
    p["h"] = float(height)
    p["d"] = float(diam)
    p["d_end"] = float(diam_end)
    p["d_outer"] = float(diam_outer)
    p["tol"] = float(tolerance)

    if p["outer_rad"] <= p["flare_rad"]:
        App.Console.PrintError(
            f"Error: diam_outer ({p['d_outer']}) must exceed the pin flare "
            f"diameter plus clearance ({2.0 * p['flare_rad']}) so the sleeve "
            f"has a wall.\n")
        return None
    if p["bore_flare"] >= p["h"] / 2.0:
        App.Console.PrintError(
            f"Error: the sleeve is too short ({p['h']}) for the pin's two end "
            f"flares.\n")
        return None
    if p["ridge"] <= p["flare_rad"]:
        App.Console.PrintError(
            f"Error: ridge_radius ({p['ridge']}) must exceed the pin flare "
            f"radius ({p['flare_rad']}) so the contact ring clears the pin "
            f"cut.\n")
        return None
    if p["ridge"] > p["outer_rad"]:
        App.Console.PrintError(
            f"Error: ridge_radius ({p['ridge']}) exceeds the sleeve outer "
            f"radius ({p['outer_rad']}).\n")
        return None
    if p["rim_h"] >= p["h"] / 2.0:
        App.Console.PrintError(
            f"Error: sleeve is too short ({p['h']}) for these 45-degree W "
            f"flanks.\n")
        return None
    return p


def sleeve(doc, name, height, diam, diam_end,
           diam_outer=13.0, tolerance=0.1, ridge_radius=None):
    """
    Hollow sleeve exactly `height` tall, riding a retained pin.

    `diam` is the pin shaft diameter; `diam_end` is the pin retain (flare)
    diameter. `diam_outer` is the sleeve's outside diameter and `tolerance`
    the radial running clearance over the pin. `ridge_radius` defaults to
    the midpoint between the bore flare and the outer wall so the contact
    ring clears the pin cut.

    Returns the Part::Cut result, or None (with a console error) when the
    parameters are outside the valid range documented at the top of this file.
    """
    p = _resolve(height, diam, diam_end, diam_outer, tolerance,
                 ridge_radius)
    if p is None:
        return None
    h, d, d_end = p["h"], p["d"], p["d_end"]
    outer_rad, a, rim_h = p["outer_rad"], p["ridge"], p["rim_h"]
    tol = p["tol"]

    # 1. Plain outer body -- exactly one sleeve tall.
    body = doc.addObject("Part::Cylinder", f"{name}_body")
    body.Radius = outer_rad
    body.Height = h

    # 2. Bottom W cut tool: removes { z < |r - a| }.
    bot_core = doc.addObject("Part::Cone", f"{name}_bot_core")          # r = a - z
    bot_core.Radius1 = a
    bot_core.Radius2 = 0.0
    bot_core.Height = a
    bot_core.Placement.Base = App.Vector(0, 0, 0)

    bot_rim_cyl = doc.addObject("Part::Cylinder", f"{name}_bot_rim_cyl")
    bot_rim_cyl.Radius = outer_rad
    bot_rim_cyl.Height = rim_h
    bot_rim_cyl.Placement.Base = App.Vector(0, 0, 0)

    bot_rim_cone = doc.addObject("Part::Cone", f"{name}_bot_rim_cone")  # r = a + z
    bot_rim_cone.Radius1 = a
    bot_rim_cone.Radius2 = outer_rad
    bot_rim_cone.Height = rim_h
    bot_rim_cone.Placement.Base = App.Vector(0, 0, 0)

    bot_rim = doc.addObject("Part::Cut", f"{name}_bot_rim")
    bot_rim.Base = bot_rim_cyl
    bot_rim.Tool = bot_rim_cone

    bot_tool = doc.addObject("Part::MultiFuse", f"{name}_bot_tool")
    bot_tool.Shapes = [bot_core, bot_rim]

    # 3. Top inverted-W cut tool: removes { z > h - |r - a| }.
    top_core = doc.addObject("Part::Cone", f"{name}_top_core")          # r = z - (h - a)
    top_core.Radius1 = 0.0
    top_core.Radius2 = a
    top_core.Height = a
    top_core.Placement.Base = App.Vector(0, 0, h - a)

    top_rim_cyl = doc.addObject("Part::Cylinder", f"{name}_top_rim_cyl")
    top_rim_cyl.Radius = outer_rad
    top_rim_cyl.Height = rim_h
    top_rim_cyl.Placement.Base = App.Vector(0, 0, h - rim_h)

    top_rim_cone = doc.addObject("Part::Cone", f"{name}_top_rim_cone")  # r = a + (h - z)
    top_rim_cone.Radius1 = outer_rad
    top_rim_cone.Radius2 = a
    top_rim_cone.Height = rim_h
    top_rim_cone.Placement.Base = App.Vector(0, 0, h - rim_h)

    top_rim = doc.addObject("Part::Cut", f"{name}_top_rim")
    top_rim.Base = top_rim_cyl
    top_rim.Tool = top_rim_cone

    top_tool = doc.addObject("Part::MultiFuse", f"{name}_top_tool")
    top_tool.Shapes = [top_core, top_rim]

    # 4. Trim the body to the W / inverted-W profile.
    profiled = doc.addObject("Part::Cut", f"{name}_profiled")
    profiled.Base = body
    profiled.Tool = bot_tool

    profiled_top = doc.addObject("Part::Cut", f"{name}_profiled_top")
    profiled_top.Base = profiled
    profiled_top.Tool = top_tool

    # 5. Hollow it out for the retained pin (clearance included).
    toleranced_pin = pin_retained(doc, f"{name}_internal_void",
                                  h, d + 2.0 * tol, d_end + 2.0 * tol)
    if not toleranced_pin:
        return None

    result = doc.addObject("Part::Cut", name)
    result.Base = profiled_top
    result.Tool = toleranced_pin

    for part in (body, bot_core, bot_rim_cyl, bot_rim_cone, bot_rim, bot_tool,
                 top_core, top_rim_cyl, top_rim_cone, top_rim, top_tool,
                 profiled, profiled_top, toleranced_pin):
        _hide(part)

    return result


def profile_points(height, diam, diam_end,
                   diam_outer=13.0, tolerance=0.1, ridge_radius=None):
    """The revolve profile Q0..Q5 as six App.Vector (x, 0, z).

    Vertices follow the module docstring: bottom valley apex -> bottom
    flank -> outer wall -> top flank -> top valley apex, then down the
    top valley cone to the throat, and back along the bottom valley cone
    to close. The bore is the two 45-degree valley cones the cut tools
    leave, not the pin profile. Returns None (with a console error) on
    invalid parameters.
    """
    p = _resolve(height, diam, diam_end, diam_outer, tolerance,
                 ridge_radius)
    if p is None:
        return None
    R, a, fl = p["outer_rad"], p["ridge"], p["rim_h"]
    throat = p["throat_rad"]
    h = p["h"]
    valley_z = a - throat              # height where the valley meets the throat
    return [
        App.Vector(a, 0.0, 0.0),             # Q0  bottom valley apex
        App.Vector(R, 0.0, fl),              # Q1  bottom flank -> outer wall
        App.Vector(R, 0.0, h - fl),          # Q2  outer wall -> top flank
        App.Vector(a, 0.0, h),               # Q3  top flank -> top valley apex
        App.Vector(throat, 0.0, h - valley_z),   # Q4  top valley -> throat
        App.Vector(throat, 0.0, valley_z),       # Q5  throat -> bottom valley
    ]


def profile_sketch(doc, name, height, diam, diam_end,
                   diam_outer=13.0, tolerance=0.1, ridge_radius=None):
    """The revolve profile as a Sketcher sketch in the XZ half-plane (y = 0).

    GeoId 0 is a construction line marking the axis; GeoIds 1..6 are the
    profile segments Q0->Q1->...->Q5->Q0, each tied to the next by a
    coincidence constraint so the wire stays closed when dragged. The
    profile never reaches the axis (the sleeve is hollow), so the axis
    line is separate construction geometry. The sketch's local (u, v)
    maps to global (u, 0, v): u is the distance from the axis, v the
    height. Returns the sketch, or None when the parameters are invalid.
    """
    pts = profile_points(height, diam, diam_end, diam_outer=diam_outer,
                         tolerance=tolerance, ridge_radius=ridge_radius)
    if pts is None:
        return None

    sketch = doc.addObject("Sketcher::SketchObject", name)
    # Local (u, v) -> global (u, 0, v): rotate the local XY plane onto XZ.
    sketch.Placement = App.Placement(
        App.Vector(0.0, 0.0, 0.0), App.Rotation(App.Vector(1, 0, 0), 90.0))

    # The axis itself (construction geometry, invisible in the shape).
    sketch.addGeometry(
        Part.LineSegment(App.Vector(0.0, 0.0, 0.0),
                         App.Vector(0.0, pts[3].z, 0.0)), True)

    # Profile segments in local (u, v) = (radius, z) coordinates.
    count = len(pts)
    for i, pt in enumerate(pts):
        nxt = pts[(i + 1) % count]
        sketch.addGeometry(
            Part.LineSegment(App.Vector(pt.x, pt.z, 0.0),
                             App.Vector(nxt.x, nxt.z, 0.0)), False)

    # Close the wire: end of segment i to the start of segment i + 1.
    # (Added after all geometry exists: constraints need valid GeoIds.)
    # GeoId 0 is the axis, so segment i sits at GeoId i + 1.
    for i in range(count):
        sketch.addConstraint(
            Sketcher.Constraint("Coincident", i + 1, 2,
                                (i + 1) % count + 1, 1))
    return sketch


def sleeve_revolved(doc, name, height, diam, diam_end,
                    diam_outer=13.0, tolerance=0.1, ridge_radius=None):
    """sleeve() as a solid of revolution (Part::Revolution).

    Builds profile_sketch() as `{name}_sketch` and revolves it a full 360
    degrees about the z axis. Same parameters, identical solid and the
    same None-on-invalid behaviour as sleeve(); the sketch is hidden as
    construction.
    """
    if profile_points(height, diam, diam_end, diam_outer=diam_outer,
                      tolerance=tolerance,
                      ridge_radius=ridge_radius) is None:
        return None
    sketch = profile_sketch(doc, f"{name}_sketch", height, diam, diam_end,
                            diam_outer=diam_outer, tolerance=tolerance,
                            ridge_radius=ridge_radius)

    rev = doc.addObject("Part::Revolution", name)
    rev.Source = sketch
    rev.Axis = App.Vector(0.0, 0.0, 1.0)
    rev.Angle = 360.0
    _hide(sketch)
    return rev


def inspection_section(doc, pin_obj, sleeve_obj, height, diam_outer=13.0):
    """Cross-section slice down the centre axis (XZ plane) for visual inspection."""
    box_size = (float(diam_outer) / 2.0) * 3.0
    box_height = float(height) * 4.0

    slice_box = doc.addObject("Part::Box", "InspectionSliceBox")
    slice_box.Length = box_size * 2.0
    slice_box.Width = box_size
    slice_box.Height = box_height
    slice_box.Placement.Base = App.Vector(-box_size, -box_size, -box_size)
    _hide(slice_box)

    pin_section = doc.addObject("Part::Cut", "Inspection_Pin_Half")
    pin_section.Base = pin_obj
    pin_section.Tool = slice_box

    sleeve_section = doc.addObject("Part::Cut", "Inspection_Sleeve_Half")
    sleeve_section.Base = sleeve_obj
    sleeve_section.Tool = slice_box

    _hide(pin_obj)
    _hide(sleeve_obj)

    _set_color(pin_section, (0.2, 0.6, 0.9))
    _set_color(sleeve_section, (0.8, 0.3, 0.3))

    return pin_section, sleeve_section


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
    SLEEVE_HEIGHT = 10.0   # h    sleeve / pin height                 (mm)
    PIN_DIAM = 6.0         # pd   pin shaft diameter                 (mm)
    FLARE_DIAM = 10.0      # rd   pin retain (flare) diameter        (mm)
    SLEEVE_DIAM = 13.0     # kd   sleeve outside diameter            (mm)
    CLEARANCE = 0.1        # tol  radial running clearance over pin  (mm)

    doc = App.activeDocument()
    if not doc:
        doc = App.newDocument("SleeveDoc")

    pin = pin_retained(doc, "Pin", SLEEVE_HEIGHT, PIN_DIAM, FLARE_DIAM)
    slv = sleeve(doc, "Sleeve", SLEEVE_HEIGHT, PIN_DIAM, FLARE_DIAM,
                 diam_outer=SLEEVE_DIAM, tolerance=CLEARANCE)
    inspection_section(doc, pin, slv, SLEEVE_HEIGHT, SLEEVE_DIAM)

    d = derived_geometry(SLEEVE_HEIGHT, PIN_DIAM, FLARE_DIAM,
                         diam_outer=SLEEVE_DIAM, tolerance=CLEARANCE)
    App.Console.PrintMessage(
        f"outer_rad  = {d['outer_rad']:.3f} mm\n"
        f"flare_rad  = {d['flare_rad']:.3f} mm\n"
        f"throat_rad = {d['throat_rad']:.3f} mm\n"
        f"ridge      = {d['ridge']:.3f} mm\n"
        f"rim_h      = {d['rim_h']:.3f} mm\n"
        f"bore_flare = {d['bore_flare']:.3f} mm\n")

    doc.recompute()
