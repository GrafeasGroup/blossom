import random

from django import template

register = template.Library()


@register.simple_tag
def generate_engineering_footer():
    return random.choice(
        [
            "Around here, however, we don't look backwards for very long."
            " We keep moving forward, opening up new doors and doing new things…"
            " and curiosity keeps leading us down new paths. ~ Walt Disney",
            "Building the tools for a better tomorrow!",
            # haddaway
            "What is love? Baby don't hurt me - don't hurt me, no more",
            # portal 2
            "Science isn't about WHY, it's about WHY NOT!",
            "Space. Space. I'm in space. SPAAAAAAACE!",
            "When life gives you lemons, don't make lemonade. Make life take the"
            " lemons back! Get mad! I don't want your damn lemons! What am I supposed"
            " to do with these?! Demand to see life's manager! Make life rue the day"
            " it thought it could give Cave Johnson lemons! Do you know who I am?!"
            " I'm the man who's gonna burn your house down! With the lemons!"
            " I'm gonna get my engineers to invent a combustible lemon that burns"
            " your house down!",
            # cinderella
            "Even miracles take a little time.",
            "Just because it's what's done, doesn't mean it's what should be done.",
            # alice in wonderland
            "I give myself very good advice, but I very seldom follow it.",
            # aladdin
            "Do not be followed by its commonplace appearance. Like so many things,"
            " it is not what is outside, but what is inside that counts.",
            # the incredibles
            "I never look back, darling! It distracts me from the now.",
            # finding nemo
            "just keep swimming, just keep swimming...",
            # oregon trail
            "You have died of dysentery.",
            # duke nukem 3d
            "It's time to kick ass and chew bubblegum... and I'm all outta gum.",
            # star fox 64
            "Do a barrel roll!",
            # legend of zelda
            "It’s dangerous to go alone, take this.",
            # super mario bros
            "Thank you Mario! But our Princess is in another castle!",
            # diablo II
            "Stay awhile, and listen!",
            # ocarina of time
            "Hey! Listen!",
        ]
    )
