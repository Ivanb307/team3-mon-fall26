const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('static/js/event-discussion.js', 'utf8');

function setup({open = true, hidden = false, initialIds = []} = {}) {
  const state = {fetchCalls: [], intervalDelay: null, intervalCallback: null, postHandler: null};
  const list = {
    dataset: {
      latestMessageId: initialIds.length ? String(Math.max(...initialIds)) : '0',
      updatesUrl: '/updates/',
      discussionOpen: String(open),
    },
    children: initialIds.map((id) => ({dataset: {messageId: String(id)}, announcement: false})),
    querySelector(selector) {
      const idMatch = selector.match(/^\[data-message-id="(\d+)"\]$/);
      if (idMatch) return this.children.find((item) => item.dataset.messageId === idMatch[1]) || null;
      if (selector === '.event-discussion-message--announcement') {
        return this.children.find((item) => item.announcement) || null;
      }
      if (selector === '.event-discussion-message:not(.event-discussion-message--announcement)') {
        return this.children.find((item) => !item.announcement) || null;
      }
      return null;
    },
    closest() {
      return discussion;
    },
    append(item) {
      this.children.push(item);
    },
    insertBefore(item, reference) {
      const index = this.children.indexOf(reference);
      this.children.splice(index < 0 ? this.children.length : index, 0, item);
    },
  };
  const status = {textContent: ''};
  const button = {disabled: false};
  const textarea = {value: 'New message'};
  const form = {
    action: '/post/',
    listeners: {},
    addEventListener(name, callback) {
      this.listeners[name] = callback;
    },
    querySelector(selector) {
      if (selector === 'button[type="submit"]') return button;
      if (selector === 'textarea[name="body"]') return textarea;
      if (selector === '[data-event-discussion-status]') return status;
      return null;
    },
    closest() {
      return discussion;
    },
  };
  const empty = {remove() {discussion.empty = null;}};
  const discussion = {
    empty: empty,
    querySelector(selector) {
      if (selector === '[data-event-discussion-form]') return open ? form : null;
      if (selector === '.event-discussion-empty') return this.empty;
      return null;
    },
  };
  const document = {
    hidden,
    querySelectorAll(selector) {
      return selector === '[data-event-discussion-list]' ? [list] : [];
    },
    createElement() {
      const template = {content: {firstElementChild: null}};
      Object.defineProperty(template, 'innerHTML', {
        set(html) {
          template.content.firstElementChild = {
            html,
            dataset: {},
            announcement: html.includes('announcement'),
          };
        },
      });
      return template;
    },
  };
  const window = {
    location: {href: 'https://example.test/events/1/'},
    setInterval(callback, delay) {
      state.intervalCallback = callback;
      state.intervalDelay = delay;
      return 1;
    },
    clearInterval() { state.intervalCleared = true; },
  };
  const fetch = async (url, options) => {
    state.fetchCalls.push({url: String(url), options});
    return state.fetchResponse();
  };
  const context = {
    document,
    window,
    URL,
    FormData: function FormData() {},
    fetch,
  };

  vm.runInNewContext(source, context);

  return {state, list, form, button, textarea, status, document};
}

test('polls every 30 seconds only for an open discussion', () => {
  assert.equal(setup({open: true}).state.intervalDelay, 30000);
  assert.equal(setup({open: false}).state.intervalDelay, null);
});

test('does not request updates while the document is hidden', async () => {
  const {state} = setup({hidden: true});
  await state.intervalCallback();
  assert.equal(state.fetchCalls.length, 0);
});

test('stops polling when the event discussion closes', async () => {
  const {state} = setup();
  state.fetchResponse = async () => ({
    ok: true,
    json: async () => ({discussion_open: false, messages: [], latest_id: 0}),
  });

  await state.intervalCallback();

  assert.equal(state.intervalCleared, true);
});

test('keeps the poll cursor unchanged after local posting and skips duplicate IDs', async () => {
  const {state, list, form, textarea} = setup({initialIds: [1]});
  let fetchCount = 0;
  state.fetchResponse = async () => {
    fetchCount += 1;
    if (fetchCount === 1) {
      return {
        ok: true,
        json: async () => ({html: '<li>local-3</li>', id: 3}),
      };
    }
    return {
      ok: true,
      json: async () => ({
        discussion_open: true,
        latest_id: 3,
        messages: [
          {id: 2, html: '<li>missed-2</li>'},
          {id: 3, html: '<li>local-3</li>'},
        ],
      }),
    };
  };
  const submitEvent = {preventDefault() {}};

  await form.listeners.submit(submitEvent);
  assert.deepEqual(list.children.map((item) => item.dataset.messageId), ['1', '3']);
  assert.equal(textarea.value, '');
  await state.intervalCallback();

  assert.match(state.fetchCalls[1].url, /after=1$/);
  assert.deepEqual(list.children.map((item) => item.dataset.messageId), ['1', '3', '2']);
  assert.equal(list.dataset.latestMessageId, '3');
});
