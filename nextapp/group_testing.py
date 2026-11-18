"""Bounded group probes with queue/start/result events and responsive cancellation."""

import concurrent.futures
from .profile_testing import ProfileTest, test_tcp, test_https


def run_group(profiles, method, settings, cancel, started, received):
    # Cheap reachability screen for owned Free profiles before expensive TLS tests.
    # UDP protocols deliberately bypass TCP screening.
    free=settings.get('free_profile_ids',set())
    if method=='HTTPS' and free:
        candidates=[p for p in profiles if p.id in free and p.protocol not in {'hysteria2','hysteria','tuic'}]
        rejected=set()
        def screened(ident,result):
            if result.status in {'Failed','Timeout','Refused'} and result.code not in {'INTERNAL_ERROR','CORE_TIMEOUT','PROCESS_SUPERVISION'}:
                rejected.add(ident);received(ident,result)
        if candidates:run_group(candidates,'TCP',settings,cancel,started,screened)
        if cancel.is_set():return
        profiles=[p for p in profiles if p.id not in rejected]
    workers = (
        1
        if settings["lightweight"]
        else max(1, min(8, settings["concurrency"])) if method == "HTTPS" else max(1, min(256, settings.get("tcp_concurrency",128)))
    )
    if method == "TCP":
        groups={}
        for p in profiles:
            key=(p.host.lower(),p.port,p.protocol in {'hysteria2','hysteria','tuic'})
            groups.setdefault(key,[]).append(p)
        iterator=iter(groups.values())
    else:
        iterator=iter([p] for p in profiles)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {}

        def launch():
            if cancel.is_set():
                return False
            group = next(iterator, None)
            if group is None:
                return False
            profile=group[0]
            for item in group:
                started(item.id)
            future = (
                executor.submit(test_https, profile, settings, cancel)
                if method == "HTTPS"
                else executor.submit(
                    test_tcp, profile, min(1.5, settings.get("health_timeout", 8))
                )
            )
            pending[future] = group
            return True

        for _ in range(workers):
            launch()
        while pending:
            finished, _ = concurrent.futures.wait(
                pending, return_when=concurrent.futures.FIRST_COMPLETED
            )
            for future in finished:
                group = pending.pop(future)
                try:
                    result = future.result()
                except Exception:
                    result = ProfileTest(method, "Failed", code="INTERNAL_ERROR")
                if not cancel.is_set():
                    for item in group:
                        received(item.id, result)
                launch()
