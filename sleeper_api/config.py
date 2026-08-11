"""
Configuration settings like API base URL, timeout settings, etc.
"""
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict

logger = logging.getLogger(__name__)

BASE_URL = "https://api.sleeper.app/v1/"

# this tells us the default behavior for the API wrapper.
# True = convert everything to object oriented version
# False = return raw json results with no object oriented conversion
CONVERT_RESULTS = True
# TO DO: implement way for package user to specify this:
# ex:
# class Config:
#     def __init__(self):
#         # Default configuration
#         self.CONVERT_RESULTS = True

#     def set_convert_results(self, value: bool):
#         self.CONVERT_RESULTS = value

#     def get_convert_results(self) -> bool:
#         return self.CONVERT_RESULTS

# # Create a global config instance
# config = Config()
# then in the files, instead of importing CONVERT_RESULTS I can instead:
# import it: from sleeper_fantasy_api.config import config
# reference it: result = config.get_convert_results()

# user could specify globally by doing something like:
# from sleeper_fantasy_api.config import config
# config.set_convert_results(False)

CACHE_DURATION = timedelta(days=1)

# --- Current-season resolution (see GitHub issue #18) ---------------------
#
# `DEFAULT_SEASON = datetime.now().year` used to live here as a module-level
# constant. Two problems with that: an NFL season is labelled by the year it
# *starts*, so the calendar year overshoots by one for roughly eight months
# of the year (January through late summer); and being both module-level and
# a default argument meant it was computed exactly once, at import time, and
# then frozen for the lifetime of the process -- a service that started in
# December would keep using that year forever, including across the actual
# season rollover.
#
# `get_current_season()` replaces it. It asks Sleeper directly (GET
# /state/nfl, which reports the authoritative current `season` and
# `season_type`) instead of inferring anything from the clock, and it
# resolves on every logical "window" rather than once at import. The result
# is cached briefly so a long-running process pays for one request per
# window, not one per call.

# How long a resolved (season, season_type) pair is trusted before the next
# call re-queries /state/nfl. Long enough that normal call volume costs one
# request, short enough that a season/week rollover is picked up the same
# process session without a restart.
_SEASON_CACHE_TTL_SECONDS = 3600  # 1 hour

# Guards the two lines below together; a network call happens outside the
# lock (see _resolve_via_state_endpoint) so one slow request never blocks
# other threads sharing a client, matching the "safe across threads for
# read-only GETs" contract SleeperClient documents for itself.
_season_cache_lock = threading.Lock()
_season_cache: Dict[str, Any] = {}


def _clock_estimate_season(now=None):
    """
    Best-effort season estimate from the wall clock.

    Only used as a fallback when /state/nfl cannot be reached -- it is
    exactly the bug this module used to have, kept around deliberately as a
    last resort rather than raising and taking down every default-season
    call whenever the network hiccups.

    An NFL season is labelled by the year it starts, and the new league
    year's games begin in September, so a date from September onward belongs
    to the season starting that same year; January through August belong to
    the season that started the previous September.

    :param now: Override for the current time (used by tests). Defaults to
        ``datetime.now()``.
    :return: int season estimate.
    """
    now = now or datetime.now()
    return now.year if now.month >= 9 else now.year - 1


def _resolve_via_state_endpoint(client):
    """
    Query GET /state/nfl for the authoritative (season, season_type), using
    a short-lived cache so repeated calls in the same window cost one
    request rather than one per call.

    :param client: A SleeperClient (or anything exposing ``.get(endpoint)``
        with the same contract) used to make the request.
    :return: (season: int, season_type: str) tuple.
    :raises: Whatever the client raises (e.g. SleeperAPIError,
        RateLimitError) or a parsing error, if the state endpoint is
        unreachable or returns something unexpected. Callers are expected to
        catch this and fall back to :func:`_clock_estimate_season`.
    """
    now = time.monotonic()

    with _season_cache_lock:
        resolved_at = _season_cache.get("resolved_at")
        if resolved_at is not None and (now - resolved_at) < _SEASON_CACHE_TTL_SECONDS:
            return _season_cache["season"], _season_cache["season_type"]

    # The request itself happens outside the lock -- it is a network call,
    # and there is no reason to serialize every thread behind it. Two threads
    # racing here both make a (harmless, idempotent) request and both write
    # the same-ish cache entry; that is far cheaper than blocking on I/O
    # while holding a lock.
    state = client.get("state/nfl")
    season = int(state["season"])
    season_type = state.get("season_type", "regular")

    with _season_cache_lock:
        _season_cache["season"] = season
        _season_cache["season_type"] = season_type
        _season_cache["resolved_at"] = now

    return season, season_type


def get_current_season(client, prefer_previous_during_preseason=True):
    """
    Resolve "the current season" from GET /state/nfl rather than the clock.

    This is the fix for issue #18: the old `DEFAULT_SEASON` constant used
    `datetime.now().year`, which is wrong for roughly eight months of every
    year (an NFL season is labelled by the year it *starts*) and was frozen
    at import time. This function instead asks Sleeper directly, and
    resolves fresh (subject to a short cache -- see
    `_SEASON_CACHE_TTL_SECONDS`) on every call rather than once per process.

    Preseason subtlety: during `season_type == "pre"`, /state/nfl reports
    the *upcoming* season -- the one that has not started yet and has no
    projections, rosters, matchups, etc. Callers that want "the season with
    data" (the common case: past leagues, drafts, projections) should use
    the default `prefer_previous_during_preseason=True`, which steps back
    one season in that window. Callers that specifically want the season
    Sleeper currently considers upcoming/current (e.g. checking whether this
    year's draft has been scheduled yet) should pass `False`. Both readings
    are legitimate -- see the docstring of whichever endpoint method calls
    this for which one it picked.

    :param client: A SleeperClient used to query /state/nfl.
    :param prefer_previous_during_preseason: If True (default), returns
        `season - 1` while `season_type == "pre"`. If False, always returns
        exactly what /state/nfl reports.
    :return: int season.
    """
    try:
        season, season_type = _resolve_via_state_endpoint(client)
    except Exception as exc:
        # Unreachable /state/nfl (network error, rate limit, unexpected
        # payload shape, ...) should not take down every default-season
        # call -- fall back to a clock estimate and say so, so this doesn't
        # fail silently in a way that's hard to diagnose later.
        logger.warning(
            "Could not resolve the current NFL season from /state/nfl (%s); "
            "falling back to a clock-based estimate.", exc
        )
        return _clock_estimate_season()

    if prefer_previous_during_preseason and season_type == "pre":
        return season - 1
    return season
