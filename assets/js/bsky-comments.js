/* Render Bluesky replies as blog comments.
 *
 * Reads the announcement post's bsky.app URL from the .bsky-comments
 * container's data-bsky-url attribute, fetches the thread from the
 * public Bluesky AppView (no auth), and renders the root post plus
 * its replies. Also updates the "N comments" chip in the post header.
 */
(function () {
  'use strict';

  var APPVIEW = 'https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread';
  var MAX_INDENT_LEVELS = 4;

  function esc(s) {
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(s == null ? '' : s));
    return d.innerHTML;
  }

  function parseBskyUrl(url) {
    var m = /bsky\.app\/profile\/([^/]+)\/post\/([a-z0-9]+)/i.exec(url || '');
    return m ? { actor: m[1], rkey: m[2] } : null;
  }

  function postUrl(post) {
    return 'https://bsky.app/profile/' + post.author.handle + '/post/' +
      post.uri.split('/').pop();
  }

  function fmtDate(iso) {
    try {
      return new Date(iso).toLocaleDateString('en-US',
        { year: 'numeric', month: 'short', day: 'numeric' });
    } catch (e) { return ''; }
  }

  function authorHtml(author, cssClass) {
    var name = author.displayName || author.handle;
    return '<a class="' + cssClass + '" href="https://bsky.app/profile/' +
      esc(author.handle) + '" target="_blank" rel="noopener">' +
      (author.avatar
        ? '<img class="bsky-avatar" src="' + esc(author.avatar) + '" alt="" loading="lazy">'
        : '') +
      '<span class="bsky-author-name">' + esc(name) + '</span></a>';
  }

  function textHtml(post) {
    var t = (post.record && post.record.text) || '';
    var html = '<div class="bsky-text">' + esc(t) + '</div>';
    if (post.embed && (post.embed.images || post.embed.media || post.embed.external)) {
      html += '<div class="bsky-media-note"><a href="' + postUrl(post) +
        '" target="_blank" rel="noopener">[view attached media/link on Bluesky]</a></div>';
    }
    return html;
  }

  function replyHtml(node, level) {
    if (!node || !node.post) return '';  // notFoundPost / blockedPost stubs
    var p = node.post;
    var indent = Math.min(level, MAX_INDENT_LEVELS) * 24;
    var html = '<div class="bsky-reply" style="margin-left:' + indent + 'px">' +
      '<div class="bsky-reply-meta">' + authorHtml(p.author, 'bsky-author') +
      ' &bull; <a class="bsky-date" href="' + postUrl(p) +
      '" target="_blank" rel="noopener">' + fmtDate(p.record && p.record.createdAt) + '</a>' +
      '</div>' + textHtml(p) + '</div>';
    html += childrenHtml(node, level + 1);
    return html;
  }

  function sortByDate(nodes) {
    return (nodes || []).slice().sort(function (a, b) {
      var da = (a.post && a.post.record && a.post.record.createdAt) || '';
      var db = (b.post && b.post.record && b.post.record.createdAt) || '';
      return da < db ? -1 : da > db ? 1 : 0;
    });
  }

  function childrenHtml(node, level) {
    return sortByDate(node.replies).map(function (r) {
      return replyHtml(r, level);
    }).join('');
  }

  function countReplies(node) {
    return (node.replies || []).reduce(function (n, r) {
      return r && r.post ? n + 1 + countReplies(r) : n;
    }, 0);
  }

  function rootHtml(post, bskyUrl, nReplies) {
    return '<div class="bsky-root">' +
      '<div class="bsky-reply-meta">' + authorHtml(post.author, 'bsky-author') +
      ' &bull; <a class="bsky-date" href="' + esc(bskyUrl) +
      '" target="_blank" rel="noopener">' + fmtDate(post.record && post.record.createdAt) +
      '</a></div>' + textHtml(post) +
      '<div class="bsky-counts">' +
      nReplies + ' repl' + (nReplies === 1 ? 'y' : 'ies') + ' &bull; ' +
      (post.repostCount || 0) + ' reposts &bull; ' +
      (post.likeCount || 0) + ' likes' +
      '<a class="bsky-reply-btn" href="' + esc(bskyUrl) +
      '" target="_blank" rel="noopener">Reply on Bluesky</a></div></div>';
  }

  function updateChip(n) {
    var chip = document.getElementById('comments-chip-label');
    if (chip && n > 0) chip.textContent = ' ' + n + ' comments ';
  }

  function fail(box, bskyUrl, msg) {
    box.innerHTML = '<p class="bsky-comments-loading">' + esc(msg) + ' ' +
      '<a href="' + esc(bskyUrl) + '" target="_blank" rel="noopener">' +
      'View the thread on Bluesky</a>.</p>';
  }

  function init() {
    var box = document.querySelector('.bsky-comments');
    if (!box) return;
    var bskyUrl = box.getAttribute('data-bsky-url');
    var ref = parseBskyUrl(bskyUrl);
    if (!ref) { fail(box, bskyUrl, 'Invalid Bluesky post reference.'); return; }
    var atUri = 'at://' + ref.actor + '/app.bsky.feed.post/' + ref.rkey;

    fetch(APPVIEW + '?uri=' + encodeURIComponent(atUri) + '&depth=10&parentHeight=0')
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        var t = data.thread;
        if (!t || !t.post) throw new Error('thread unavailable');
        var n = countReplies(t);
        box.innerHTML = rootHtml(t.post, bskyUrl, n) +
          (n ? childrenHtml(t, 0)
             : '<p class="bsky-no-replies">No comments yet &mdash; be the first to reply on Bluesky.</p>');
        updateChip(n);
      })
      .catch(function () {
        fail(box, bskyUrl, 'Comments could not be loaded from Bluesky.');
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
