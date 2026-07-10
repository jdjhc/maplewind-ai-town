"""
Original character portraits for Maplewind Hollow — flat vector style,
drawn entirely in code (SVG). 100% original artwork: no external assets,
no copyright concerns. Each villager has six moods; the NPC's @@STATE@@
block picks the mood, so the portrait reacts to the conversation.
"""

MOODS = ("neutral", "happy", "sad", "angry", "shy", "surprised")

INK = "#3a2e28"


def _stroke(d, w=3, color=INK):
    return (f'<path d="{d}" stroke="{color}" stroke-width="{w}" '
            f'fill="none" stroke-linecap="round"/>')


# --------------------------------------------------------------------------
# Faces — shared geometry, swapped per mood
# --------------------------------------------------------------------------
def _face(mood, blush="#e8927c"):
    p = [_stroke("M100,120 Q102,124 100,127", 2)]  # nose
    if mood == "happy":
        p += [_stroke("M74,96 Q83,92 91,95"), _stroke("M109,95 Q117,92 126,96")]
        p += [_stroke("M77,113 Q84,105 91,113", 3.5),
              _stroke("M109,113 Q116,105 123,113", 3.5)]
        p += ['<path d="M89,132 Q100,146 111,132 Q100,139 89,132" fill="#a34a38"/>']
        p += [f'<ellipse cx="70" cy="126" rx="7" ry="4" fill="{blush}" opacity="0.55"/>',
              f'<ellipse cx="130" cy="126" rx="7" ry="4" fill="{blush}" opacity="0.55"/>']
    elif mood == "sad":
        p += [_stroke("M75,103 Q85,96 91,97"), _stroke("M109,97 Q115,96 125,103")]
        p += [f'<ellipse cx="84" cy="114" rx="3.4" ry="4.2" fill="{INK}"/>',
              f'<ellipse cx="116" cy="114" rx="3.4" ry="4.2" fill="{INK}"/>']
        p += [_stroke("M92,140 Q100,134 108,140")]
        p += ['<ellipse cx="77" cy="125" rx="2.5" ry="4" fill="#9ecbe8" opacity="0.9"/>']
    elif mood == "angry":
        p += [_stroke("M75,94 L91,102"), _stroke("M109,102 L125,94")]
        p += [f'<ellipse cx="84" cy="113" rx="3.6" ry="3.2" fill="{INK}"/>',
              f'<ellipse cx="116" cy="113" rx="3.6" ry="3.2" fill="{INK}"/>']
        p += [_stroke("M91,140 Q100,134 109,140")]
        p += [_stroke("M130,86 L138,78 M134,90 L142,84", 2.5, "#c0392b")]
    elif mood == "shy":
        p += [_stroke("M74,99 Q83,96 91,99"), _stroke("M109,99 Q117,96 126,99")]
        p += [f'<ellipse cx="87" cy="113" rx="3" ry="4.4" fill="{INK}"/>',
              f'<ellipse cx="119" cy="113" rx="3" ry="4.4" fill="{INK}"/>']
        p += [f'<ellipse cx="71" cy="124" rx="8.5" ry="5" fill="{blush}" opacity="0.7"/>',
              f'<ellipse cx="129" cy="124" rx="8.5" ry="5" fill="{blush}" opacity="0.7"/>']
        p += [_stroke("M92,137 Q96,134 100,137 Q104,140 108,137", 2.5)]
    elif mood == "surprised":
        p += [_stroke("M74,92 Q83,88 91,91"), _stroke("M109,91 Q117,88 126,92")]
        p += [f'<circle cx="84" cy="113" r="7" fill="#fff" stroke="{INK}" stroke-width="2.5"/>',
              f'<circle cx="116" cy="113" r="7" fill="#fff" stroke="{INK}" stroke-width="2.5"/>',
              f'<circle cx="84" cy="114" r="2.6" fill="{INK}"/>',
              f'<circle cx="116" cy="114" r="2.6" fill="{INK}"/>']
        p += ['<ellipse cx="100" cy="140" rx="5" ry="7" fill="#7c4234"/>']
    else:  # neutral
        p += [_stroke("M74,99 Q83,95 91,98"), _stroke("M109,98 Q117,95 126,99")]
        p += [f'<ellipse cx="84" cy="113" rx="3.6" ry="5" fill="{INK}"/>',
              f'<ellipse cx="116" cy="113" rx="3.6" ry="5" fill="{INK}"/>']
        p += [_stroke("M92,136 Q100,141 108,136")]
    return "".join(p)


# --------------------------------------------------------------------------
# Bodies — one original design per villager
# --------------------------------------------------------------------------
def _marla(face):
    skin, hair = "#f2c9a0", "#8a5a33"
    return (
        f'<circle cx="134" cy="70" r="15" fill="{hair}"/>'                      # bun
        f'<rect x="89" y="136" width="22" height="52" rx="9" fill="{skin}"/>'   # neck
        f'<path d="M38,260 Q44,186 100,182 Q156,186 162,260 Z" fill="#6a8f5f"/>'  # dress
        f'<path d="M70,260 Q72,208 100,205 Q128,208 130,260 Z" fill="#f2e8d8"/>'  # apron
        f'<path d="M84,186 Q100,196 116,186 L112,180 Q100,187 88,180 Z" fill="#f2e8d8"/>'  # collar
        f'<ellipse cx="100" cy="108" rx="40" ry="42" fill="{skin}"/>'
        f'<path d="M60,104 Q56,58 100,55 Q144,58 140,104 Q132,76 100,78 '
        f'Q68,76 60,104 Z" fill="{hair}"/>'
        + face
    )


def _odell(face):
    skin, hair = "#d9a577", "#3a3230"
    return (
        f'<rect x="88" y="136" width="24" height="50" rx="9" fill="{skin}"/>'
        f'<path d="M28,260 Q36,182 100,178 Q164,182 172,260 Z" fill="#4a4a52"/>'   # shirt
        f'<path d="M62,260 Q64,204 100,200 Q136,204 138,260 Z" fill="#7a5233"/>'   # leather apron
        f'<path d="M70,200 L64,236 M130,200 L136,236" stroke="#5c3d24" '
        f'stroke-width="4" fill="none"/>'                                          # straps
        f'<ellipse cx="100" cy="108" rx="40" ry="42" fill="{skin}"/>'
        f'<path d="M72,130 Q100,160 128,130 Q100,148 72,130 Z" fill="{INK}" '
        f'opacity="0.14"/>'                                                        # stubble
        f'<path d="M60,102 Q56,56 100,52 Q144,56 140,102 L133,82 L125,94 L117,78 '
        f'L107,92 L97,76 L87,92 L77,80 L69,96 Z" fill="{hair}"/>'                  # messy hair
        + face
    )


def _wren(face):
    skin, hair = "#f5d0ae", "#7c5cbf"
    return (
        f'<path d="M138,66 Q170,58 174,96 Q162,122 146,102 Q152,82 138,66 Z" '
        f'fill="{hair}"/>'                                                         # ponytail
        f'<path d="M58,95 Q50,150 62,186 Q74,158 66,108 Z" fill="{hair}"/>'        # side strand L
        f'<path d="M142,95 Q150,148 138,182 Q128,156 134,108 Z" fill="{hair}"/>'   # side strand R
        f'<rect x="90" y="136" width="20" height="52" rx="9" fill="{skin}"/>'
        f'<path d="M46,260 Q52,190 100,186 Q148,190 154,260 Z" fill="#3f8f8a"/>'   # tunic
        f'<path d="M72,190 Q100,176 128,190 Q100,202 72,190 Z" fill="#e08a3c"/>'   # scarf
        f'<ellipse cx="100" cy="108" rx="40" ry="42" fill="{skin}"/>'
        f'<path d="M60,102 Q56,56 100,54 Q144,56 140,102 Q134,72 116,84 '
        f'Q108,68 94,82 Q78,70 60,102 Z" fill="{hair}"/>'
        f'<rect x="118" y="72" width="12" height="4" rx="2" fill="#e8c23c" '
        f'transform="rotate(24 124 74)"/>'                                         # hairpin
        + face
    )


_BODIES = {"marla": _marla, "odell": _odell, "wren": _wren}


def sprite_svg(npc_id, mood="neutral"):
    """Return a self-contained SVG portrait for this villager in this mood."""
    if mood not in MOODS:
        mood = "neutral"
    body = _BODIES[npc_id](_face(mood))
    return (f'<svg viewBox="0 0 200 260" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="{npc_id} ({mood})">{body}</svg>')
