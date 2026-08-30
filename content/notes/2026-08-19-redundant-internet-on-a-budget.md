---
note_id: 2026-08-19-fallback-4g-a-lo-croto
lang: en
title: Redundant Internet on a Budget
date: '2026-08-19'
tags:
- linux
- proxmox
- 4g
- homelab
- tailscale
- cloudflare
slug: redundant-internet-on-a-budget
summary: A low-budget 4G fallback built from spare hardware and a tiny LTE router,
  so I can keep remote access, tunnels, and a backup route alive when fiber goes down.
---

The other day I started thinking about what would happen to my home setup if the fiber went down. If the home ISP disappeared for a few hours, I still wanted to be able to get in remotely to the servers, keep some Cloudflare tunnels alive, and have an emergency exit.

That is how KernelPanic-Rescue was born, a very handmade 4G fallback, built from hardware I already had lying around and a tiny LTE router that looks like a USB stick.

The main rule was that fiber would always remain the normal connection. The servers run independent checks against the internet and, if most of them fail, they wait another 15 seconds before making any decision.

If the internet comes back during that window, nothing happens.

If it is still down, they bring up the emergency connection, change the necessary routes, and some services start going out over 4G. When the fiber recovers in a stable way, everything returns automatically to its original state.

Those 15 seconds ended up mattering more than it seemed. Early one morning the ISP renewed the public IP and caused a small outage. One of the servers detected it, waited out the confirmation window, and logged:

`Fiber ISP health-check failed; confirming in 15 seconds.`
`Fiber ISP recovered during confirmation window.`

It never switched to 4G. That was exactly what I wanted to avoid: any little blink from the provider triggering a full failover.

## The Wi-Fi card zoo

The least elegant part was figuring out how to connect each machine to the emergency router.

I tried several USB adapters I had saved: a tiny TP-Link with a Realtek chipset, an old D-Link with a Ralink RT3070, and the built-in Wi-Fi of a Raspberry Pi.

The theory said any of them should be enough. Reality was different. The TP-Link had what looked like a reasonable signal, but could take full seconds to answer a ping. The old Ralink, on the other hand, ended up working much better. After trying different USB ports, positions, and distances, it was assigned exclusively to Bernarda, one of my Proxmox hosts.

The spare TP-Link ended up passed through USB to a Kali Linux VM, where it found a much more appropriate second life.

The LTE router also had something interesting: when connected directly by USB to the server, Linux sees it as a normal Ethernet card. That allowed one of the hosts to skip Wi-Fi entirely and have its own wired connection to the 4G router. It is not exactly datacenter architecture, but it works.

## What remained

The system is still small. I do not want to run streaming or heavy services over 4G. If the fiber goes down, the goal is to keep remote administration, Tailscale, Cloudflare, and a few important things alive until the normal connection returns.

The experiment ended up being much more entertaining than I expected. It started as “put a Wi-Fi antenna on it in case the internet goes down” and ended up involving policy routing, namespaces, systemd, recycled dongles, and a lot of time moving USB adapters from one port to another.

When I was a kid, I used to mess around with wire antennas on the terrace at home, trying to catch signals. A few decades later I am basically still doing the same thing. Only now there is Proxmox in the middle.
