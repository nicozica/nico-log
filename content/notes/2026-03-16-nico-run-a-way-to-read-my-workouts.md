---
note_id: 2026-03-16-nico-run-training-interpreted
lang: en
title: 'nico://run: A Way to Read My Workouts'
date: 2026-03-16
tags:
- nico-run
- pacer
- running
- astro
- raspberry-pi
- argensonix-labs
slug: nico-run-a-way-to-read-my-workouts
summary: 'After building Pacer, I took one more step and launched nico://run: a lightweight
  portal that takes that data, organizes it better, and turns it into a clearer
  reading of the last session, the week, and what might come next.'
---

After **Pacer**, the next need showed up pretty quickly. I did not just want better data for ChatGPT; I also wanted a place of my own to read what I’ve been doing more clearly. I was not looking for a running app, or another widget-filled dashboard, or a homemade copy of Strava. What I wanted was simpler: to see the last session, understand how the week is going, have an idea of what comes next, and read all that with a bit more clarity. That is how **nico://run** was born.

### What was missing

Pacer solved the data-prep part pretty well. It pulls activities from Strava, summarizes them, builds a cleaner brief, and lets me have a better conversation with ChatGPT. But there was still an intermediate layer missing, because having the data and actually seeing it arranged with some intention are two different things. That is where the idea of a personal running portal started to take shape: one that would not try to record everything, but instead help me interpret the important stuff a little better.

### What nico://run is

**nico://run** is basically a reading layer on top of Pacer. It lives at [run.nico.ar](https://run.nico.ar/), and what it does is take the snapshot I already prepare on the Pacer side and turn it into something more legible: the latest run as the main block, the next workout as a short suggestion, a weekly summary, and a few links to keep reading interesting things about running and wellness. The logic is pretty simple at heart: **Pacer prepares, nico://run organizes, and ChatGPT interprets**. Each piece does one distinct job, and for now that has worked better than trying to cram everything into one place.

### How it runs

The idea is still to keep it light. It is built as a static site, works with local data, and avoids unnecessary complexity. It is also meant to run comfortably even on small hardware, which is a big part of the project’s appeal. I really like the idea of showing something useful without needing oversized infrastructure to solve a fairly simple problem.

### What it already does

Today **nico://run** already does something concrete for me. It lets me look at the last session without digging through a dozen screens, quickly grasp the context of the week, and keep a friendlier layer between the raw workout and the next day’s decision. It does not replace Garmin or Strava, and it does not try to. It sits in that odd space between the watch and the next workout.

### What could come next

There is still room to keep polishing it. I would like to improve the history archive, give some views more personality, build a cleaner layer for the race calendar, and find better ways to connect the base plan with what I actually end up doing. But the important part is already there: **nico://run stopped being a nice idea and started turning into a tool of its own.**
