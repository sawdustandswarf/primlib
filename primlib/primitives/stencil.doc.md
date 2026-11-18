# stencil: documentation overrides

The author's requests for this primitive's page. They win over the standard page
template, for this primitive only. Each entry has the author's words and the date.
Remove an entry when the author withdraws it.

## First order

The first order parameters, most important first (confirmed by the author: not yet).

- `lines` and each line's `text{i}`: up to six lines (the author, 2026-11-11: "upto 6 lines of text, with different fonts"; first "use the two line approach")
- `text_size` and each line's `size{i}`
- `font` and each line's `font{i}`
- each line's `h{i}` and `v{i}`: justification, horizontal and vertical (the author, 2026-11-11: "justify the text of each line in both vertical and horizontal settings")
- `origin_x`, `origin_y`: the text's origin from the template's centre (the author, 2026-11-13: "Lets make it in centre of the template"; first, 2026-11-11, "a specified origin wrt to corner"), and each line's `line{i}_x`, `line{i}_y` from it
- `fence_top`, `fence_bottom`, `fence_left`, `fence_right`: a fence on any side, each on or off (the author, 2026-11-13: "add fences to any side of the stencil, but be able to turn them on / off"; for "a very large part to put text in the centre", the top fence alone)
- `length`, `width`: the plate's area ("Set area")
- `thickness` ("Set Thickness")
- `bit_d`: the router's guide bearing ("using a router with a template following bit")
- `clearance`

Units: in mm on a project's sheet (the author, 2026-11-11: "The units need to be in mm"); the library takes plain numbers, bound as `Alias / 1 mm`.

## Parts

For an assembly: the part names to use on the page, in order.

- Template A (`{name}_a`): the first pass, bridges at `bar_a1` and `bar_a2`
- Template B (`{name}_b`): the second pass, which completes what A's bridges hid (the author, 2026-11-11: "a second template that will be used to complete the missing parts")

## Layout

Sections to add, drop or reorder, and views or dimensions to add or leave out.

-

## Text

Text to appear on the page word for word, with the section it goes in.

-
