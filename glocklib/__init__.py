import discord


class Properties:

    def __init__(self):
        self._main_colour = discord.Colour(0x757575)

    @property
    def main_colour(self):
        """Main color used for most embeds"""
        return self._main_colour

    @main_colour.setter
    def main_colour(self, colour: int) -> None:
        self._main_colour = discord.Colour(colour)


properties = Properties()
