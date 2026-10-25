/* Run the shipped browser controller against a tiny DOM/Leaflet adapter.
 * No npm packages or test-only hooks in the production script are needed. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/explore.js', 'utf8');

function element() {
  return {hidden: false, textContent: '', children: [], listeners: {},
    addEventListener(name, handler) { this.listeners[name] = handler; },
    append(child) { this.children.push(child); },
    replaceChildren() { this.children = []; }};
}

async function controller({data, reject = false, leaflet = true, selected = false} = {}) {
  const nodes = {};
  for (const key of ['.explore-filters', '[data-park-dialog]', '[data-close-preview]',
    '[data-map-shell]', '#explore-map', '[data-list-fallback]', '[data-map-error]',
    '[data-map-status]', '[data-unmapped]', '[data-map-retry]']) nodes[key] = element();
  const checkbox = element();
  let submits = 0;
  nodes['.explore-filters'].querySelector = () => checkbox;
  nodes['.explore-filters'].requestSubmit = () => submits++;
  const dialog = nodes['[data-park-dialog]'];
  dialog.open = selected;
  dialog.close = () => { dialog.open = false; dialog.listeners.close?.(); };
  dialog.showModal = () => { dialog.open = true; };
  dialog.removeAttribute = () => { dialog.open = false; };
  nodes['#explore-map'].dataset = {mapUrl: '/events/api/map/?zip=11211&zip=11222'};
  const root = {dataset: {view: 'map'}, querySelector: key => nodes[key]};
  const navigations = [];
  const markers = [];
  let clusterOptions;
  let fits = 0;
  let tileError;
  const map = {setView() {return this;}, fitBounds() {fits++;}, eachLayer() {}};
  const group = {addTo() {return this;}, clearLayers() {}, addLayers() {}, getBounds() {return {};}};
  const L = {
    map: () => map,
    tileLayer: () => ({on(name, handler) {tileError = handler; return this;}, addTo() {return this;}}),
    markerClusterGroup(options) {clusterOptions = options; return group;},
    divIcon: options => options,
    marker(position, options) {
      const marker = {position, options, listeners: {},
        on(name, handler) {this.listeners[name] = handler; return this;},
        bindTooltip() {}, getElement() {return {setAttribute() {}};}};
      markers.push(marker);
      return marker;
    }
  };
  const window = {L: leaflet ? L : undefined, location: {
    href: 'http://localhost/events/?view=map&zip=11211&zip=11222&page=2' + (selected ? '&park=7&panel=1' : ''),
    assign(url) {navigations.push(new URL(url));}}};
  vm.runInNewContext(source, {window, L, URL, AbortController,
    document: {querySelector: () => root, createElement: element, createTextNode: text => ({textContent: text})},
    fetch: async () => {
      if (reject) throw new Error('Offline');
      return {ok: true, redirected: false, json: async () => data || {parks: [], unmapped_event_count: 0}};
    }});
  await new Promise(resolve => setImmediate(resolve));
  return {nodes, markers, clusterOptions, fits, navigations, checkbox, dialog,
    submits: () => submits, tileError};
}

const parks = [
  {id: 7, name: 'McCarren', borough: 'Brooklyn', lat: 40.7, lng: -73.9, event_count: 3},
  {id: 8, name: 'Central', borough: 'Manhattan', lat: 40.8, lng: -73.9, event_count: 4},
  {id: 9, name: 'Empty park', borough: 'Queens', lat: 40.7, lng: -73.8, event_count: 0},
];

test('clusters sum events rather than parks; empty pins/clusters are muted', async () => {
  const ui = await controller({data: {parks, unmapped_event_count: 0}});
  const sum = ui.clusterOptions.iconCreateFunction({getAllChildMarkers: () => ui.markers});
  assert.equal(sum.html.textContent, '7');
  assert.match(sum.html.className, /is-active/);
  const empty = ui.clusterOptions.iconCreateFunction({getAllChildMarkers: () => [ui.markers[2]]});
  assert.doesNotMatch(empty.html.className, /is-active/);
  assert.equal(ui.markers[0].options.icon.html.textContent, '3');
  assert.equal(ui.markers[2].options.icon.html.textContent, '');
  assert.equal(ui.fits, 1);
  assert.equal(ui.nodes['[data-list-fallback]'].hidden, true);
});

test('pin selection and closing preserve repeated filters in shareable URL state', async () => {
  const ui = await controller({data: {parks, unmapped_event_count: 0}, selected: true});
  assert.equal(ui.dialog.open, true);
  ui.markers[0].listeners.click();
  const selected = ui.navigations[0].searchParams;
  assert.equal(selected.get('park'), '7');
  assert.equal(selected.get('panel'), '1');
  assert.deepEqual(selected.getAll('zip'), ['11211', '11222']);
  assert.equal(selected.has('page'), false);
  ui.nodes['[data-close-preview]'].listeners.click();
  assert.equal(ui.navigations[1].searchParams.has('park'), false);
  assert.equal(ui.navigations[1].searchParams.has('panel'), false);
  assert.deepEqual(ui.navigations[1].searchParams.getAll('zip'), ['11211', '11222']);
});

test('unmapped notice links to Events list without losing filters', async () => {
  const ui = await controller({data: {parks, unmapped_event_count: 2}});
  const notice = ui.nodes['[data-unmapped]'];
  assert.equal(notice.hidden, false);
  assert.match(notice.children[0].textContent, /2 matching events/);
  const url = notice.children[1].href;
  assert.equal(url.searchParams.get('view'), 'list');
  assert.equal(url.searchParams.get('tab'), 'events');
  assert.deepEqual(url.searchParams.getAll('zip'), ['11211', '11222']);
});

test('missing Leaflet, failed data and failed tiles keep the server list available', async () => {
  for (const options of [{leaflet: false}, {reject: true}]) {
    const ui = await controller(options);
    assert.equal(ui.nodes['[data-map-error]'].hidden, false);
    assert.equal(ui.nodes['[data-list-fallback]'].hidden, false);
  }
  const ui = await controller({data: {parks, unmapped_event_count: 0}});
  ui.tileError();
  assert.equal(ui.nodes['[data-map-error]'].hidden, false);
  assert.equal(ui.nodes['[data-list-fallback]'].hidden, false);
});

test('events-only checkbox submits the existing shared filter form', async () => {
  const ui = await controller();
  ui.checkbox.listeners.change();
  assert.equal(ui.submits(), 1);
});
