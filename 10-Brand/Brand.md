---
type: brand
id: nightshift
title: "Brand"
name: "NIGHT SHIFT SUPPLY"

# ─────────────────────────────────────────────────────────────────────
# This file is the root of the graph. Every prompt the room compiles
# opens with the `look` block below, verbatim, in this order.
# Changing a line here changes every clip made after it. That is the point,
# and it is also the risk — treat edits as a brand decision, not a tweak.
# ─────────────────────────────────────────────────────────────────────

look:
  aspect: "9:16 vertical"
  fps: "24 fps"
  film: >
    Shot on expired 16mm stock, halation blooming around every light source,
    grain visible in the shadows.
  lens: >
    Wide 28mm at chest height, slight barrel distortion at the edges of frame,
    focus that hunts for a beat before it settles.
  lighting: >
    Lit only by what is in the room — fluorescent tubes, a cooler's glow, a
    phone screen. One source dominant, everything else falling to black.
  palette: >
    Sodium-vapor amber against cold fluorescent green, with a single object in
    the frame carrying saturated red.
  grade: >
    Crushed blacks, blown highlights left blown, no lift in the shadows.
  texture: >
    Fingerprints on glass, condensation, dust in the light, surfaces that have
    been touched by a lot of people.
  default_camera: >
    Locked-off wide, no movement, the frame waiting for someone to walk into it.

audio:
  bed: >
    Fluorescent hum, a cooler compressor cycling, distant traffic through glass.

# Rendered as the AVOID line on every prompt. Absolutes only — anything
# conditional belongs on the entity or shot that conditions it.
negative:
  - drone or aerial shots
  - lens flare added in post
  - orchestral or swelling score
  - anyone smiling directly at camera
  - daylight exteriors
  - text or logos rendered in frame
  - slow motion
  - shallow depth of field on wide shots
---

# NIGHT SHIFT SUPPLY

> A 24-hour store that has never once been closed, and the people who are
> awake at the hours it serves.

## The one-line brand

Everything happens between 1am and 5am, indoors, under someone else's lighting.

## What the brand is actually selling

Recognition. The audience has been in this room at this hour. The clips do not
explain the feeling; they just get the room right and let the feeling arrive.

## The three rules

1. **Never leave the hour.** No daylight, no morning, no "the next day."
2. **The camera is a bystander,** not a participant. It does not chase.
3. **Nobody performs for it.** The moment the frame is acknowledged, the brand
   is broken.

## The system around this file

- [[Voice-and-Tone]] — how the writing sounds
- [[Visual-System]] — why the `look` block reads the way it does
- [[Audio-System]] — the bed, and what's allowed on top of it
- [[Do-Not-Render]] — the negatives, with reasons attached
