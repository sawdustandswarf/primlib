# Retained pin — parameters and revolve profile

> This note documents the 20 mm drawing sample in `doc/pin_retained.html`.
> For the chosen nominal set (`h = 10`) see `doc/pin.html`.

Source: `doc/pin_retained.html`, modelled by `pin_retained.py`.
Drawing: `doc/pin_retained_clearance_front.svg` (nominal pin in grey,
clearance envelope in red — extracted from the HTML).

## Parameters

| symbol   | name                     | value    | note                                                 |
|----------|--------------------------|----------|------------------------------------------------------|
| `pd`     | pin (shaft) diameter     | 6.0 mm   | straight central shaft                               |
| `rd`     | retain (flare) diameter  | 10.0 mm  | outer diameter at each end face                      |
| `h`      | overall pin height       | 20.0 mm  | end face to end face (sample; module default is 10)  |
| `p_ang`  | flare flank angle (`angle`) | 45°   | flare flank angle to the end face                    |
| `c`      | clearance (`clearance`)  | 0.10 mm  | optional; pushes every face out along its own normal |

Derived:

| symbol | meaning                            | expression                       | value    |
|--------|------------------------------------|----------------------------------|----------|
| cone   | visible cone (frustum) height      | `(rd/2 − pd/2)·tan(p_ang)`        | 2.0 mm   |
| `ls`   | straight shaft length              | `h − 2·cone`                     | 16.0 mm  |
| `ca`   | complete-cone height (face → apex) | `(rd/2)·tan(p_ang)`              | 5.0 mm   |

Valid range: `0 < p_ang < 90`, `rd > pd`, `h > 2·cone`.

## Rotation area (meridian profile) — nominal pin

Closed polyline in the XZ half-plane (`y = 0`), revolved 360° about the
z axis. Point form: `(x, y, z)`.

| point | x                    | y   | z                | between                       |
|-------|----------------------|-----|------------------|-------------------------------|
| P0    | `0`                  | `0` | `0`              | axis, bottom                  |
| P1    | `rd/2`               | `0` | `0`              | bottom end face → flare rim   |
| P2    | `pd/2`               | `0` | `cone`           | flare flank → shaft           |
| P3    | `pd/2`               | `0` | `h − cone`       | shaft → top flare             |
| P4    | `rd/2`               | `0` | `h`              | flare flank → top rim         |
| P5    | `0`                  | `0` | `h`              | top end face → axis           |

with `cone = (rd/2 − pd/2)·tan(p_ang)`.

Path (`x,z`, numbers from the table values):

```
M 0,0 L 5,0 L 3,2 L 3,18 L 5,20 L 0,20 Z
```

## Rotation area — clearance version

Same six-point form with clearance-grown values (equal to the nominal
ones when `c = 0`):

```
h'  = h + 2c
pd' = pd + 2c
rd' = rd + 2c/tan(p_ang/2)   (= rd + 2c·cot(p_ang/2))
cone' = (rd'/2 − pd'/2)·tan(p_ang)
```

| point | x                 | y   | z                   | between                       |
|-------|-------------------|-----|---------------------|-------------------------------|
| P0    | `0`               | `0` | `0`                 | axis, bottom                  |
| P1    | `rd'/2`           | `0` | `0`                 | bottom end face → flare rim   |
| P2    | `pd'/2`           | `0` | `cone'`             | flare flank → shaft           |
| P3    | `pd'/2`           | `0` | `h' − cone'`        | shaft → top flare             |
| P4    | `rd'/2`           | `0` | `h'`                | flare flank → top rim         |
| P5    | `0`               | `0` | `h'`                | top end face → axis           |

Path (`x,z`, `c = 0.10 mm`, `p_ang = 45°`):

```
M 0,0 L 5.241421,0 L 3.1,2.141421 L 3.1,18.058579 L 5.241421,20.2 L 0,20.2 Z
```

The envelope is built from `z = 0` like any pin; to centre it on the
nominal pin (as drawn) shift it by `−c`, i.e. `z → z − c`, so it spans
`z = −0.1 … 20.1`.
