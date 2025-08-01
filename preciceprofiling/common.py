#! /usr/bin/env python3

# Import the currently fastest json library
import datetime
import functools
import polars as pl
import sqlite3
import json

from preciceprofiling.merge import warning, MERGED_FILE_VERSION


def mergedDict(dict1, dict2):
    merged = dict1.copy()
    merged.update(dict2)
    return merged


@functools.lru_cache
def ns_to_unit_factor(unit):
    return {
        "ns": 1,
        "us": 1e-3,
        "ms": 1e-6,
        "s": 1e-9,
        "m": 1e-9 / 60,
        "h": 1e-9 / 3600,
    }[unit]


class Run:
    def __init__(self, filename):
        print(f"Reading events file {filename}")

        self._con = sqlite3.connect(filename)
        self._cur = self._con.cursor()

    def toTrace(self, selectRanks):

        events = [
            {"name": "process_name", "ph": "M", "pid": pid, "args": {"name": name}}
            for pid, name in self._cur.execute("SELECT pid, name FROM participants")
        ]

        rankQuery = "SELECT DISTINCT pid, rank FROM events"
        if selectRanks:
            print(f'Selected ranks: {",".join(map(str,sorted(selectRanks)))}')
            self._cur.execute(
                f'{rankQuery} WHERE rank IN ( { ", ".join("?" * len(selectRanks)) } )',
                tuple(selectRanks),
            )
        else:
            self._cur.execute(rankQuery)

        events += [
            {
                "name": "thread_name",
                "ph": "M",
                "pid": pid,
                "tid": rank,
                "args": {
                    "name": ("Primary (0)" if rank == 0 else f"Secondary ({rank})")
                },
            }
            for pid, rank in self._cur.fetchall()
        ]

        eventQuery = "SELECT n.name, e.pid, e.rank, e.ts, e.dur, e.data FROM events e INNER JOIN names n ON e.eid = n.eid"
        if selectRanks:
            self._cur.execute(
                f'{eventQuery} WHERE rank IN ( { ", ".join("?" * len(selectRanks)) } )',
                tuple(selectRanks),
            )
        else:
            self._cur.execute(eventQuery)

        events += [
            {
                "name": name,
                "cat": "Solver" if name.startswith("solver") else "preCICE",
                "ph": "X",  # complete event
                "pid": pid,
                "tid": tid,
                "ts": ts,
                "dur": dur,
                "args": {} if not data else json.loads(data),
            }
            for name, pid, tid, ts, dur, data in self._cur
        ]

        return {"traceEvents": events}

    def allDataFields(self):
        return list(
            {
                key
                for row in self._cur.execute(
                    "SELECT data FROM events WHERE data NOTNULL"
                )
                for key in json.loads(row[0]).keys()
            }
        )

    def toExportList(self, unit, dataNames):
        factor = ns_to_unit_factor(unit) * 1e3 if unit else 1

        def makeData(s):
            if not s:
                return tuple(None for dname in dataNames)
            return tuple(json.loads(s).get(dname, None) for dname in dataNames)

        for p, r, s, n, ts, dur, data in self._cur.execute("SELECT * FROM full_events"):
            yield (p, r, s, n, ts, dur * factor) + makeData(data)

    def participants(self):
        return [name for (name,) in self._cur.execute("SELECT name FROM participants")]

    def events(self):
        return [name for (name,) in self._cur.execute("SELECT name FROM names")]

    def toDataFrame(self, participant=None, event=None):
        query = "SELECT * FROM full_events"
        if participant and event:
            query += f" WHERE participant = '{participant}' and event = '{event}'"
        elif participant:
            query += f" WHERE participant = '{participant}'"
        elif event:
            query += f" WHERE event = '{event}'"

        return (
            pl.read_database(
                query=query,
                connection=self._cur,
            )
            .with_columns([pl.col("ts").cast(pl.Datetime("us"))])
            .rename({"event": "eid"})
        )

    def toExportDataFrame(self, unit):
        dataFields = self.allDataFields()
        schema = [
            ("participant", pl.Utf8),
            ("rank", pl.Int32),
            ("size", pl.Int32),
            ("eid", pl.Utf8),
            ("ts", pl.Int64),
            ("dur", pl.Int64),
        ] + [(dn, pl.Int64) for dn in dataFields]
        df = pl.DataFrame(
            data=self.toExportList(unit, dataFields),
            schema=schema,
        )
        return df
