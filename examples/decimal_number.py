"""Live numeric readout backed by Geometry Nodes string curves."""

from bmath import DecimalNumber, Scene, Style


class DecimalNumberExample(Scene):
    def construct(self):
        number = DecimalNumber(0, decimals=2, font_size=0.5, style=Style(color=(1, 1, 1, 1)))
        number.key_value(1, 0).key_value(31, 0.65).key_value(61, -0.35).key_value(91, 0)
        self.add(number)
        self.wait(3)
