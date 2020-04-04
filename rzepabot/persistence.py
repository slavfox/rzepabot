# Copyright (c) 2020 Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from __future__ import annotations

from typing import Set
from dataclasses import dataclass

from peewee import (
    BooleanField,
    CharField,
    Check,
    DateField,
    DateTimeField,
    FixedCharField,
    ForeignKeyField,
    IntegerField,
    ManyToManyField,
    Model,
    SqliteDatabase,
    TextField,
    TimeField,
)

from rzepabot.config import DB_PATH, tznow_dt, tznow_t

db = SqliteDatabase(DB_PATH, pragmas={"foreign_keys": 1})

dt_default = lambda: tznow_dt().to_datetime_string()
t_default = tznow_t


@dataclass
class Fruit:
    name: str
    pl_name: str
    emoji: str
    aliases: Set[str]


FRUIT = {
    0: Fruit(
        "apple",
        "jabłka",
        "🍎",
        {"jabłko", "jabłka", "jablko", "jablka", "japko", "japka"},
    ),
    1: Fruit(
        "cherry", "wiśnie", "🍒", {"wiśnia", "wiśnie", "wisnia", "wisnie"}
    ),
    2: Fruit(
        "orange",
        "pomarańcze",
        "🍊",
        {"pomarańcza", "pomarańcze", "pomarancza", "pomarancze", "orange"},
    ),
    3: Fruit("pear", "gruszki", "🍐", {"gruszki", "gruszka", "pear"}),
    4: Fruit(
        "peach", "brzoskwinie", "🍑", {"brzoskwinie", "brzoskwinia", "peach"}
    ),
}

PERSONALITIES = [
    ("marudny", "maruda", "cranky"),
    ("biceps", "jock"),
    ("leniwy", "leń", "leniwa", "lazy"),
    ("normalna", "normalny", "normal"),
    ("ożywiona", "ożywiony", "ozywiona", "ozywiony", "peppy"),
    ("siostrzana", "sisterly", "siostra", "uchi"),
    ("próżny", "prozny", "próżna", "prozna", "smug"),
    ("przemądrzała", "przemądrzały", "przemadrzala", "przemadrzaly", "snooty"),
]

SPECIES = [
    ("ptak", "bird"),
    ("wiewiórka", "squirrel"),
    ("świnia", "pig"),
    ("goryl", "gorilla"),
    ("aligator", "alligator"),
    ("koala", "koala"),
    ("orzeł", "eagle"),
    ("mrówkojad", "anteater"),
    ("koteł", "kot", "kotek", "cat"),
    ("byk", "bull"),
    ("mysz", "mouse"),
    ("koń", "horse"),
    ("chomik", "hamster"),
    ("kangur", "kangaroo"),
    ("wilk", "wolf"),
    ("pingwin", "penguin"),
    ("kurczak", "chicken"),
    ("słoń", "elephant"),
    ("owca", "sheep"),
    ("jeleń", "deer"),
    ("tygrys", "tiger"),
    ("miś", "cub"),
    ("pieseł", "pies", "piesek", "dog"),
    ("niedźwiedź", "bear"),
    ("hipopotam", "hippo"),
    ("kaczka", "duck"),
    ("koza", "goat"),
    ("struś", "ostrich"),
    ("zając", "rabbit"),
    ("lew", "lion"),
    ("żaba", "frog"),
    ("małpa", "monkey"),
    ("nosorożec", "rhino"),
    ("ośmiornica", "octopus"),
    ("krowa", "cow"),
]

SPECIES_EMOJI = {
    "Ptak": "🐦",
    "Wiewiórka": "🐿",
    "Świnia": "🐖",
    "Goryl": "🦍",
    "Aligator": "🐊",
    "Koala": "🐨",
    "Orzeł": "🦅",
    "Mrówkojad": "🐜🍽",
    "Koteł": "🐈",
    "Byk": "🐂",
    "Mysz": "🐁",
    "Koń": "🐎",
    "Chomik": "🐹",
    "Kangur": "🦘",
    "Wilk": "🐺",
    "Pingwin": "🐧",
    "Kurczak": "🐔",
    "Słoń": "🐘",
    "Owca": "🐑",
    "Jeleń": "🦌",
    "Tygrys": "🐅",
    "Miś": "🧸",
    "Pieseł": "🐕",
    "Niedźwiedź": "🐻",
    "Hipopotam": "🦛",
    "Kaczka": "🦆",
    "Koza": "🐐",
    "Struś": "🦃",
    "Zając": "🐇",
    "Lew": "🦁",
    "Żaba": "🐸",
    "Małpa": "🐒",
    "Nosorożec": "🦏",
    "Ośmiornica": "🐙",
    "Krowa": "🐄",
}


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    discord_id = IntegerField(index=True, unique=True)


class Island(BaseModel):
    villager = ForeignKeyField(User, backref="island", unique=True)
    character_name = CharField(null=True, default=None)
    island_name = CharField(null=True, default=None)
    friend_code = FixedCharField(max_length=12, null=True, default=None)
    native_fruit = IntegerField(choices=list(FRUIT.keys()), null=True)


class Guild(BaseModel):
    discord_id = IntegerField(index=True, unique=True)


class GuildMembership(BaseModel):
    user = ForeignKeyField(User, backref="guilds")
    guild = ForeignKeyField(Guild, backref="users")

    class Meta:
        database = db
        indexes = ((("user", "guild"), True),)


class StalkPrice(BaseModel):
    timestamp = DateTimeField(default=dt_default)
    user = ForeignKeyField(User, backref="stalk_prices")
    price = IntegerField()
    user_time = TimeField(default=t_default)
    is_buy_price = BooleanField(default=False)


class Villager(BaseModel):
    name = CharField()
    catchphrase = CharField(null=True)
    birthday_month = IntegerField(
        constraints=[Check("birthday_month BETWEEN 1 AND 12")]
    )
    birthday_day = IntegerField(
        constraints=[Check("birthday_day BETWEEN 1 AND 31")]
    )
    personality = CharField()
    species = CharField()
    image_url = TextField()


class Residency(BaseModel):
    # Maps users to their villagers
    villager = ForeignKeyField(Villager, backref="villagers")
    acprofile = ForeignKeyField(Island, backref="islands")

    class Meta:
        database = db
        indexes = ((("villager", "acprofile"), True),)


class Critter(BaseModel):
    time_mask = IntegerField()
    month_mask = IntegerField()
    price = IntegerField(null=True, default=None)
    name = CharField(unique=True, index=True)
    location = CharField()
    is_fish = BooleanField()


class HotItem(BaseModel):
    user = ForeignKeyField(User, backref="hot_items")
    item = CharField()
    timestamp = DateTimeField(default=lambda: dt_default)


class DodoCode(BaseModel):
    user = ForeignKeyField(User, backref="dodocodes")
    guild = ForeignKeyField(Guild, backref="dodocodes")
    code = CharField()
    timestamp = DateTimeField(default=dt_default)
    comment = TextField(null=True)

    class Meta:
        database = db
        indexes = ((("user", "guild"), True),)


models = [
    User,
    Guild,
    GuildMembership,
    StalkPrice,
    Villager,
    Residency,
    Critter,
    HotItem,
    DodoCode,
    Island,
]

db.create_tables(models)


def get_user_and_guild(user_id, guild_id, dbcontext):
    user, _ = User.get_or_create(discord_id=user_id)
    guild, _ = Guild.get_or_create(discord_id=guild_id)
    guild_membership = GuildMembership.get_or_create(user=user, guild=guild)
    return user, guild


def cleanup():
    now = tznow_dt()
    day_ago = now.shift(days=-1)
    month_ago = now.shift(months=-1)
    with db:
        StalkPrice.delete().where(StalkPrice.timestamp < month_ago).execute()
        HotItem.delete().where(HotItem.timestamp < day_ago).execute()
        DodoCode.delete().where(DodoCode.timestamp < day_ago).execute()
