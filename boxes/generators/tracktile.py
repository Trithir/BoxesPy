import math

import boxes


class TrackTile(boxes.Boxes):
    """Open marble track tile with a configurable curved turn."""

    ui_group = "Misc"

    def __init__(self) -> None:
        boxes.Boxes.__init__(self)

        self.addSettingsArgs(boxes.edges.FingerJointSettings)
        self.addSettingsArgs(boxes.edges.FlexSettings)

        self.argparser.add_argument(
            "--track_width", action="store", type=float, default=20.0,
            help="clear inner track width in mm")
        self.argparser.add_argument(
            "--wall_height", action="store", type=float, default=20.0,
            help="height of the side walls in mm")
        self.argparser.add_argument(
            "--angle", action="store", type=float, default=90.0,
            help="turn angle in degrees")
        self.argparser.add_argument(
            "--leg1", action="store", type=float, default=60.0,
            help="straight length before the turn in mm")
        self.argparser.add_argument(
            "--leg2", action="store", type=float, default=60.0,
            help="straight length after the turn in mm")
        self.argparser.add_argument(
            "--turn_radius", action="store", type=float, default=25.0,
            help="inner radius of the curved turn in mm")
        self.argparser.add_argument(
            "--connectors", action="store", type=boxes.boolarg, default=True,
            help="add finger-joint ends to wall strips and a matching joiner template")
        self.argparser.add_argument(
            "--joiner_length", action="store", type=float, default=24.0,
            help="length of the loose end-joining template in mm")

    def _track_poly(self, inner_radius, outer_radius, width):
        return [
            self.leg1, (self.angle, inner_radius),
            self.leg2, 90,
            width, 90,
            self.leg2, (-self.angle, outer_radius),
            self.leg1, 90,
            width, 90,
        ]

    def base_plate(self, move=None):
        t = self.thickness
        base_width = self.track_width + 2 * t
        edge = "eeFeeF" if self.connectors else "e"
        self.polygonWall(
            self._track_poly(self.turn_radius, self.turn_radius + base_width, base_width),
            edge=edge,
            move=move,
            label="base")

    def wall_strip(self, radius, label="wall"):
        bottom = "F" if self.connectors else "e"
        body_height = self.wall_height - 2 * self.thickness
        self.polygonWalls(
            [self.leg1, (self.angle, radius), self.leg2, 0],
            body_height,
            bottom=bottom,
            top="e",
            symmetrical=False)
        self.ctx.stroke()
        if self.labels:
            strip_length = self.leg1 + self.leg2 + abs(math.radians(self.angle) * radius)
            self.text(label, strip_length / 2, self.wall_height / 2,
                      align="middle center", fontsize=4)
            self.ctx.stroke()

    def joiner_template(self, move=None):
        t = self.thickness
        base_width = self.track_width + 2 * t
        width = base_width + 2 * t
        height = max(self.joiner_length, self.wall_height + 2 * t)

        if self.move(width, height, move, before=True):
            return

        self.rectangularWall(width, height, "eeee", label="joiner")

        # Three matching mortises: one for the floor, one for each side wall.
        self.fingerHolesAt(t, t / 2, base_width, angle=0)
        self.fingerHolesAt(t / 2, (height - self.wall_height) / 2, self.wall_height)
        self.fingerHolesAt(width - t / 2, (height - self.wall_height) / 2, self.wall_height)
        self.ctx.stroke()

        self.move(width, height, move)

    def render(self):
        t = self.thickness
        if self.track_width <= 0:
            raise ValueError("track_width must be positive")
        if self.wall_height <= 0:
            raise ValueError("wall_height must be positive")
        if self.wall_height <= 2 * t:
            raise ValueError("wall_height must be more than two material thicknesses")
        if self.leg1 <= 0 or self.leg2 <= 0:
            raise ValueError("leg lengths must be positive")
        if self.turn_radius <= 0:
            raise ValueError("turn_radius must be positive")
        if abs(self.angle) <= 0:
            raise ValueError("angle must not be zero")

        self.base_plate(move="right")

        inner_radius = self.turn_radius + 0.5 * t
        outer_radius = self.turn_radius + self.track_width + 1.5 * t

        with self.saved_context():
            self.wall_strip(outer_radius, "outer wall")
        self.moveTo(0, self.wall_height + 4 * t)

        with self.saved_context():
            self.wall_strip(inner_radius, "inner wall")
        self.moveTo(0, self.wall_height + 4 * t)

        if self.connectors:
            self.joiner_template(move="right")
