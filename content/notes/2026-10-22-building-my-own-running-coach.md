---
title: Building My Own Running Coach
date: '2026-10-22'
tags:
- running
- garmin
- garmin-connect
- smartwatch
- automation
summary: After several months of working on Pacer, I finally managed to get the workouts
  I plan through conversations with ChatGPT sent directly to my Garmin. It took quite
  a bit of testing, some frustrating pace-related issues, and a few surprises along
  the way.
lang: en
note_id: 2026-10-22-del-chat-al-garmin-con-algunas-vueltas-en-el-medio
---

Back in March, I wrote about [Pacer](https://www.nico.com.ar/en/pacer-from-screenshots-to-a-clean-chatgpt-brief/), a small tool I built so I could stop sending screenshots to ChatGPT every time I wanted to review my training. Shortly afterward came [nico://run](https://www.nico.com.ar/es/nico-run-training-interpreted/), a site where I started publishing my runs, some stats, and recommendations for upcoming sessions.

At the time, that was as far as the system went. Pacer gathered the information, I talked through how my training was going, and whenever I had a plan for my next run, I still had to enter it manually into Garmin Connect. It worked, but a very repetitive part of the process was still up to me.

On September 20, I finished my second Buenos Aires Marathon. After several months following a fairly structured training plan, I wanted to keep running with some consistency, just without the pressure of preparing for another marathon right away. And while I was at it, improve the tools I was already using.

The idea was this: after each run, Pacer gathers the activity data and generates a summary I can share with ChatGPT. It includes pace, heart rate, laps recorded by Garmin, recovery information, and a few personal observations I add myself.

I also started incorporating wellness data from [Intervals.icu](https://www.intervals.icu/): sleep duration and quality, resting heart rate, training load, and weight trends. I even ended up bringing a Chinese smart scale into the mix, which I managed to read automatically over Bluetooth without having to open its ad-filled app every time I weigh myself.

All of this adds context, although numbers alone don't always tell the whole story. Seeing that I ran seven kilometers at a certain pace isn't quite the same as explaining that my legs felt fine, but I found running that slowly unbearably boring.

With that information, I can discuss the session, review whether I achieved its purpose, and decide what makes sense for the next one. The analysis doesn't always have to agree with what Garmin says. In fact, part of what I enjoy is being able to question the recommendations and adjust the training based on how I actually felt.

Once everything makes sense, ChatGPT returns a JSON object containing two parts: an analysis of the completed activity and a proposal for the next workout. Pacer interprets that file, validates its contents, and shows me a preview before I approve it.

So far, so good. Things got complicated when I started looking for a way to send those workouts to my watch automatically.

Garmin lets you create structured workouts with warm-ups, running intervals, target paces, recovery periods, and repetitions. They're particularly useful when you're out running and want the watch to tell you what to do next, rather than constantly checking how much time has passed or calculating when the next interval should start.

Of course, I'm not inventing anything new here. There's Runna, which offers training plans and syncs them with Garmin. Some Garmin watches also have \*Daily Suggested Workouts\*, a feature my Venu 2 Plus doesn't support.

But what interested me went a little further than simply receiving a suggested workout. I wanted to discuss my training, include my own observations, question a proposed session, and end up with something I could actually execute on my watch. And, above all, I wanted to build on what I already had instead of adding yet another app to the list.

To make this work, I brought Intervals.icu into the setup as an intermediary. Completed activities come from Garmin, pass through Intervals.icu, and end up in Pacer. For planned workouts, the process runs in reverse: Pacer generates the structure, Intervals.icu receives it, and Garmin syncs it to the watch.

It sounded straightforward in theory. In practice, not so much.

The first workouts reached the watch with the correct durations, but every step appeared as \*Run\*, including the warm-up and cool-down. The pace targets were included in the descriptions, but it wasn't clear whether the watch was interpreting them as actual targets or just displaying them as text.

We tried several ways of generating the workout structure. We looked at how Intervals.icu parsed the steps, what information it exported, and what Garmin actually displayed. There was plenty of testing, and more than once I thought I'd end up having to configure everything manually after all.

One missing piece was properly configuring \*Threshold Pace\* in Intervals.icu. After reviewing a few recent races, we settled on an estimated value of 5:10 min/km. Once that was configured, the pace targets finally started appearing on the Garmin.

Next, we had to adjust Pacer's adapter to send the correct intensity types. Simply writing "Warm up" in a description wasn't enough: the system needed to identify that step as an actual warm-up, the next one as active running, and the last one as a cool-down.

And then there were the repetitions.

We wanted to define something like two 20-second accelerations, each followed by 1 minute and 40 seconds of recovery, and have Garmin recognize the whole thing as a repeated set. Not two separate instructions, and definitely not a description I'd have to read while running.

On October 22, I finally got to test it during a real workout. I went out for a 45-minute progressive run with two short accelerations and their recovery periods. The Venu displayed the steps correctly, including their pace targets and the repetitions grouped as *2 Sets*. During the run, the transitions between steps worked exactly as programmed.

That was precisely what I'd been trying to achieve.

<figure class="note-photo">
 <img src="/assets/img/notes/garmin-venu-2-plus-training-calendar-b1cf1203a3.webp" alt="Garmin Venu 2 Plus Workout" width="1519" height="855" loading="lazy" />
 <figcaption>Workout view on the watch, automatically planned by Pacer.</figcaption>
</figure>

All that information is now integrated with the rest of the system, too. Pacer keeps track of planned workouts, their synchronization status, and completed-session analyses. On [nico://run](https://run.nico.ar), I can publish my completed runs and display the next scheduled workout, including its duration and estimated distance.

There are some excellent tools handling different parts of this process. My work was connecting them, adapting the data, dealing with incompatibilities, and building an interface where the whole workflow made sense. Most of the time went into testing, finding bugs, and making sure that fixing one thing didn't break another.

Now comes the hardest part: getting out there and actually doing what we planned. 😁
