# Copyright (c) 2020 Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from __future__ import annotations

from calendar import month_name
from urllib import request

from lxml import html

basepath = (
    "https://animalcrossing.fandom.com/wiki/Villager_list_(New_Horizons)"
)

months = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

personality_to_pl = {
    "peppy": "Ożywiona",
    "sisterly": "Siostrzana",
    "normal": "Normalna",
    "snooty": "Przemądrzała",
    "cranky": "Marudny",
    "jock": "Biceps",
    "smug": "Próżny",
    "lazy": "Leniwy",
}

species_to_pl = {
    "bird": "Ptak",
    "squirrel": "Wiewiórka",
    "pig": "Świnia",
    "gorilla": "Goryl",
    "alligator": "Aligator",
    "koala": "Koala",
    "eagle": "Orzeł",
    "anteater": "Mrówkojad",
    "cat": "Koteł",
    "bull": "Byk",
    "mouse": "Mysz",
    "horse": "Koń",
    "hamster": "Chomik",
    "kangaroo": "Kangur",
    "wolf": "Wilk",
    "penguin": "Pingwin",
    "chicken": "Kurczak",
    "elephant": "Słoń",
    "sheep": "Owca",
    "deer": "Jeleń",
    "tiger": "Tygrys",
    "cub": "Miś",
    "dog": "Pieseł",
    "bear": "Niedźwiedź",
    "hippo": "Hipopotam",
    "duck": "Kaczka",
    "goat": "Koza",
    "ostrich": "Struś",
    "rabbit": "Zając",
    "lion": "Lew",
    "frog": "Żaba",
    "monkey": "Małpa",
    "rhino": "Nosorożec",
    "octopus": "Ośmiornica",
    "cow": "Krowa",
}


def get_villager_rows():
    with request.urlopen(basepath) as resp:
        villagerlist_body = resp.read()
    tree = html.fromstring(villagerlist_body)
    villager_rows = tree.xpath('//table[//a[@title="Villagers"]]//table/tr')
    return villager_rows


def get_villagers():
    rows = get_villager_rows()
    villagers = []
    for row in rows:
        tds = row.xpath("./td")
        try:
            name, image, personality, species, birthday, catchphrase = tds
        except ValueError:
            continue

        name = name.xpath(".//a")[0].text.strip()
        image = image.xpath(".//a")[0].attrib["href"]

        personality = personality.xpath(".//a")[0].text.split()[-1].lower()
        personality = personality_to_pl[personality]

        species = species.xpath(".//a")[0].text.strip().lower()
        species = species_to_pl[species]

        month, day = birthday.text.strip().split()
        birthday = (months[month.lower()], int(day))

        catchphrase = catchphrase.xpath(".//i")[0].text.strip().strip('"')
        villagers.append(
            (name, image, personality, species, birthday, catchphrase)
        )
    return villagers


if __name__ == "__main__":
    from pprint import pformat

    with open("villagers.py", "w") as f:
        s = "villagers = " + pformat(get_villagers())
        f.write(s)
