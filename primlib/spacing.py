"""SPACING -- lay pieces along a length, symmetrically, as live spreadsheet formulas.

A span is filled with big pieces (`Target` long) and little pieces (`LittleLength`
long), with a spacer between neighbours and, if asked, at both ends. Whatever is
left over goes in the odd pieces. The count of bigs decides how many odd pieces
there are, so that the row stays symmetric:

    an even number of bigs: one odd piece, in the middle
        little  big  big  ODD  big  big  little
    an odd number of bigs: two equal odd pieces, either side of the middle big
        little  big  ODD  big  ODD  big  little

    odd length = (Span - Bigs * Target - Littles * LittleLength
                  - spacers * Spacer) / odd pieces
    spacers = pieces - 1 + 2 * EndSpacers

`add_spacing` writes that as plain formulas on a sheet, so a saved file adjusts
itself in FreeCAD without primlib or a script, whatever the span or the fields
become. `Status` says "OK" or what to change. Each piece's start, length and kind
are in a table, measured from the span's start, with a fixed number of slots
since a sheet can't grow by itself; a piece past the last is flagged in `Status`.
"""

from primlib.core import add_parameter, add_section, next_row

SLOTS = 15


def spacing(span, target, spacer, bigs, littles=0, little_length=0, end_spacers=0):
    """The same layout in Python: [(kind, start, length), ...]."""
    odds = 2 if bigs % 2 else 1
    pieces = bigs + littles + odds
    gaps = pieces - 1 + 2 * end_spacers
    odd = (span - bigs * target - littles * little_length - gaps * spacer) / odds
    middle = ["big"] * (bigs // 2) + ["odd"] + ["big"] * (bigs // 2)
    if bigs % 2:
        middle = ["big"] * (bigs // 2) + ["odd", "big", "odd"] + ["big"] * (bigs // 2)
    kinds = ["little"] * (littles // 2) + middle + ["little"] * (littles // 2)
    lengths = {"big": target, "odd": odd, "little": little_length}
    out, at = [], end_spacers * spacer
    for kind in kinds:
        out.append((kind, at, lengths[kind]))
        at += lengths[kind] + spacer
    return out


def add_spacing(sheet, prefix, span, target="50 mm", max_part="80 mm", min_part="20 mm",
                spacer="10 mm", bigs=4, littles=0, little_length="20 mm", end_spacers=1,
                slots=SLOTS):
    """Append a spacing section to `sheet`, its aliases starting `prefix`_.
    `span` is an expression; the rest are this row's starting values, for the
    user to change on the sheet."""
    p = f"{prefix}_"
    add_section(sheet, f"Spacing: {prefix}")
    add_parameter(sheet, f"{p}Span", f"={span}", "the length to fill")
    add_parameter(sheet, f"{p}Target", f"={target}", "a big piece's length")
    add_parameter(sheet, f"{p}MaxPart", f"={max_part}", "the longest odd piece allowed")
    add_parameter(sheet, f"{p}MinPart", f"={min_part}", "the shortest odd piece allowed")
    add_parameter(sheet, f"{p}Spacer", f"={spacer}", "the spacer between pieces")
    add_parameter(sheet, f"{p}Bigs", f"={bigs}", "how many big pieces: even gives one odd "
                                                 "piece, odd gives two")
    add_parameter(sheet, f"{p}Littles", f"={littles}", "how many little pieces, half at each "
                                                       "end: must be even")
    add_parameter(sheet, f"{p}LittleLength", f"={little_length}", "a little piece's length")
    add_parameter(sheet, f"{p}EndSpacers", f"={end_spacers}", "1: a spacer at both ends too; "
                                                              "0: none")

    add_section(sheet, "Result", style="italic")
    S, T, G = f"{p}Span", f"{p}Target", f"{p}Spacer"
    B, L, LL, E = f"{p}Bigs", f"{p}Littles", f"{p}LittleLength", f"{p}EndSpacers"
    O, P, N, K = f"{p}OddPieces", f"{p}Pieces", f"{p}Spacers", f"{p}OddLength"
    add_parameter(sheet, O, f"=mod({B}; 2) == 1 ? 2 : 1", "odd pieces: set by the bigs")
    add_parameter(sheet, P, f"={B} + {L} + {O}", "pieces in all")
    add_parameter(sheet, N, f"={P} - 1 + 2 * {E}", "spacers in all")
    add_parameter(sheet, K, f"=({S} - {B} * {T} - {L} * {LL} - {N} * {G}) / {O}",
                  "each odd piece's length")
    A, Z = f"{p}OddPlaceA", f"{p}OddPlaceB"
    add_parameter(sheet, A, f"=mod({B}; 2) == 1 ? ({B} - 1) / 2 : {B} / 2",
                  "the first odd piece's place among the bigs and odds, from 0")
    add_parameter(sheet, Z, f"=mod({B}; 2) == 1 ? ({B} - 1) / 2 + 2 : {B} / 2",
                  "the second's: the same place when there's only one")
    add_parameter(sheet, f"{p}Status",
                  f"=mod({L}; 2) == 1 ? <<Littles must be even>> : "
                  f"({P} > {slots} ? <<Too many pieces for the table>> : "
                  f"({K} < {p}MinPart ? <<Odd piece too short: fewer bigs, littles or spacers>> : "
                  f"({K} > {p}MaxPart ? <<Odd piece too long: more bigs or littles>> : <<OK>>)))",
                  "OK, or what to change")

    add_section(sheet, "Pieces", style="italic")
    row = next_row(sheet)
    for col, title in zip("ABCD", ("Piece", "Start", "Length", "Kind")):
        sheet.set(f"{col}{row}", title)
    for i in range(slots):
        r = row + 1 + i
        m = f"({i} - {L} / 2)"              # its place among the bigs and odds
        def pick(none, little, big, odd_piece):
            return (f"={i} >= {P} ? {none} : ({i} < {L} / 2 ? {little} : "
                    f"({i} >= {P} - {L} / 2 ? {little} : "
                    f"({m} == {A} ? {odd_piece} : ({m} == {Z} ? {odd_piece} : {big}))))")
        sheet.set(f"A{r}", str(i + 1))
        sheet.set(f"C{r}", pick("0 mm", LL, T, K))
        sheet.setAlias(f"C{r}", f"{p}Length{i + 1}")
        sheet.set(f"D{r}", pick("<<>>", "<<little>>", "<<big>>", "<<odd>>"))
        sheet.setAlias(f"D{r}", f"{p}Kind{i + 1}")
        start = f"={E} * {G}" if i == 0 else f"={p}Start{i} + {p}Length{i} + {G}"
        sheet.set(f"B{r}", start)
        sheet.setAlias(f"B{r}", f"{p}Start{i + 1}")
    return p
