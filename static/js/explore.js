/* US-2.1 / US-2.2: progressive enhancement; all list/filter links work without JS. */
(() => {
  'use strict';
  const root = document.querySelector('[data-explore]');
  if (!root) return;
  const filtersForm = root.querySelector('.explore-filters');
  filtersForm.querySelector('[name="events_only"]').addEventListener('change', () => filtersForm.requestSubmit());
  const dialog = root.querySelector('[data-park-dialog]');
  const previewContent = root.querySelector('[data-preview-content]');
  let previewRequest;
  async function preview(url) {
    previewRequest?.abort();
    previewRequest = new AbortController();
    previewContent.textContent = 'Loading park…';
    if (!dialog.open) dialog.showModal();
    try {
      const response = await fetch(url, {signal: previewRequest.signal, credentials: 'same-origin'});
      if (!response.ok) throw new Error('Park unavailable');
      // Only a same-origin, Django-autoescaped HTML partial is accepted here.
      previewContent.innerHTML = await response.text();
    } catch (error) {
      if (error.name !== 'AbortError') previewContent.textContent = 'This park could not be loaded. Please close this panel and try again.';
    }
  }
  root.querySelector('[data-close-preview]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => previewRequest?.abort());
  root.addEventListener('click', (event) => {
    const link = event.target.closest('[data-park-preview]');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    preview(link.href);
  });
  if (root.dataset.view !== 'map') return;
  const shell = root.querySelector('[data-map-shell]');
  const container = root.querySelector('#explore-map');
  const fallback = root.querySelector('[data-list-fallback]');
  const errorBox = root.querySelector('[data-map-error]');
  const status = root.querySelector('[data-map-status]');
  function fail() { errorBox.hidden = false; fallback.hidden = false; status.hidden = true; }
  if (!window.L || !L.markerClusterGroup) { fail(); return; }
  shell.hidden = false;
  let map;
  let group;
  function icon(count, cluster = false) {
    const span = document.createElement('span');
    span.className = (cluster ? 'explore-cluster' : 'explore-pin') + (count > 0 ? ' is-active' : '');
    span.textContent = count > 0 ? String(count) : (cluster ? '○' : '');
    return L.divIcon({html: span, className: 'explore-marker', iconSize: cluster ? [46,46] : [30,30]});
  }
  try {
    map = L.map(container, {scrollWheelZoom: false}).setView([40.73, -73.94], 11);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, referrerPolicy: 'strict-origin-when-cross-origin',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).on('tileerror', fail).addTo(map);
    group = L.markerClusterGroup({showCoverageOnHover: false, maxClusterRadius: 48,
      iconCreateFunction: (cluster) => icon(cluster.getAllChildMarkers().reduce(
        (sum, marker) => sum + marker.options.eventCount, 0), true)
    }).addTo(map);
  } catch (_) { fail(); return; }
  let mapRequest;
  async function load() {
    mapRequest?.abort();
    mapRequest = new AbortController();
    status.hidden = false;
    status.textContent = 'Loading parks…';
    errorBox.hidden = true;
    try {
      const response = await fetch(container.dataset.mapUrl, {signal: mapRequest.signal, credentials: 'same-origin'});
      if (!response.ok || response.redirected) throw new Error('Map unavailable');
      const data = await response.json();
      group.clearLayers();
      const markers = data.parks.map((park) => {
        const title = `${park.name} · ${park.event_count} matching events`;
        const marker = L.marker([park.lat,park.lng], {icon: icon(park.event_count), eventCount: park.event_count,
          title, alt: title, keyboard: true});
        marker.on('add', () => marker.getElement()?.setAttribute('aria-label', title));
        const tooltip = document.createElement('span');
        tooltip.textContent = `${park.name} · ${park.borough}`;
        marker.bindTooltip(tooltip);
        marker.on('click', () => {
          const url = new URL(park.preview_url, window.location.origin);
          url.search = new URL(container.dataset.mapUrl, window.location.origin).search;
          preview(url);
        });
        return marker;
      });
      group.addLayers(markers);
      if (markers.length) map.fitBounds(group.getBounds(), {padding:[36,36], maxZoom:15});
      status.hidden = markers.length > 0;
      if (!markers.length) status.textContent = 'No parks match your filters. Try broadening your search.';
      const unmapped = root.querySelector('[data-unmapped]');
      unmapped.hidden = !data.unmapped_event_count;
      unmapped.replaceChildren();
      if (data.unmapped_event_count) {
        unmapped.append(document.createTextNode(`${data.unmapped_event_count} matching events are at parks without a map location. `));
        const link = document.createElement('a');
        const listURL = new URL(window.location.href);
        listURL.searchParams.set('view','list');
        listURL.searchParams.set('tab','events');
        listURL.searchParams.delete('page');
        link.href = listURL;
        link.textContent = 'See them in List view.';
        unmapped.append(link);
      }
      if (errorBox.hidden) fallback.hidden = true;
    } catch (error) { if (error.name !== 'AbortError') fail(); }
  }
  root.querySelector('[data-map-retry]').addEventListener('click', () => { map.eachLayer(layer => {
    if (layer instanceof L.TileLayer) layer.redraw();
  }); load(); });
  load();
})();
