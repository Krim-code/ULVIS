
import argparse
import os
import time
import json
import math
import random
from typing import Tuple, Dict

import redis

def percentile(sorted_list, p):
    if not sorted_list:
        return 0.0
    k = (len(sorted_list)-1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_list[int(k)])
    d0 = sorted_list[f] * (c - k)
    d1 = sorted_list[c] * (k - f)
    return float(d0 + d1)

def approx_zipf_index(n:int, s:float=1.2) -> int:
    if n <= 1:
        return 0
    u = random.random()
    if abs(s-1.0) < 1e-9:
        x = max(1.0, min(n, math.exp(u * math.log(n))))
    else:
        x = ((u * (n**(1.0-s) - 1.0) + 1.0))**(1.0/(1.0-s))
        x = max(1.0, min(float(n), x))
    return int(x) - 1

def gen_key(idx:int) -> str:
    return f"k:{idx}"

def gather_info(r:redis.Redis) -> Dict[str,int]:
    info = r.info()
    fields = ("keyspace_hits","keyspace_misses","evicted_keys","expired_keys","used_memory")
    return {k: int(info.get(k, 0)) for k in fields}

def safe_set(r:redis.Redis, key:bytes, val:bytes):
    try:
        r.set(key, val)
        return True
    except redis.exceptions.OutOfMemoryError:
        # write rejected under maxmemory/noeviction — treat as failed warmup write
        return False

def run_load(
    host:str="127.0.0.1",
    port:int=6379,
    db:int=0,
    n_keys:int=200_000,
    value_size:int=1024,
    read_p:float=0.8,
    distribution:str="zipf",
    duration_s:int=60,
    pipeline:int=1,
) -> Tuple[dict, dict, dict]:
    r = redis.Redis(host=host, port=port, db=db, decode_responses=False)
    r.ping()

    # Warmup / populate keys if needed
    force_pop = os.getenv("FORCE_POPULATE","0") == "1"
    need_populate = force_pop or (r.dbsize() < n_keys//2)
    t0p = t1p = time.perf_counter()
    if need_populate:
        payload = b"a" * value_size
        t0p = time.perf_counter()
        # Try to use pipeline, but gracefully degrade on OOM
        pipe = r.pipeline(transaction=False)
        batch = 0
        for i in range(n_keys):
            pipe.set(gen_key(i), payload)
            batch += 1
            if batch >= 1000:
                try:
                    pipe.execute()
                except redis.exceptions.OutOfMemoryError:
                    # Fallback: attempt single-key sets until OOM persists, then stop warmup
                    pipe = r.pipeline(transaction=False)  # reset pipeline queue
                    filled = 0
                    for j in range(i-1000, i):
                        if not safe_set(r, gen_key(j).encode(), payload):
                            # Can't insert more keys; stop warmup
                            break
                        filled += 1
                    # If even single writes fail consistently — stop warmup early
                    if filled == 0:
                        break
                batch = 0
        if batch:
            try:
                pipe.execute()
            except redis.exceptions.OutOfMemoryError:
                # ignore tail OOM
                pass
        t1p = time.perf_counter()

    info_before = gather_info(r)

    # Load phase
    deadline = time.time() + duration_s
    ops = 0
    lat_ms = []
    pipe = r.pipeline(transaction=False) if pipeline > 1 else None
    pending = 0

    while time.time() < deadline:
        p = random.random()
        if distribution == "random":
            idx = random.randint(0, n_keys-1)
        elif distribution == "sequential":
            idx = ops % n_keys
        else:
            idx = approx_zipf_index(n_keys, 1.2)

        key = gen_key(idx).encode()
        t0 = time.perf_counter_ns()
        try:
            if pipe:
                if p < read_p:
                    pipe.get(key)
                else:
                    pipe.set(key, b"a"*value_size)
                pending += 1
                if pending >= pipeline:
                    pipe.execute()
                    t1 = time.perf_counter_ns()
                    lat_ms.append((t1 - t0)/1e6)
                    pending = 0
            else:
                if p < read_p:
                    r.get(key)
                else:
                    r.set(key, b"a"*value_size)
                t1 = time.perf_counter_ns()
                lat_ms.append((t1 - t0)/1e6)
        except redis.exceptions.OutOfMemoryError:
            # Treat as operation done with failure; record latency anyway
            t1 = time.perf_counter_ns()
            lat_ms.append((t1 - t0)/1e6)
        finally:
            ops += 1

    if pipe and pending:
        try:
            pipe.execute()
        except redis.exceptions.OutOfMemoryError:
            pass

    info_after = gather_info(r)

    lat_ms.sort()
    def pct(q): return percentile(lat_ms, q)
    stats = {
        "host": host,
        "port": port,
        "db": db,
        "n_keys": n_keys,
        "value_size": value_size,
        "read_p": read_p,
        "distribution": distribution,
        "duration_s": duration_s,
        "pipeline": pipeline,
        "ops": ops,
        "p50_ms": pct(0.50),
        "p95_ms": pct(0.95),
        "p99_ms": pct(0.99),
        "warmup_sec": (t1p - t0p),
        "ts": int(time.time())
    }
    return stats, info_before, info_after

def main():
    ap = argparse.ArgumentParser(description="Redis load generator (Python) with Zipf/random/sequential.")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=6379)
    ap.add_argument("--db", type=int, default=0)
    ap.add_argument("--n-keys", type=int, default=200_000)
    ap.add_argument("--value-size", type=int, default=1024)
    ap.add_argument("--read-p", type=float, default=0.8)
    ap.add_argument("--distribution", choices=["zipf","random","sequential"], default="zipf")
    ap.add_argument("--duration", type=int, default=60)
    ap.add_argument("--pipeline", type=int, default=1)
    args = ap.parse_args()

    stats, before, after = run_load(
        host=args.host,
        port=args.port,
        db=args.db,
        n_keys=args.n_keys,
        value_size=args.value_size,
        read_p=args.read_p,
        distribution=args.distribution,
        duration_s=args.duration,
        pipeline=args.pipeline,
    )

    deltas = {k: after.get(k,0) - before.get(k,0) for k in after.keys()}
    hits = after.get("keyspace_hits",0) - before.get("keyspace_hits",0)
    misses = after.get("keyspace_misses",0) - before.get("keyspace_misses",0)
    total = hits + misses
    hit_ratio = (hits/total) if total>0 else 0.0

    out = {
        "stats": stats,
        "info_before": before,
        "info_after": after,
        "deltas": deltas,
        "hit_ratio": hit_ratio,
        "hits": hits,
        "misses": misses,
    }
    print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()
