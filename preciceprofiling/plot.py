#!python3

import sqlite3
import pathlib
import collections
import math


def participants(cur):
    return cur.execute("SELECT name FROM participants")


def ranks(cur):
    return cur.execute("SELECT DISTINCT participant, rank FROM full_events")


Event = collections.namedtuple("Event", ["name", "ts", "dur", "data"])


def eventsFor(cur, participant, rank):
    for e in cur.execute(
        "SELECT event, ts - min(ts) OVER () as ts, dur, data FROM full_events WHERE dur > 0 AND participant == ? AND rank == ? ORDER BY ts ASC",
        (participant, rank),
    ):
        yield Event(*e)


def lastEnd(cur):
    return cur.execute("SELECT max(ts+dur) - min(ts) FROM events").fetchone()[0]


LANE_HEIGHT = 20


def drawEvent(name, lane, x, w):
    y = lane * LANE_HEIGHT
    return f"""<rect x="{x}" y="{y}" width="{w}" height="{LANE_HEIGHT}" fill="#F79257" stroke="#000000">
<title>{name}</title>
</rect>
<text class="name" x="{x}" y="{y+LANE_HEIGHT}">{name.rpartition("/")[-1]}</text>
"""


def drawRank(cur, lane, p, r):
    active = []
    content = []

    for event in eventsFor(cur, p, r):
        content.append(drawEvent(event.name, lane, event.ts, event.dur))
        lane += 1

    return content, lane


SVG_START = """<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
"""

STYLE = """<defs>
  <style type="text/css">
    <![CDATA[
      rect       { stroke-width: 1; stroke-opacity: 0; }
      rect.background   { fill: rgb(255,255,255); }
      rect.activating   { fill: rgb(255,0,0); fill-opacity: 0.7; }
      rect.active       { fill: rgb(200,150,150); fill-opacity: 0.7; }
      rect.deactivating { fill: rgb(150,100,100); fill-opacity: 0.7; }
      rect.kernel       { fill: rgb(150,150,150); fill-opacity: 0.7; }
      rect.initrd       { fill: rgb(150,150,150); fill-opacity: 0.7; }
      rect.firmware     { fill: rgb(150,150,150); fill-opacity: 0.7; }
      rect.loader       { fill: rgb(150,150,150); fill-opacity: 0.7; }
      rect.userspace    { fill: rgb(150,150,150); fill-opacity: 0.7; }
      rect.security     { fill: rgb(144,238,144); fill-opacity: 0.7; }
      rect.generators   { fill: rgb(102,204,255); fill-opacity: 0.7; }
      rect.unitsload    { fill: rgb( 82,184,255); fill-opacity: 0.7; }
      rect.box   { fill: rgb(240,240,240); stroke: rgb(192,192,192); }
      line       { stroke: rgb(64,64,64); stroke-width: 1; }
//    line.sec1  { }
      line.sec5  { stroke-width: 2; }
      line.sec01 { stroke: rgb(224,224,224); stroke-width: 1; }
      text       { font-family: Verdana, Helvetica; font-size: 14px; }
      text.name  { font-family: Verdana, Helvetica; font-size: 10px; }
      text.left  { font-family: Verdana, Helvetica; font-size: 14px; text-anchor: start; }
      text.right { font-family: Verdana, Helvetica; font-size: 14px; text-anchor: end; }
      text.sec   { font-size: 10px; }
    ]]>
   </style>
</defs>
"""


def drawTimes(w, h):
    TEXT_OFFSET = 3
    for s in range(math.floor(w / 1000)):
        x = s * 1000
        print(
            f'<text class="sec" x="{x+TEXT_OFFSET}" y="{LANE_HEIGHT-TEXT_OFFSET}">{s}s</text>"'
        )
        print(f'<line class="sec1" x1="{x}" y1="0" x2="{x}" y2="{h}"/>')

        for ds in range(1, 10):
            sx = x + ds * 100
            print(f'<line class="sec01" x1="{sx}" y1="0" x2="{sx}" y2="{h}"/>')


def main():
    con = sqlite3.connect("profiling.db")
    cur = con.cursor()

    content = []
    lane = 1  # lane 0 is for time
    for p, r in ranks(cur):
        res, lane = drawRank(cur, lane, p, r)
        content += res

    height = lane * LANE_HEIGHT
    width = lastEnd(cur)

    print(SVG_START)
    print(
        f'<svg width="{width}px" height="{height}px" version="1.1" xmlns="http://www.w3.org/2000/svg">'
    )
    print(STYLE)
    print(f'<rect class="background" x="0" y="0" width="{width}" height="{height}" />')
    drawTimes(width, height)

    for c in content:
        print(c)
    print("</svg>")


if __name__ == "__main__":
    main()
