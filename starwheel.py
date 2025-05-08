#!/usr/bin/python3
# starwheel.py
# -*- coding: utf-8 -*-
#
# The python script in this file makes the various parts of a model planisphere.
#
# Copyright (C) 2014-2024 Dominic Ford <https://dcford.org.uk/>
#
# This code is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# You should have received a copy of the GNU General Public License along with
# this file; if not, write to the Free Software Foundation, Inc., 51 Franklin
# Street, Fifth Floor, Boston, MA  02110-1301, USA

"""
Render the star wheel for the planisphere.
"""

import re
from math import pi, sin, cos, atan2, hypot
from numpy import arange
from typing import Dict, Tuple
import calendar
from bright_stars_process import fetch_bright_star_list
from constants import unit_deg, unit_rev, unit_mm, unit_cm, r_1, r_gap, central_hole_size, radius
from graphics_context import BaseComponent, GraphicsContext
from settings import fetch_command_line_arguments
from text import text
from themes import themes

# ——— Nakṣatra settings ———
NAKSHATRAS = [
    "Aśvini", "Bharanī", "Kṛttikā", "Rohiṇī", "Mṛgaśīrṣā",
    "Ārdrā", "Punarvasu", "Puṣya", "Āśleṣā", "Maghā",
    "Pūrva Phālgunī", "Uttara Phālgunī", "Hasta", "Chitrā",
    "Svātī", "Viśākhā", "Anurādhā", "Jyeṣṭhā", "Mūla",
    "Pūrva Aṣāḍhā", "Uttara Aṣāḍhā", "Śrāvaṇa", "Dhaniṣṭhā",
    "Śatabhīṣā", "Pūrva Bhādrapadā", "Uttara Bhādrapadā", "Revati"
]
ANGLE_STEP_NAK = 360.0 / len(NAKSHATRAS)   # ≈ 13.333° per nakṣatra


class StarWheel(BaseComponent):
    """
    Render the star wheel for the planisphere.
    """

    def default_filename(self) -> str:
        return "star_wheel"

    def bounding_box(self, settings: dict) -> Dict[str, float]:
        return {
            'x_min': -r_1 - 4 * unit_mm,
            'x_max': r_1 + 4 * unit_mm,
            'y_min': -r_1 - 4 * unit_mm,
            'y_max': r_1 + 4 * unit_mm
        }

    def do_rendering(self, settings: dict, context: GraphicsContext) -> None:
        is_southern: bool = settings['latitude'] < 0
        language: str = settings['language']
        latitude: float = abs(settings['latitude'])
        theme: Dict[str, Tuple[float, float, float, float]] = themes[settings['theme']]

        context.set_font_size(1.2)

        # Radii
        r_2: float = r_1 - r_gap
        r_3: float = r_1 * 0.1 + r_2 * 0.9
        r_4: float = r_1 * 0.2 + r_2 * 0.8
        r_5: float = r_1
        r_6: float = r_1 * 0.4 + r_2 * 0.6

        # Shade background
        shading_inner_radius: float = r_1 * 0.55 + r_2 * 0.45
        context.begin_path()
        context.circle(centre_x=0, centre_y=0, radius=r_1)
        context.circle(centre_x=0, centre_y=0, radius=shading_inner_radius)
        context.fill(color=theme['shading'])

        # Outer edge
        context.begin_path()
        context.circle(centre_x=0, centre_y=0, radius=r_1)
        context.fill(color=theme['background'])

        # Central hole
        context.begin_sub_path()
        context.circle(centre_x=0, centre_y=0, radius=central_hole_size)
        context.stroke(color=theme['edge'])

        # Clip to circle
        context.clip()

        # Declination circles
        for dec in arange(-80, 85, 15):
            r: float = radius(dec=dec, latitude=latitude)
            if r > r_2:
                continue
            context.begin_path()
            context.circle(centre_x=0, centre_y=0, radius=r)
            context.stroke(color=theme['grid'])

        # Constellation stick figures
        with open("raw_data/constellation_stick_figures.dat", "rt") as f_in:
            for line in f_in:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                name, ra1_str, dec1_str, ra2_str, dec2_str = line.split()
                dec1, ra1 = float(dec1_str), float(ra1_str)
                dec2, ra2 = float(dec2_str), float(ra2_str)
                if is_southern:
                    dec1, ra1, dec2, ra2 = -dec1, -ra1, -dec2, -ra2
                r1 = radius(dec=dec1, latitude=latitude)
                r2 = radius(dec=dec2, latitude=latitude)
                if r1 > r_2 or r2 > r_2 or hypot(r2* cos(ra2*unit_deg)-r1*cos(ra1*unit_deg),
                                                   r2*sin(ra2*unit_deg)-r1*sin(ra1*unit_deg))>4*unit_cm:
                    continue
                p1 = (-r1 * cos(ra1 * unit_deg), -r1 * sin(ra1 * unit_deg))
                p2 = (-r2 * cos(ra2 * unit_deg), -r2 * sin(ra2 * unit_deg))
                context.begin_path()
                context.move_to(x=p1[0], y=p1[1])
                context.line_to(x=p2[0], y=p2[1])
                context.stroke(color=theme['stick'], line_width=1, dotted=True)

        # Bright stars
        for star in fetch_bright_star_list()['stars'].values():
            ra, dec, mag = star[:3]
            if mag == '-' or float(mag) > 4.0:
                continue
            ra, dec = float(ra), float(dec)
            if is_southern:
                ra, dec = -ra, -dec
            r = radius(dec=dec, latitude=latitude)
            if r > r_2:
                continue
            context.begin_path()
            context.circle(centre_x=-r * cos(ra * unit_deg), centre_y=-r * sin(ra * unit_deg),
                           radius=0.18 * unit_mm * (5 - mag))
            context.fill(color=theme['star'])

        # Constellation names
        context.set_font_size(0.7)
        context.set_color(theme['constellation'])
        with open("raw_data/constellation_names.dat") as f_in:
            for line in f_in:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                name, ra_str, dec_str = line.split()[:3]
                if name in text[language]['constellation_translations']:
                    name = text[language]['constellation_translations'][name]
                ra, dec = float(ra_str)*360/24, float(dec_str)
                if is_southern:
                    ra, dec = -ra, -dec
                r = radius(dec=dec, latitude=latitude)
                if r <= r_2:
                    p = (-r * cos(ra*unit_deg), -r * sin(ra*unit_deg))
                    a = atan2(p[0], p[1])
                    context.text(text=name.replace('_',' '), x=p[0], y=p[1], h_align=0, v_align=0, gap=0,
                                 rotation=unit_rev/2 - a)

        # Hemisphere direction
        s: int = -1 if not is_southern else 1

        def theta2014(d: float) -> float:
            return (d - calendar.julian_day(year=2014, month=3, day=20,
                                             hour=16, minute=55, sec=0)) / 365.25 * unit_rev

        # ——— Nakṣatra scale around the date rim ———
        context.set_font_size(1.8)
        context.set_color(theme['date'])

        radius_label = r_1 * 0.75 + r_2 * 0.25
        tick_outer   = r_1
        tick_inner   = r_1 - 0.15 * unit_cm

        for i, nak in enumerate(NAKSHATRAS):
            base_theta = s * theta2014(calendar.julian_day(year=2014, month=3, day=20,
                                                           hour=16, minute=55, sec=0)) / unit_deg
            theta = (base_theta + i * ANGLE_STEP_NAK) * unit_deg

            context.begin_path()
            context.move_to(x=tick_outer * cos(theta), y=-tick_outer * sin(theta))
            context.line_to(x=tick_inner * cos(theta), y=-tick_inner * sin(theta))
            context.stroke(line_width=1, dotted=False)

            mid_theta = theta + (ANGLE_STEP_NAK/2) * unit_deg
            x_lab = radius_label * cos(mid_theta)
            y_lab = -radius_label * sin(mid_theta)
            context.text(text=nak, x=x_lab, y=y_lab, h_align=0, v_align=0, gap=0,
                         rotation=unit_rev/2 - mid_theta)

        # dividing line
        context.begin_path()
        context.circle(centre_x=0, centre_y=0, radius=r_2)
        context.stroke(color=theme['date'], line_width=1, dotted=False)


# Run as script
if __name__ == "__main__":
    args = fetch_command_line_arguments(default_filename=StarWheel().default_filename())
    StarWheel(settings={
        'latitude': args['latitude'],
        'language': 'en',
        'theme': args['theme'],
    }).render_to_file(
        filename=args['filename'],
        img_format=args['img_format'],
    )
