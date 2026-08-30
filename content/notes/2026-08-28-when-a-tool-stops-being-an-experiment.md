---
note_id: 2026-08-28-cuando-una-herramienta-deja-de-ser-un-experimento
lang: en
title: When a Tool Stops Being an Experiment
date: '2026-08-28'
tags:
- automation
- drupal
- devops
- ai
slug: when-a-tool-stops-being-an-experiment
summary: Provisional English adaptation of a note about an internal campaign scheduler that stopped feeling like an experiment once it handled a real campaign.
---

This is a provisional English adaptation of the original Spanish note.
It exists to validate the bilingual site architecture, not as final editorial copy.

A few weeks ago a very concrete problem showed up at work: we had to publish and remove a banner across dozens of markets, at a specific time, inside Drupal.
Doing it manually was possible. It was also exactly the kind of task that makes you ask: **why are we still doing this by hand?** That question became the Banner Scheduler.
The first version had a narrow goal: schedule visibility changes. Pick markets, define a date, and let the tool do the work when the time came. But a more interesting problem appeared almost immediately: visibility was only part of the story.
What happens when the banner content changes too? What do we do with multiple translations? How do we schedule several steps inside the same campaign? How do we keep Drupal from becoming the place where all the content actually lives? What happens if the site is temporarily in maintenance mode right when a change should run?

That is where the project started to shift. Today the Scheduler works together with **Atlas**, another internal tool we use as the source of truth for content and translations. The split became pretty clean:

* Atlas knows **what content should exist**.
* The Scheduler knows **when it should change and when it should be visible**.
* Drupal becomes the final destination, not the place where the whole process is managed.

A campaign can start from a spreadsheet, validate its markets and schedules, prepare its content changes, and generate the jobs that will run later. There is also a tiny sequence I really like: **check, apply, arm**. First verify that what we want to do makes sense. Then create the campaign. Only after that do we arm the jobs that can touch production.

Market schedules are normalized, actions are recorded, and the worker takes care of executing what was planned. If a temporary condition prevents a change from happening right away, the system retries instead of assuming everything failed. All of that ended up paired with a small interface where you can inspect campaigns, upcoming changes, recent activity, and the state of each operation.

This week the little milestone that made me want to write this happened: **we armed the first real campaign.**
It was no longer a test, a dry run, or specially prepared data for development. There was real content, real timing, and real changes that actually had to happen.

And it worked. What I like most about this project is that it did not begin with a giant specification or the ambition to build a “platform”.
It began by staring at a tedious task and thinking: **this should be possible to do better.** The rest appeared one question at a time. And there are probably still quite a few questions left.
