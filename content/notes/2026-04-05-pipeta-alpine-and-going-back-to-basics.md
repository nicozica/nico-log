---
note_id: 2026-04-05-alpine-linux-pipeta
lang: en
title: Pipeta, Alpine, and the Charm of Going Back to Basics
date: 2026-04-05
tags:
- alpine-linux
- raspberry-pi-zero-2w
- python
- sqlite
- rss
- weather
- argensonix-labs
slug: pipeta-alpine-and-going-back-to-basics
summary: These days I started using Pipeta, a Raspberry Pi Zero 2 W meant purely as
  an experimentation playground. The idea was to use it to learn without pressure,
  with small scripts, weather, RSS, SQLite, and the sort of minimal tests that do
  not change the world but teach a lot.
---

These days I found myself in an interesting situation: having a Raspberry Pi Zero 2 W turned on in Buenos Aires, running Alpine Linux, while I am far from home and do not need anything urgent from that machine. In other words, the ideal context to start trying things without guilt.

The machine is called **Pipeta** and the name fits, because that is exactly how I want to use it: as a pure sandbox to experiment, learn, and make mistakes without turning every attempt into a service, an obligation, or another piece of infrastructure to maintain.

<figure class="note-photo">
  <img src="/assets/img/notes/pipeta-alpine-linux-20260407.webp" alt="Pipeta, a Raspberry Pi Zero 2 W turned on over a dark surface" loading="lazy" />
  <figcaption>Pipeta, ready to keep doing small, manual, and pretty calm experiments.</figcaption>
</figure>

### The charm of not doing something important

A lot of the time we learn technology by trying to solve something big too quickly. Stand up a server, expose a subdomain, automate half the planet, or turn a script into a system before its time. This time I wanted the opposite.

The rule was pretty simple: no production, no availability, and no leaving things running just because. Only small, manual, local things that were harmless enough to play with without pressure.

### The first experiments

I started with two very simple Python scripts. One to compare weather between cities and another to read headlines from RSS feeds. They were not especially sophisticated tools, but that was exactly the point.

What was interesting was understanding more clearly what each layer does: Python as the language, `requests` to fetch data, `feedparser` to read RSS, a weather API, and then a bit of my own logic to organize everything and present it more clearly. There was no strange magic behind it, just data, simple rules, and some judgment to show it well.

Saying it like that makes it sound obvious, but seeing it work in a remote terminal, on such a tiny machine, had a lot of charm.

### From script to little program

Then came the next step, which was to put those pieces together into a sort of tiny interactive lab. That is how **Pipeta Lab** appeared, a terminal menu script that lets me compare cities, read headlines, and combine both things in a simple observatory-style view.

It is still small, manual, and very light. And that is exactly what interested me the most: not building an app, a dashboard, or a platform, but a little program that feels alive enough to help me understand better how the pieces fit together.

### When SQLite showed up

The most interesting jump so far was adding **SQLite**. Not because I needed it urgently, but because it seemed like a good way to touch a database without bringing in too much complexity.

Until then, data appeared on screen and disappeared there. With SQLite something else showed up: persistence. The program no longer just queried and displayed, it could also save one run and read it back later. That made a structure that is always there, even if you do not always see it, much clearer: input, processing, persistence, and output.

In other words, the script stopped being only a live query and started looking a bit more like a system, even if it was still a very small experiment.

### What I liked most

I think the best part of this little adventure was not Alpine, or Python, or SQLite separately. The best part was going back to something very basic and very healthy: learning without the pressure to publish, automate, or turn everything into “infrastructure” right away.

Open a terminal, write something, break an indentation, wrestle with a capricious API, understand why a city is missing, and save three rows in a database may sound tiny, but that scale is exactly where it becomes easier to understand what is going on.

### What may come next

For now I want to keep Pipeta in that place: pure sandbox, lab, and test box. Maybe later one of these little things moves to another machine or ends up online, but I would rather have that happen later, if it makes sense, and not as the starting point.

It is good to remember that not every project has to be born as infrastructure. Sometimes a tiny idea, a terminal, and some free time are enough to learn a bit more.
