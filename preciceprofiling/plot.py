#!python3

import sqlite3
import pathlib
import collections
import math

LANE_HEIGHT = 20
TEXT_OFFSET = 3


def ranks(cur):
    return cur.execute("SELECT DISTINCT participant, rank FROM full_events").fetchall()


Event = collections.namedtuple("Event", ["name", "ts", "dur", "data"])


def eventsFor(cur, participant, rank):
    for e in cur.execute(
        "SELECT event, ts - min(ts) OVER () as ts, dur, data FROM full_events WHERE dur > 0 AND participant == ? AND rank == ? ORDER BY ts ASC",
        (participant, rank),
    ):
        yield Event(*e)


def lastEnd(cur):
    return cur.execute("SELECT max(ts+dur) - min(ts) FROM events").fetchone()[0]


def drawRank(cur, lane, p, r):
    active = []

    seen = []

    content = [
        f'<line class="rank" x1="0" y1="{lane*LANE_HEIGHT}" x2="{lastEnd(cur)}" y2="{lane*LANE_HEIGHT}"/>',
        f'<text class="rank" x="{TEXT_OFFSET}" y="{(lane+1)*LANE_HEIGHT-TEXT_OFFSET}">{p} Rank:{r}</text>',
    ]

    for e in eventsFor(cur, p, r):
        mainName = e.name.rpartition("/")[-1]

        if mainName not in seen:
            seen.append(mainName)
        thislane = lane + 1 + seen.index(mainName)

        y = thislane * LANE_HEIGHT
        content += [
            "<g>",
            f"<title>Name {e.name}",
            f"Start {e.ts}us",
            f"Duration {e.dur}us",
            f"Participant {p}",
            f"Rank {r}",
            "</title>",
            f'<rect class="event" x="{e.ts}" y="{y}" width="{e.dur}" height="{LANE_HEIGHT}"/>',
            f'<text class="event" x="{e.ts + TEXT_OFFSET}" y="{y+LANE_HEIGHT-TEXT_OFFSET}">{mainName}</text>',
            "</g>",
        ]

    return content, len(seen) + 1


SVG_START = """<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
"""

STYLE = """<defs>
  <style type="text/css">
    <![CDATA[
      rect       { stroke-width: 1; stroke-opacity: 0; }
      rect.background   { fill: rgb(255,255,255); }
      rect.event        { fill: #ED762C; fill-opacity: 0.7; stroke: #000000; stroke-opacity: 1 }
      line       { stroke: rgb(64,64,64); stroke-width: 1; }
      line.sec1  { }
      line.sec01 { stroke: rgb(224,224,224); stroke-width: 1; }
      text       { font-family: Verdana, Helvetica; font-size: 14px; }
      text.event { font-family: Verdana, Helvetica; font-size: 10px; }
      text.sec   { font-size: 10px; }
    ]]>
   </style>
</defs>
"""


def drawTimes(w, h):
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
        res, lanes = drawRank(cur, lane, p, r)
        lane += lanes
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
