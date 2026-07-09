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
            help="track floor width in mm")
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
            "--finger_joints", action="store", type=str, default="both",
            choices=["none", "start", "end", "both"],
            help="which open track ends get outward finger joints")

    def _track_poly(self, inner_radius, outer_radius, width):
        angle = -self.angle
        return [
            self.leg1, (angle, inner_radius),
            self.leg2, 90,
            width, 90,
            self.leg2, (-angle, outer_radius),
            self.leg1, 90,
            width, 90,
        ]

    def base_plate(self, move=None):
        base_width = self.track_width
        start_edge = "f" if self._finger_joint_at("start") else "e"
        end_edge = "f" if self._finger_joint_at("end") else "e"
        edge = "ff" + end_edge + "ff" + start_edge
        self.polygonWall(
            self._track_poly(self.turn_radius, self.turn_radius + base_width, base_width),
            edge=edge,
            move=move,
            label="base")

    def _finger_joint_at(self, side):
        return self.finger_joints in (side, "both")

    def wall_strip(self, radius, label="wall", move=None):
        bottom = self.edges["F"]
        top = self.edges["e"]
        left = self.edges["f"] if self._finger_joint_at("start") else self.edges["e"]
        right = self.edges["f"] if self._finger_joint_at("end") else self.edges["e"]

        arc = abs(math.radians(self.angle) * radius) / self.edges["X"].settings.stretch
        strip_length = self.leg1 + arc + self.leg2
        overallwidth = strip_length + left.spacing() + right.spacing()
        overallheight = self.wall_height + bottom.margin() + top.margin()

        if self.move(overallwidth, overallheight, move, before=True):
            return

        self.moveTo(left.spacing(), bottom.margin())
        bottom(self.leg1)
        self.edges["X"](arc, self.wall_height + bottom.startWidth())
        bottom(self.leg2)

        with self.saved_context():
            self.edgeCorner(bottom, right, 90)
            right(self.wall_height)
            self.edgeCorner(right, top, 90)
            top(strip_length)
            self.edgeCorner(top, left, 90)
            left(self.wall_height)
            self.edgeCorner(left, bottom, 90)
        self.ctx.stroke()

        if self.labels:
            self.text(label, self.leg1 / 2 - strip_length, self.wall_height / 2,
                      align="middle center", fontsize=4, color=boxes.Color.ANNOTATIONS)
            self.ctx.stroke()

        self.move(overallwidth, overallheight, move)

    def joiner_template(self, move=None):
        t = self.thickness
        base_width = self.track_width
        width = base_width
        height = self.wall_height

        if self.move(width, height, move, before=True):
            return

        # Three matching mortises: one for the floor, one for each side wall.
        self.fingerHolesAt(0, t / 2, base_width, angle=0)
        self.fingerHolesAt(t / 2, 0, self.wall_height)
        self.fingerHolesAt(base_width - t / 2, 0, self.wall_height)
        self.ctx.stroke()

        if self.labels:
            self.text("joiner", width / 2, height / 2,
                      align="middle center", fontsize=4, color=boxes.Color.ANNOTATIONS)
            self.ctx.stroke()

        self.move(width, height, move)

    def render(self):
        t = self.thickness
        if self.track_width <= 0:
            raise ValueError("track_width must be positive")
        if self.wall_height <= 0:
            raise ValueError("wall_height must be positive")
        if self.leg1 <= 0 or self.leg2 <= 0:
            raise ValueError("leg lengths must be positive")
        if self.turn_radius <= 0:
            raise ValueError("turn_radius must be positive")
        if abs(self.angle) <= 0:
            raise ValueError("angle must not be zero")

        self.base_plate(move="right")

        inner_radius = self.turn_radius
        outer_radius = self.turn_radius + self.track_width

        with self.saved_context():
            self.wall_strip(inner_radius, "inner wall")
        self.moveTo(0, self.wall_height + 4 * t)

        with self.saved_context():
            self.wall_strip(outer_radius, "outer wall")
        self.moveTo(0, self.wall_height + 4 * t)

        if self.finger_joints != "none":
            self.joiner_template(move="right")
