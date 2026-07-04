async function loadPosts() {
  const feed = document.getElementById('feed');
  const lastSync = document.getElementById('lastSync');

  try {
    const res = await fetch('data/posts.json', { cache: 'no-store' });
    const posts = await res.json();

    if (!posts.length) {
      const emptyTpl = document.getElementById('emptyTemplate');
      feed.appendChild(emptyTpl.content.cloneNode(true));
      lastSync.textContent = 'NO DATA YET';
      return;
    }

    const cardTpl = document.getElementById('cardTemplate');

    posts.forEach((post) => {
      const node = cardTpl.content.cloneNode(true);

      node.querySelector('.meta-source').textContent = post.source || 'UNKNOWN';
      node.querySelector('.meta-id').textContent = post.id;
      node.querySelector('.meta-time').textContent = formatDateTime(post.published_at);

      const img = node.querySelector('.meta-image');
      img.src = post.image;
      img.alt = post.source ? `${post.source} — cybersecurity news` : 'cybersecurity news';

      node.querySelector('.meta-en').textContent = post.en_text;
      node.querySelector('.meta-ar').textContent = post.ar_text;

      const link = node.querySelector('.meta-link');
      link.href = post.link;

      setupCopyButton(node.querySelector('.copy-en'), post.en_text);
      setupCopyButton(node.querySelector('.copy-ar'), post.ar_text);

      feed.appendChild(node);
    });

    lastSync.textContent = `LAST SYNC ${formatDateTime(posts[0].published_at)}`;
  } catch (err) {
    lastSync.textContent = 'SYNC ERROR';
    console.error('Failed to load posts.json', err);
  }
}

function setupCopyButton(button, text) {
  if (!button) return;
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      // بديل احتياطي للمتصفحات القديمة
      const helper = document.createElement('textarea');
      helper.value = text;
      helper.style.position = 'fixed';
      helper.style.opacity = '0';
      document.body.appendChild(helper);
      helper.select();
      document.execCommand('copy');
      document.body.removeChild(helper);
    }
    button.dataset.copied = '1';
    setTimeout(() => { button.dataset.copied = '0'; }, 2000);
  });
}

function formatDateTime(isoString) {
  const d = new Date(isoString);
  if (isNaN(d)) return isoString;
  const pad = (n) => String(n).padStart(2, '0');
  const date = `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`;
  const time = `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
  return `${date} · ${time}`;
}

loadPosts();
