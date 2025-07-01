#! /usr/bin/env python3

# Import the currently fastest json library
import orjson
import datetime
import functools
import polars as pl

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


class RankData:
    def __init__(self, data):
        meta = data["meta"]
        self.name = meta["name"]
        self.rank = meta["rank"]
        self.size = meta["size"]
        self.unix_us = meta["unix_us"]
        self.tinit = meta["tinit"]

        self.events = data["events"]

    @property
    def type(self):
        return "Primary (0)" if self.rank == 0 else f"Secondary ({self.rank})"

    def toListOfTuples(self, eventLookup):
        for e in self.events:
            yield (
                self.name,
                self.rank,
                eventLookup[e["eid"]],
                int(e["ts"]),
                int(e["dur"]),
            )


class Run:
    def __init__(self, filename):
        print(f"Reading events file {filename}")

        with open(filename, "r") as f:
            content = orjson.loads(f.read())

        if "file_version" not in content:
            warning(
                "The file doesn't contain a version (preCICE version v3.2 or earlier) and may be incompatible.",
                filename,
            )
        elif (version := content["file_version"]) != MERGED_FILE_VERSION:
            warning(
                f"The file uses version {version}, which doesn't match the expected version {MERGED_FILE_VERSION} and may be incompatible.",
                filename,
            )

        self.eventLookup = {int(id): name for id, name in content["eventDict"].items()}
        self.data = content["events"]

    def iterRanks(self):
        for pranks in self.data.values():
            for d in sorted(
                pranks.values(), key=lambda data: int(data["meta"]["rank"])
            ):
                yield RankData(d)

    def iterParticipant(self, name):
        for d in self.data[name].values():
            yield RankData(d)

    def participants(self):
        return self.data.keys()

    def lookupEvent(self, id):
        return self.eventLookup[int(id)]

    def toTrace(self, selectRanks):
        if selectRanks:
            print(f'Selected ranks: {",".join(map(str,sorted(selectRanks)))}')

        def filterop(rank):
            return True if not selectRanks else rank.rank in selectRanks

        pids = {name: id for id, name in enumerate(self.participants())}
        tids = {
            (rank.name, rank.rank): id
            for id, rank in enumerate(filter(filterop, self.iterRanks()))
        }
        metaEvents = [
            {"name": "process_name", "ph": "M", "pid": pid, "args": {"name": name}}
            for name, pid in pids.items()
        ] + [
            {
                "name": "thread_name",
                "ph": "M",
                "pid": pid,
                "tid": tids[(rank.name, rank.rank)],
                "args": {"name": rank.type},
            }
            for name, pid in pids.items()
            for rank in filter(filterop, self.iterParticipant(name))
        ]

        mainEvents = []
        for rank in filter(filterop, self.iterRanks()):
            pid, tid = pids[rank.name], tids[(rank.name, rank.rank)]
            for e in rank.events:
                en = self.lookupEvent(e["eid"])
                mainEvents.append(
                    mergedDict(
                        {
                            "name": en,
                            "cat": "Solver" if en.startswith("solver") else "preCICE",
                            "ph": "X",  # complete event
                            "pid": pid,
                            "tid": tid,
                            "ts": e["ts"],
                            "dur": e["dur"],
                        },
                        {} if "data" not in e else {"args": e["data"]},
                    )
                )

        return {"traceEvents": metaEvents + mainEvents}

    def allDataFields(self):
        return list(
            {
                dname
                for rank in self.iterRanks()
                for e in rank.events
                if "data" in e
                for dname in e["data"].keys()
            }
        )

    def toExportList(self, unit, dataNames):
        factor = ns_to_unit_factor(unit) * 1e3 if unit else 1

        def makeData(e):
            if "data" not in e:
                return tuple(None for dname in dataNames)

            return tuple(e["data"].get(dname, None) for dname in dataNames)

        for rank in self.iterRanks():
            for e in rank.events:
                yield (
                    rank.name,
                    rank.rank,
                    rank.size,
                    self.lookupEvent(e["eid"]),
                    e["ts"],
                    e["dur"] * factor,
                ) + makeData(e)

    def toDataFrame(self):
        import itertools

        schema = [
            ("participant", pl.Utf8),
            ("rank", pl.Int32),
            ("eid", pl.Utf8),
            ("ts", pl.Int64),
            ("dur", pl.Int64),
        ]

        columns = ["participant", "rank", "eid", "ts", "dur"]
        df = pl.DataFrame(
            data=itertools.chain.from_iterable(
                map(lambda r: r.toListOfTuples(self.eventLookup), self.iterRanks())
            ),
            schema=schema,
        ).with_columns([pl.col("ts").cast(pl.Datetime("us"))])
        return df

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
