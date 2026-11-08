document.querySelectorAll('[data-event-discussion-list]').forEach((list) => {
  const discussion = list.closest('.event-discussion');
  const form = discussion.querySelector('[data-event-discussion-form]');
  let latestId = Number(list.dataset.latestMessageId) || 0;
  let polling = false;

  const addMessage = (html, id, isAnnouncement = false) => {
    const message = document.createElement('template');
    message.innerHTML = html.trim();
    const item = message.content.firstElementChild;
    if (!item) return;
    item.dataset.messageId = String(id);

    if (isAnnouncement) {
      const firstAnnouncement = list.querySelector('.event-discussion-message--announcement');
      const firstRegular = list.querySelector('.event-discussion-message:not(.event-discussion-message--announcement)');
      list.insertBefore(item, firstAnnouncement || firstRegular);
    } else {
      list.append(item);
    }

    discussion.querySelector('.event-discussion-empty')?.remove();
    latestId = Math.max(latestId, Number(id) || 0);
    list.dataset.latestMessageId = String(latestId);
  };

  if (form) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();

      const button = form.querySelector('button[type="submit"]');
      const textarea = form.querySelector('textarea[name="body"]');
      const status = form.querySelector('[data-event-discussion-status]');
      button.disabled = true;
      status.textContent = '';

      try {
        const response = await fetch(form.action, {
          method: 'POST',
          body: new FormData(form),
          credentials: 'same-origin',
          headers: {'X-Requested-With': 'XMLHttpRequest'},
        });
        const result = await response.json();
        if (!response.ok) {
          status.textContent = result.error || 'Could not post your message. Please try again.';
          return;
        }

        addMessage(result.html, result.id);
        textarea.value = '';
      } catch {
        status.textContent = 'Could not post your message. Please try again.';
      } finally {
        button.disabled = false;
      }
    });
  }

  const updateDiscussion = async () => {
    if (polling) return;
    polling = true;
    try {
      const url = new URL(list.dataset.updatesUrl, window.location.href);
      url.searchParams.set('after', String(latestId));
      const response = await fetch(url, {credentials: 'same-origin'});
      if (!response.ok) return;
      const result = await response.json();
      result.messages.forEach((message) => {
        addMessage(message.html, message.id, message.is_announcement);
      });
    } catch {
      // A later poll retries transient network errors without interrupting posting.
    } finally {
      polling = false;
    }
  };

  window.setInterval(updateDiscussion, 5000);
});
