---
type: network
id: network
title: "Network"
name: "THE NETWORK"

# ─────────────────────────────────────────────────────────────────────
# The top of the inheritance chain. Everything here binds every channel.
#
# The test for putting something in this file: would it still be true if we
# launched a channel about competitive dog grooming tomorrow? If not, it is a
# channel's business, not the network's. This file should stay short. A network
# that over-specifies produces channels that look like each other, which is the
# one thing a network cannot afford.
# ─────────────────────────────────────────────────────────────────────

# Delivery format. Channels inherit these and rarely override them.
look:
  aspect: "9:16 vertical"
  fps: "24 fps"

format:
  clip_seconds: 10
  max_clip_seconds: 12
  clips_per_post: [3, 5]
  max_post_seconds: 60
  # A channel that hasn't answered these has no visual identity yet, and lint
  # will refuse to let it compile.
  channels_must_define: [film, lens, lighting, palette, grade]

# True of every clip on every channel, forever. Merged into the AVOID line
# ahead of the channel's own negatives.
negative:
  - text, captions, subtitles, watermarks or logos rendered in frame
  - real-world brand names or trademarks
  - recognizable public figures
  - children
---

# The Network

A set of channels that share a production system and a delivery format, and
share nothing else on screen.

## What the network owns

1. **The format.** Vertical, ~10-second clips, 3–5 to a post. Every channel
   works in the same unit, which is what lets one room staff all of them.
2. **The method.** Locks, inheritance, and the compiler. See
   [[How-This-Vault-Works]].
3. **The floor.** The `negative` list above — the things no channel renders,
   for legal and platform reasons rather than taste ones.
4. **The seam.** One handoff contract for every channel, so the video
   engineering side integrates once. See [[Handoff-Contract]].

## What the network does not own

Look, voice, cast, tone, subject, cadence. Those are the channel's, and the
network should resist the urge to harmonize them. Two channels that feel like
the same account are one account with half the reach.

## Channels

| Channel | Handle | The one-line |
|---|---|---|
| [[Night Shift Supply]] | @nightshiftsupply | Nothing happens in a 24-hour store, slowly. |

## Adding a channel

```
tools/roomctl.py new channel "Channel Name"
```

That scaffolds the folder, the doctrine notes, and empty canon. A channel is
ready to compile once it has answered `channels_must_define` above and has one
character with a `lock`.

## Crossovers

A channel may cast another channel's character. The compiler allows it and
flags it as a warning at build time, so it is never accidental. Before you do
it, be sure the two channels have been established separately long enough that
the crossing means something — a network's advantage is the crossover, and it
is spent the first time it's used.
