---
title: My Cheap Chinese Scale Now Talks to Garmin
date: '2026-10-15'
tags:
- homelab
- raspberry-pi
- garmin
- bluetooth
- running
summary: I got tired of OKOK's annoying ads and ended up connecting my cheap Chinese
  smart scale directly to Garmin Connect using a Raspberry Pi 5. Another little homelab
  experiment that worked out better than expected.
lang: en
note_id: 2026-10-15-mi-balanza-china-ahora-habla-con-garmin
---

A while ago, I bought one of those cheap Chinese smart scales that work with an app called OKOK. The scale itself works perfectly fine, but the app is unbearable. Every time I wanted to weigh myself, I had to sit through an ad that lasted almost 20 seconds. Ridiculous for something that should take five seconds.

First, I discovered [OpenScale](https://github.com/oliexdev/openScale), an open-source Android app that recognizes the scale without any issues. But then I started wondering: what if I could send my weight straight to Garmin Connect, without relying on any app?

That's when I came across [BLE Scale Sync](https://github.com/KristianP26/ble-scale-sync), a project that reads Bluetooth scales and syncs their data with different services, including Garmin.

Since I already have a Raspberry Pi 5 running 24/7, I figured I'd put it to work. I installed the project, configured the scale, set up Garmin authentication, and created a systemd service to keep everything running automatically.

Of course, it didn't all work on the first try. There was some Bluetooth troubleshooting, a few cryptic error messages, and quite a few trips to the scale. But eventually, it worked!

Now I just step on the scale, and a couple of seconds after Raspberry Pi picks up the reading, my weight shows up in Garmin Connect. It also saves a local history that I might eventually integrate into my little running project.

It even syncs body composition metrics, although in this case they're software estimates rather than actual measurements from the scale.

I didn't need another scale, let alone a Garmin Index. I just needed the one I already had to do what I wanted.

A small homelab victory. 😁
