import math

import boxes
from boxes import boolarg


class TrackStairs(boxes.Boxes):
    """Square spiral marble staircase around a central pillar."""

    ui_group = "Misc"

    SIDES = ("A", "B", "C", "D")

    def __init__(self) -> None:
        boxes.Boxes.__init__(self)

        self.addSettingsArgs(boxes.edges.FingerJointSettings)

        track_group = self.argparser.add_argument_group("TrackStairs Settings")
        plinko_group = self.argparser.add_argument_group("Plinko")

        track_group.add_argument(
            "--track_width", action="store", type=float, default=20.0,
            help="usable shelf depth from pillar to outer wall in mm")
        track_group.add_argument(
            "--wall_height", action="store", type=float, default=20.0,
            help="height of the outer track walls in mm")
        track_group.add_argument(
            "--x_side_length", action="store", type=float, default=80.0,
            help="length of the A/C pillar faces and matching shelves in mm")
        track_group.add_argument(
            "--y_side_length", action="store", type=float, default=80.0,
            help="length of the B/D pillar faces and matching shelves in mm")
        track_group.add_argument(
            "--entry_height", action="store", type=float, default=120.0,
            help="height of the entry end of the first shelf in mm")
        track_group.add_argument(
            "--exit_height", action="store", type=float, default=20.0,
            help="height of the exit end of the last shelf in mm")
        track_group.add_argument(
            "--entry_side", action="store", type=str, default="A",
            choices=self.SIDES,
            help="pillar side where the marble enters")
        track_group.add_argument(
            "--exit_side", action="store", type=str, default="C",
            choices=self.SIDES,
            help="pillar side where the marble exits")
        track_group.add_argument(
            "--direction", action="store", type=str, default="cw",
            choices=("cw", "ccw"),
            help="direction around the pillar from entry to exit")
        track_group.add_argument(
            "--turns", action="store", type=int, default=2,
            help="full turns around the pillar before reaching the exit side")
        track_group.add_argument(
            "--corner_extension", action="store", type=float, default=20.0,
            help="extra landing length on the outside of each shelf in mm")
        track_group.add_argument(
            "--shelf_drop", action="store", type=float, default=0.0,
            help="vertical drop between the exit of one shelf and entry of the next in mm")
        track_group.add_argument(
            "--entry_shelf_length", action="store", type=float, default=0.0,
            help="extra straight lead-in length before the first shelf in mm")
        track_group.add_argument(
            "--exit_shelf_length", action="store", type=float, default=0.0,
            help="extra straight lead-out length after the last shelf in mm")
        track_group.add_argument(
            "--lead_wall_min_length", action="store", type=float, default=10.0,
            help="minimum lead-in/out length that gets an inner wall in mm")
        plinko_group.add_argument(
            "--plinko", action="store", type=boolarg, default=False,
            help="optional plinko pin holes in the pillar walls")
        plinko_group.add_argument(
            "--plinko_hole_diameter", action="store", type=float, default=2.0,
            help="diameter of the plinko pin holes in mm")
        plinko_group.add_argument(
            "--plinko_pin_density", action="store", type=float, default=18.0,
            help="plinko pin spacing in mm; smaller values make denser pins")

    def _advance(self):
        return 1 if self.direction == "cw" else -1

    def _side_offset(self):
        start = self.SIDES.index(self.entry_side)
        end = self.SIDES.index(self.exit_side)
        return (end - start) % 4 if self.direction == "cw" else (start - end) % 4

    def _shelves(self):
        start = self.SIDES.index(self.entry_side)
        advance = self._advance()
        count = self.turns * 4 + self._side_offset() + 1
        total_drop = self.entry_height - self.exit_height
        gap_drop = self.shelf_drop * max(count - 1, 0)
        drop = (total_drop - gap_drop) / count

        shelves = []
        for i in range(count):
            side = self.SIDES[(start + advance * i) % 4]
            run = self.x_side_length if side in ("A", "C") else self.y_side_length
            z0 = self.entry_height - i * (drop + self.shelf_drop)
            z1 = z0 - drop
            slope_length = math.hypot(run, z0 - z1)
            angle = math.degrees(math.atan2(z1 - z0, run))
            shelves.append({
                "index": i + 1,
                "side": side,
                "run": run,
                "length": slope_length,
                "entry_extra": self.entry_shelf_length if i == 0 else 0.0,
                "exit_extra": self.exit_shelf_length if i == count - 1 else 0.0,
                "is_first": i == 0,
                "is_last": i == count - 1,
                "z0": z0,
                "z1": z1,
                "angle": angle,
            })

        return shelves

    def _shelves_for_side(self, side):
        return [s for s in self._shelves() if s["side"] == side]

    def _side_width(self, side):
        return self.x_side_length if side in ("A", "C") else self.y_side_length

    def _landing_length(self, shelf):
        if shelf["is_first"] and shelf["entry_extra"] > 0:
            return 0.0
        return self.corner_extension

    def _shelf_floor_segments(self, shelf):
        landing = self._landing_length(shelf)
        entry_extra = shelf["entry_extra"]
        exit_extra = shelf["exit_extra"]
        entry_edge = self.edges["f"] if entry_extra >= self.lead_wall_min_length else self.edges["e"]
        exit_edge = self.edges["f"] if exit_extra >= self.lead_wall_min_length else self.edges["e"]

        if shelf["is_last"]:
            segments = [
                (entry_extra, entry_edge),
                (shelf["length"], self.edges["f"]),
                (landing, self.edges["e"]),
            ]
            reverse = self.direction != "ccw"
            if reverse:
                segments.reverse()

            if exit_extra > 0:
                exit_segment = (exit_extra, exit_edge)
                if reverse:
                    segments.append(exit_segment)
                else:
                    segments.insert(0, exit_segment)

            return segments

        segments = [
            (entry_extra, entry_edge),
            (shelf["length"], self.edges["f"]),
            (landing, self.edges["e"]),
            (exit_extra, exit_edge),
        ]

        reverse = self.direction == "ccw"
        if not shelf["is_first"] and not shelf["is_last"]:
            reverse = not reverse

        if reverse:
            segments.reverse()

        return segments

    def _distance_to_shelf_slot(self, x, y, shelf):
        x1 = 0.0
        y1 = shelf["z0"]
        angle = math.radians(shelf["angle"])
        x2 = x1 + math.cos(angle) * shelf["length"]
        y2 = y1 + math.sin(angle) * shelf["length"]
        dx = x2 - x1
        dy = y2 - y1
        length2 = dx * dx + dy * dy

        if length2 == 0:
            return math.hypot(x - x1, y - y1)

        u = ((x - x1) * dx + (y - y1) * dy) / length2
        u = min(1.0, max(0.0, u))
        px = x1 + u * dx
        py = y1 + u * dy
        return math.hypot(x - px, y - py)

    def _shelf_y_at_x(self, shelf, x):
        x = min(shelf["run"], max(0.0, x))
        angle = math.radians(shelf["angle"])
        return shelf["z0"] + math.tan(angle) * x

    def _plinko_exit_surface_y(self):
        last_shelf = self._shelves()[-1]
        width = (self.x_side_length if last_shelf["side"] in ("A", "C")
                 else self.y_side_length)
        radius = 10.0
        x = width - radius
        x = min(width - radius, max(radius, x))
        return self._shelf_y_at_x(last_shelf, x) + self.thickness

    def _plinko_lowest_pin_y(self):
        return self._plinko_exit_surface_y() + 20.0 + 5.0 + 0.5 * self.plinko_hole_diameter

    def _plinko_exit_hole(self, width, height, side):
        if not self.plinko:
            return None

        last_shelf = self._shelves()[-1]
        if side != last_shelf["side"]:
            return None

        radius = 10.0
        x = width - radius
        x = min(width - radius, max(radius, x))
        y = self._shelf_y_at_x(last_shelf, x) + self.thickness + radius - 1.0
        y = min(height - radius, max(radius, y))
        return x, y, 2 * radius

    def plinko_holes(self, width, height, side):
        if not self.plinko:
            return

        spacing = self.plinko_pin_density
        diameter = self.plinko_hole_diameter
        margin = max(0.5 * spacing, 2 * diameter, 2 * self.thickness)
        slot_clearance = max(0.45 * spacing, diameter + self.thickness)
        lowest_pin = max(margin, self._plinko_lowest_pin_y())
        exit_hole = self._plinko_exit_hole(width, height, side)

        y = lowest_pin
        row = 0
        while y <= height - margin:
            x = margin + (0.5 * spacing if row % 2 else 0.0)
            while x <= width - margin:
                clear_of_exit = True
                if exit_hole is not None:
                    hx, hy, hd = exit_hole
                    clear_of_exit = math.hypot(x - hx, y - hy) >= 0.5 * hd + diameter
                if all(self._distance_to_shelf_slot(x, y, shelf) >= slot_clearance
                       for shelf in self._shelves_for_side(side)) and clear_of_exit:
                    self.hole(x, y, d=diameter)
                x += spacing
            y += spacing * 0.866
            row += 1

    def plinko_exit_hole(self, width, height, side):
        exit_hole = self._plinko_exit_hole(width, height, side)
        if exit_hole is not None:
            x, y, diameter = exit_hole
            self.hole(x, y, d=diameter)

    def _plinko_collector(self):
        if not self.plinko:
            return None

        last_shelf = self._shelves()[-1]
        exit_side = last_shelf["side"]
        exit_index = self.SIDES.index(exit_side)
        support_sides = (
            self.SIDES[(exit_index - 1) % 4],
            self.SIDES[(exit_index + 1) % 4],
        )
        run = self._side_width(support_sides[0])
        width = self._side_width(exit_side)
        panel_height = max(self.entry_height, self.exit_height) + 2 * self.thickness
        exit_hole = self._plinko_exit_hole(width, panel_height, exit_side)

        if exit_hole is None:
            return None

        _, y, diameter = exit_hole
        low_y = y - 0.5 * diameter
        rise = self.track_width
        high_y = low_y + rise
        length = math.hypot(run, rise)
        angle = math.degrees(math.atan2(low_y - high_y, run))
        finger_length = min(length, max(24.0, 1.25 * self.track_width))
        finger_start = max(0.0, length - finger_length - self.thickness)

        return {
            "exit_side": exit_side,
            "support_sides": support_sides,
            "run": run,
            "width": width,
            "length": length,
            "finger_start": finger_start,
            "finger_length": finger_length,
            "z0": high_y,
            "angle": angle,
        }

    def plinko_collector_slots(self, side):
        collector = self._plinko_collector()
        if collector is None or side not in collector["support_sides"]:
            return

        angle = math.radians(collector["angle"])
        x = math.cos(angle) * collector["finger_start"]
        y = collector["z0"] + math.sin(angle) * collector["finger_start"]
        self.fingerHolesAt(x, y, collector["finger_length"],
                           angle=collector["angle"])

    def pillar_panel(self, side, move=None):
        width = self._side_width(side)
        height = max(self.entry_height, self.exit_height) + 2 * self.thickness

        def slots():
            for shelf in self._shelves_for_side(side):
                self.fingerHolesAt(0, shelf["z0"], shelf["length"],
                                   angle=shelf["angle"])
            self.plinko_collector_slots(side)
            self.plinko_holes(width, height, side)
            self.plinko_exit_hole(width, height, side)

        edges = "efef" if side in ("A", "C") else "eFeF"
        self.rectangularWall(width, height, edges,
                             callback=[slots, None, None, None],
                             move=move, label=f"pillar {side}")

    def shelf_floor(self, shelf, move=None):
        label = f"shelf {shelf['index']} {shelf['side']}"
        landing = self._landing_length(shelf)
        entry_extra = shelf["entry_extra"]
        exit_extra = shelf["exit_extra"]

        if landing <= 0 and entry_extra <= 0 and exit_extra <= 0:
            self.rectangularWall(shelf["length"], self.track_width, "fefe",
                                 move=move, label=label)
            return

        total_top = entry_extra + shelf["length"] + landing + exit_extra
        overallwidth = total_top
        overallheight = self.track_width + 2 * self.edges["f"].spacing()

        if self.move(overallwidth, overallheight, move, before=True):
            return

        self.moveTo(0, self.edges["f"].margin())
        for length, edge in self._shelf_floor_segments(shelf):
            edge(length)
        self.corner(90)
        self.edges["e"](self.track_width)
        self.corner(90)
        self.edges["f"](total_top)
        self.corner(90)
        self.edges["e"](self.track_width)
        self.corner(90)
        self.move(overallwidth, overallheight, move, label=label)

    def outer_wall(self, shelf, move=None):
        label = f"outer wall {shelf['index']} {shelf['side']}"
        length = (shelf["entry_extra"] + shelf["length"] +
                  self._landing_length(shelf) + shelf["exit_extra"])
        self.rectangularWall(length,
                             self.wall_height, "Feee",
                             move=move, label=label)

    def lead_inner_walls(self, shelf, move=None):
        walls = []
        if shelf["entry_extra"] >= self.lead_wall_min_length:
            walls.append(("entry", shelf["entry_extra"]))
        if shelf["exit_extra"] >= self.lead_wall_min_length:
            walls.append(("exit", shelf["exit_extra"]))

        for name, length in walls:
            label = f"{name} inner wall {shelf['index']} {shelf['side']}"
            self.rectangularWall(length, self.wall_height, "Feee",
                                 move=move, label=label)

    def plinko_collector_ramp(self, move=None):
        collector = self._plinko_collector()
        if collector is None:
            return

        length = collector["length"]
        width = collector["width"]
        finger_start = collector["finger_start"]
        finger_length = collector["finger_length"]
        finger_end = length - finger_start - finger_length
        overallheight = width + 2 * self.edges["f"].spacing()

        if self.move(length, overallheight, move, before=True):
            return

        self.moveTo(0, self.edges["f"].margin())
        self.edges["e"](finger_start)
        self.edges["f"](finger_length)
        self.edges["e"](finger_end)
        self.corner(90)
        self.edges["e"](width)
        self.corner(90)
        self.edges["e"](finger_end)
        self.edges["f"](finger_length)
        self.edges["e"](finger_start)
        self.corner(90)
        self.edges["e"](width)
        self.corner(90)
        self.move(length, overallheight, move, label="plinko collector ramp")

    def render(self):
        if self.track_width <= 0:
            raise ValueError("track_width must be positive")
        if self.wall_height <= 0:
            raise ValueError("wall_height must be positive")
        if self.x_side_length <= 0 or self.y_side_length <= 0:
            raise ValueError("side lengths must be positive")
        if self.turns < 0:
            raise ValueError("turns must not be negative")
        if self.entry_height <= self.exit_height:
            raise ValueError("entry_height must be greater than exit_height")
        if self.corner_extension < 0:
            raise ValueError("corner_extension must not be negative")
        if self.shelf_drop < 0:
            raise ValueError("shelf_drop must not be negative")
        if self.entry_shelf_length < 0:
            raise ValueError("entry_shelf_length must not be negative")
        if self.exit_shelf_length < 0:
            raise ValueError("exit_shelf_length must not be negative")
        if self.lead_wall_min_length < 0:
            raise ValueError("lead_wall_min_length must not be negative")
        if self.plinko_hole_diameter <= 0:
            raise ValueError("plinko_hole_diameter must be positive")
        if self.plinko_pin_density <= self.plinko_hole_diameter:
            raise ValueError("plinko_pin_density must be larger than plinko_hole_diameter")

        shelves = self._shelves()
        if any(shelf["z1"] >= shelf["z0"] for shelf in shelves):
            raise ValueError("shelf_drop is too large for the requested heights and path")

        for side in self.SIDES:
            self.pillar_panel(side, move="right")

        for shelf in shelves:
            self.shelf_floor(shelf, move="up")
            self.outer_wall(shelf, move="up")
            self.lead_inner_walls(shelf, move="up")

        self.plinko_collector_ramp(move="up")
