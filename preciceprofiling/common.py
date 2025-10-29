#! /usr/bin/env python3

# Import the currently fastest json library
import datetime
import functools
import polars as pl
import sqlite3
import json
import pathlib
import collections

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
    def __init__(self, filename: pathlib.Path):
        print(f"Reading events file {filename}")

        if not filename.exists():
            raise FileNotFoundError(f"File {filename} doesn't exist")

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
                "name": name.rpartition("/")[2],
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

    def ranks(self):
        return self._cur.execute(
            "SELECT DISTINCT participant, rank FROM full_events ORDER BY participant ASC, rank ASC"
        ).fetchall()

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
            ("event", pl.Utf8),
            ("timestamp", pl.Int64),
            ("duration", pl.Int64),
        ] + [(dn, pl.Int64) for dn in dataFields]
        df = pl.DataFrame(
            data=self.toExportList(unit, dataFields),
            schema=schema,
        )
        return df

    def toPFTrace(self):
        import uuid
        from perfetto.trace_builder.proto_builder import TraceProtoBuilder
        from perfetto.protos.perfetto.trace.perfetto_trace_pb2 import (
            TrackEvent,
            TrackDescriptor,
            TracePacket,
        )

        Event = collections.namedtuple("Event", ["name", "ts", "dur", "data"])

        def eventsFor(participant, rank):
            for e in self._cur.execute(
                "SELECT event, (ts - (SELECT min(ts) FROM events))*1000 as ts , dur*1000, data FROM full_events WHERE dur > 0 AND event <> '_GLOBAL' AND participant == ? AND rank == ? ORDER BY ts ASC",
                (participant, rank),
            ):
                yield Event(*e)

        def groupFor(name):
            if name == "solver.advance" or name == "solver.initialize":
                return 1
            if "m2n.acceptPrimary" in name or "m2n.requestPrimary" in name:
                return 2
            if "m2n.acceptSecondary" in name or "m2n.requestSecondary" in name:
                return 3
            if "mapping" in name:
                return 4
            return None

        TPS_ID = 2025

        builder = TraceProtoBuilder()

        participants = {name: pid for pid, name in enumerate(self.participants())}

        for name, pid in participants.items():
            pkt = builder.add_packet()
            pkt.track_descriptor.uuid = uuid.uuid4().int & ((1 << 63) - 1)
            pkt.track_descriptor.process.pid = pid
            pkt.track_descriptor.process.process_name = name
            pkt.trusted_packet_sequence_id = TPS_ID

        ranks = [
            (p, r, i)
            for i, (p, r) in enumerate(
                self.ranks(),
                start=10,  # 0 is reserved
            )
        ]

        for p, r, u in ranks:
            pkt = builder.add_packet()
            pkt.track_descriptor.uuid = u
            pkt.track_descriptor.thread.thread_name = f"Rank {r}"
            pkt.track_descriptor.thread.pid = participants[p]
            pkt.track_descriptor.thread.tid = u
            pkt.trusted_packet_sequence_id = TPS_ID
            pkt.sequence_flags = TracePacket.SEQ_INCREMENTAL_STATE_CLEARED

        seen = {}

        for p, r, u in ranks:
            active = []
            for e in eventsFor(p, r):

                # end past events
                for a in active:
                    if (a.ts + a.dur) <= e.ts:
                        pkt = builder.add_packet()
                        pkt.timestamp = a.ts + a.dur
                        pkt.track_event.type = TrackEvent.TYPE_SLICE_END
                        pkt.track_event.track_uuid = u
                        pkt.trusted_packet_sequence_id = TPS_ID
                        pkt.sequence_flags = TracePacket.SEQ_NEEDS_INCREMENTAL_STATE

                # discard inactive
                active = [a for a in active if (a.ts + a.dur) > e.ts]
                active.append(e)

                # add new event
                pkt = builder.add_packet()
                pkt.timestamp = e.ts
                pkt.track_event.type = TrackEvent.TYPE_SLICE_BEGIN
                pkt.track_event.track_uuid = u
                if group := groupFor(e.name):
                    pkt.track_event.correlation_id = group
                pkt.trusted_packet_sequence_id = TPS_ID
                name = e.name.rpartition("/")[-1]
                if name in seen:
                    pkt.track_event.name_iid = seen[name]
                else:
                    pkt.track_event.name = name
                    entry = pkt.interned_data.event_names.add()
                    entry.iid = seen[name] = len(seen) + 1
                    entry.name = name
                pkt.sequence_flags = TracePacket.SEQ_NEEDS_INCREMENTAL_STATE

                # add data
                if e.data:
                    for key, value in json.loads(e.data).items():
                        annotation = pkt.track_event.debug_annotations.add()
                        annotation.name = key
                        annotation.int_value = value

            # end leftover events
            for a in active:
                pkt = builder.add_packet()
                pkt.timestamp = a.ts + a.dur
                pkt.track_event.type = TrackEvent.TYPE_SLICE_END
                pkt.track_event.track_uuid = u
                pkt.trusted_packet_sequence_id = TPS_ID
                pkt.sequence_flags = TracePacket.SEQ_NEEDS_INCREMENTAL_STATE

        return builder.serialize()
