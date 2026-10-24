# Explore map and list integration (US-2.1 / US-2.2)

## Updated sprint scope and split

Yueli owns #16 (US-2.1), #17 (US-2.2), and the newly assigned #78 (US-2.8).

1. Foundation #77 has been reviewed and approved; its author still needs to merge it.
2. **PR #83** (`feature/explore-filter-base`) is the early shared-filter step of
   #17. It is a draft until #77 merges. See `explore-filter-contract.md` for the
   stable interface Rae's bundle 3 should extend. It does not close #17.
3. This local branch now builds on #83 and retains the map, clustering, map/list
   and Events/Parks presentation. The shared filter partial, stylesheet and query
   helpers are reused directly, so the map follow-up won't replace Rae's widgets.
4. **#78 remains to implement in the follow-up**: a shared Events hub header,
   Explore/Create main toggle, Events navbar label, My Events account link, and
   session restoration of the last results query (including view/tab/park state).
   Include the hub partial on Explore, create and event detail; provide it for
   the owner of #21 to include on park detail. Keep #22's title-field work with
   bundle 5 rather than changing its form fields here.

Merge order: #77, then #83, then the map/list/hub follow-up when reviewed. Rae
can branch from updated develop after #83 merges. Do not close #18/#19/#20/#70
or #21/#23/#79 as part of Yueli's map or hub work.

This branch builds on PR #77's shared schema. It adds no models, migrations,
credentials, paid map SDK or AWS resources. Review and merge #77 first; then
sync this branch with develop before opening the feature PR.

## Local preview

```sh
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py sync_parks --if-empty
python manage.py seed_events
python manage.py runserver
```

The sync downloads public NYC Open Data. `seed_events` is optional, local sample
data; it is not run by a deployment hook. Open `/events/` for the default map,
`/events/?view=list&tab=events` for events, or `?view=list&tab=parks` for parks.
Local SQLite contains only local data, separate from the AWS database.

## Shared contract for parallel filter stories

`events/explore.py` is the single query boundary:

- `ExploreFilterForm` validates URL state, preserving valid members of repeated
  parameters and ignoring unknown values. Invalid date ranges are shown as
  validation messages and do not silently turn into partial ranges.
- `matching_events(filters, user=None)` defines event membership.
- `displayed_parks(filters, user=None)` defines park membership and annotates
  `event_count`. It includes parks that independently match the park filters,
  plus parks hosting matching events. Date and skill affect counts, not park
  visibility. My Events scopes force `events_only`.
- `filter_params(filters)` serializes canonical state with `QueryDict.setlist`;
  `explore_url` changes view/tab/page or removes a pill without losing repeated
  values. A filter or view change resets pagination.

Parameters: `q`, `borough`, repeated `zip`, repeated `sport`, repeated `facility`,
`when=today`, `date_from`, `date_to`, `skill`, `scope`, `events_only`, `park`,
`view=map|list` and `tab=events|parks`. Default view is map and default tab events;
both list tabs have 20 cards per page. The old `include_past` option is retired.

The basic server-rendered controls and backend predicates establish the shared
interface. Coordinate with the owners of #18/#19/#70/#75/#76 before replacing
their UI: lookahead/pill selectors and richer empty-state/capacity/host controls
remain in their respective stories. Add their widgets to
`templates/events/includes/explore_filters.html` and extend this engine, rather
than making a second set of map/list queries. This branch does not close those
other stories.

`GET /events/api/map/` returns all displayed parks with coordinates (not a page):
`parks: [{id, name, borough, lat, lng, event_count, preview_url}]` and
`unmapped_event_count`. The endpoint uses two data queries regardless of the
number of pins, plus active-park validation when a `park` parameter is supplied.
Personal scopes require login and use the authenticated user;
caller-supplied user IDs are never accepted.

Cluster icons sum matching events rather than park counts. Zero-event pins and
clusters are muted. Data failures leave the server-rendered list available.
JavaScript-disabled browsers see a notice and the list immediately.

## Park preview and future park detail integration

Pins and Quick view open a small read-only dialog using the shared filter engine.
Its endpoint is `/events/parks/<pk>/preview/`. This is an integration point for the
US-2.9 park panel, not a second full park detail implementation. Without JS the
Quick view link opens the server-rendered preview. If #21 provides a named
`park_detail` route accepting `pk`, Park details links appear automatically;
until then no broken `/parks/<id>/` link is emitted. Ratings show Not yet rated
until #42 exists. Confirm those route/panel contracts with their story owners.

## Map assets and external tiles

Leaflet 1.9.4 and Leaflet.markercluster 1.5.3 are vendored under `static/vendor/`
with their original licenses and source maps. No CDN JavaScript is required.
The visible base map uses OpenStreetMap standard raster tiles, with visible
attribution and an origin-only cross-origin Referer (required by the tile usage
policy). Do not prefetch/offline-download tiles or bypass browser caching.

References:
- https://leafletjs.com/examples/quick-start/
- https://github.com/Leaflet/Leaflet.markercluster
- https://operations.osmfoundation.org/policies/tiles/

## Verification

```sh
python manage.py test
python -m unittest discover -s infra -p 'test_*.py'
python manage.py makemigrations --check --dry-run
```

`events/test_explore.py` checks map/list membership and count agreement,
retired/unmapped parks, events-only, repeated URL values and pagination, public
exclusions and personal scope isolation, whole-token facilities and zip codes,
NY date boundaries, invalid ranges, escaping, preview filtering, and constant
map query count. Browser checks should include clustering, pin preview,
Map/List/Events/Parks navigation, a repeated filter selection, and map failure.
