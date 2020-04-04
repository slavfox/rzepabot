# Copyright (c) 2020 Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from __future__ import annotations

from rzepabot.data import bugs, fish, villagers
from rzepabot.persistence import Critter, Villager, db


def update_villagers():
    created = 0
    updated = 0
    for row in villagers:
        name, image_url, personality, species, birthday, catchphrase = row
        bm, bd = birthday
        villager, was_created = Villager.get_or_create(
            name=name,
            defaults={
                "catchphrase": catchphrase,
                "birthday_month": bm,
                "birthday_day": bd,
                "species": species,
                "personality": personality,
                "image_url": image_url,
            },
        )
        created += was_created
        villager.catchphrase = catchphrase
        villager.birthday_month = bm
        villager.birthday_day = bd
        villager.species = species
        villager.personality = personality
        villager.image_url = image_url
        updated += villager.save()
    return created, updated


def update_critter(row, is_fish):
    name, price, location, hour_bitmask, month_bitmask = row
    critter, created = Critter.get_or_create(
        name=name,
        defaults={
            "price": price,
            "time_mask": hour_bitmask,
            "month_mask": month_bitmask,
            "location": location,
            "is_fish": is_fish,
        },
    )
    critter.price = price
    critter.time_mask = hour_bitmask
    critter.month_mask = month_bitmask
    critter.location = location
    critter.is_fish = is_fish
    updated = critter.save()
    return created, updated


def update_critters():
    created = 0
    updated = 0
    for row in fish:
        c, u = update_critter(row, True)
        created += c
        updated += u
    for row in bugs:
        c, u = update_critter(row, False)
        created += c
        updated += u
    return created, updated


if __name__ == "__main__":
    print("Updating villager table.")
    created, updated = update_villagers()
    print(f"Done! {created}/{updated} created.\n")
    print("Updating critters table.")
    created, updated = update_critters()
    print(f"Done! {created}/{updated} created.\n")
    print("Done.")
