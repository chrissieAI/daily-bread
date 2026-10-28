(function () {
  'use strict';
  var APP_VERSION = '20261028b';
  // User-visible section names — change here only.
  var DD_LABEL = 'Historic Writings';
  var ARCH_LABEL = 'Archaeology Finds';
  try { window.DB_APP_VERSION = APP_VERSION; window.DB_checkAppUpdate = null; } catch (e) {}
  var TZ = 'America/New_York';
  var COLORS = {
    GREEN:  { swatch: '#2e7d32', accent: '#2e7d32', ink: '#2e7d32' },
    PURPLE: { swatch: '#6a3d9a', accent: '#6a3d9a', ink: '#6a3d9a' },
    WHITE:  { swatch: '#ffffff', accent: '#c9a227', ink: '#8a6d12', light: true },
    GOLD:   { swatch: '#d4af37', accent: '#c9a227', ink: '#8a6d12', light: true },
    RED:    { swatch: '#b71c1c', accent: '#b71c1c', ink: '#b71c1c' },
    ROSE:   { swatch: '#e48aa8', accent: '#c2577c', ink: '#a63d62' },
    BLACK:  { swatch: '#222222', accent: '#333333', ink: '#333333' }
  };
  var RANK_LABEL = {
    SOLEMNITY: 'Solemnity', SUNDAY: 'Sunday', FEAST: 'Feast', MEMORIAL: 'Memorial',
    OPTIONAL_MEMORIAL: 'Optional memorial', WEEKDAY: 'Weekday'
  };

  var $ = function (id) { return document.getElementById(id); };

  // Lightweight self-update for iOS standalone / sticky caches: compare live index.html's
  // app.js?v= to APP_VERSION; one reload per target version (sessionStorage guard).
  function checkAppUpdate() {
    var url = 'index.html?_=' + Date.now();
    fetch(url, { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.text() : Promise.reject(); })
      .then(function (html) {
        var m = /app\.js\?v=([0-9a-z]+)/.exec(html);
        if (!m) return;
        var remote = m[1];
        if (remote === APP_VERSION) return;
        var guard = 'db-reloaded-for-' + remote;
        try {
          if (sessionStorage.getItem(guard)) return;
          sessionStorage.setItem(guard, '1');
        } catch (e) { /* private mode etc. */ }
        if (typeof window.DB_onReloadRequest === 'function') {
          try { window.DB_onReloadRequest(remote); } catch (e2) {}
          return;
        }
        location.reload();
      })
      .catch(function () { /* offline / blocked — ignore */ });
  }
  try { window.DB_checkAppUpdate = checkAppUpdate; } catch (e) {}
  // Overlay nav hooks filled in after overlays are defined.
  checkAppUpdate();
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') checkAppUpdate();
  });
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) checkAppUpdate();
  });

  var romcal = new Romcal.Romcal({ localizedCalendar: UnitedStates_En });
  var calCache = {};
  var readings = null;
  var movies = null;
  var parish = null;
  var dayInfo = {};

  function todayISO() {
    var p = new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' })
      .formatToParts(new Date());
    var g = function (t) { return p.filter(function (x) { return x.type === t; })[0].value; };
    return g('year') + '-' + g('month') + '-' + g('day');
  }
  function addDays(iso, n) {
    var d = new Date(iso + 'T12:00:00Z');
    d.setUTCDate(d.getUTCDate() + n);
    return d.toISOString().slice(0, 10);
  }
  function diffDays(a, b) {
    return Math.round((new Date(a + 'T12:00:00Z') - new Date(b + 'T12:00:00Z')) / 864e5);
  }
  function usccbUrl(iso) {
    return 'https://bible.usccb.org/bible/readings/' + iso.slice(5, 7) + iso.slice(8, 10) + iso.slice(2, 4) + '.cfm';
  }
  function prettyDate(iso) {
    return new Date(iso + 'T12:00:00Z').toLocaleDateString('en-US',
      { timeZone: 'UTC', weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
  }
  function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }
  function getCal(year) {
    if (!calCache[year]) calCache[year] = romcal.generateCalendar(year);
    return calCache[year];
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  var current = null;

  function isoFromHash() {
    var m = /^#(\d{4}-\d{2}-\d{2})$/.exec(location.hash);
    return m ? m[1] : null;
  }

  function show(iso) {
    current = iso;
    var t = todayISO();
    var dd = diffDays(iso, t);
    $('date').firstChild.nodeValue = prettyDate(iso);
    $('rel').textContent = dd === 0 ? 'Today' : dd === 1 ? 'Tomorrow' : dd === -1 ? 'Yesterday' : '';
    $('todayBtn').hidden = dd === 0;
    var url = usccbUrl(iso);
    var cta = $('usccb');
    cta.href = url;
    cta.firstChild.nodeValue = (dd === 0 ? "Read today's readings at USCCB" : 'Read this day\u2019s readings at USCCB') + '\n';
    document.querySelector('#readings .label').textContent = dd === 0 ? "Today's reading references" : 'Reading references';
    renderReadings(iso);
    renderMovie(iso);
    renderParish(iso);
    if (typeof renderArt === 'function' && art) renderArt(iso);
    if (saints) renderSaint(iso);
    getCal(+iso.slice(0, 4)).then(function (cal) {
      if (current !== iso) return;
      renderDay(cal[iso] || []);
      dayInfo[iso] = cal[iso] || [];
      renderParish(iso);
      renderPrayShort(iso);
      if (!$('prayers').hidden) renderPrayers();
    }).catch(function (e) {
      $('err').style.display = 'block';
      $('err').textContent = 'Could not compute the liturgical calendar for this date.';
      if (window.console) console.warn(e);
    });
  }

  function renderDay(days) {
    $('err').style.display = 'none';
    var main = days.filter(function (d) { return !d.isOptional; })[0] || days[0];
    if (!main) { $('feast').textContent = '—'; return; }
    $('feast').textContent = main.name;
    $('rank').textContent = RANK_LABEL[main.rank] || cap(main.rankName);
    $('season').textContent = (main.seasonNames && main.seasonNames[0]) || '';
    $('seasonChip').style.display = $('season').textContent ? '' : 'none';
    var cols = (main.colors || []).filter(function (c) { return COLORS[c]; });
    var sw = $('swatches');
    sw.textContent = '';
    cols.forEach(function (c) {
      var s = el('span', 'sw');
      s.style.background = COLORS[c].swatch;
      sw.appendChild(s);
    });
    $('color').textContent = (main.colorNames || []).map(cap).join(' or ');
    var c0 = COLORS[cols[0]] || COLORS.GREEN;
    var root = document.documentElement.style;
    root.setProperty('--accent', c0.accent);
    root.setProperty('--accent-ink', c0.ink);
    document.querySelector('meta[name=theme-color]').setAttribute('content', c0.accent);
    var opt = $('optional');
    opt.textContent = '';
    days.filter(function (d) { return d !== main; }).forEach(function (d) {
      opt.appendChild(el('li', null, (RANK_LABEL[d.rank] || cap(d.rankName)) + ': ' + d.name));
    });
  }

  // USCCB sometimes glues a non-verse ref onto the heading (e.g. "Alleluia See Te Deum")
  // when the address block is empty. Split so the row stays label + reference.
  // Bare "See" / "Cf." (truncated heading) → "See USCCB"; keep "See Te Deum" etc.
  var REF_HEADING_SPLIT = /^(Reading\s+\d+|Responsorial Psalm|Alleluia|Gospel|Sequence|Verse [Bb]efore the Gospel)\s+(.+)$/;
  var REF_INCOMPLETE = /^(See|Cf\.?)$/i;
  function normalizeRef(r) {
    var h = (r && r.heading) || '';
    var c = ((r && r.citation) || '').trim();
    if (/^[\s"'>/\\]*$/.test(c)) c = '';
    var m = REF_HEADING_SPLIT.exec(h);
    if (m) {
      h = m[1];
      if (!c && m[2]) c = m[2].trim();
    }
    if (c && REF_INCOMPLETE.test(c)) c = 'See USCCB';
    return { heading: h, citation: c };
  }
  function refsList(list, usccb) {
    var ul = el('ul', 'refs');
    list.forEach(function (r) {
      r = normalizeRef(r);
      var li = el('li');
      li.appendChild(el('span', 'h', r.heading));
      if (r.citation === 'See USCCB' && usccb) {
        var a = el('a', 'c', r.citation);
        a.href = usccb; a.target = '_blank'; a.rel = 'noopener';
        li.appendChild(a);
      } else {
        li.appendChild(el('span', 'c', r.citation || '\u2014'));
      }
      ul.appendChild(li);
    });
    return ul;
  }

  function renderReadings(iso) {
    var body = $('refsBody');
    if (readings === null) return; // still loading; rerun when loaded
    body.textContent = '';
    var day = readings && readings.days && readings.days[iso];
    if (!day || !day.masses || !day.masses.length) {
      body.appendChild(el('p', 'note', 'References for this date aren\u2019t saved in the app yet. Use the button above to open the readings at USCCB.'));
      return;
    }
    var dayUrl = (day.url) || usccbUrl(iso);
    if (day.title) body.appendChild(el('h2', null, day.title));
    day.masses.forEach(function (m) {
      if (m.name) body.appendChild(el('h3', null, m.name));
      if (m.readings && m.readings.length) body.appendChild(refsList(m.readings, (m.url) || dayUrl));
    });
  }

  function weekStart(iso) {
    var d = new Date(iso + 'T12:00:00Z');
    return addDays(iso, -d.getUTCDay());
  }

  // The week's pick (weeks start on Sunday). Before the first listed week show the
  // first (upcoming) pick; after the last week keep showing the last one.
  function moviePick(ws) {
    var list = (movies && movies.weeks || []).slice().sort(function (a, b) { return a.week_start < b.week_start ? -1 : 1; });
    if (!list.length) return null;
    var hit = list.filter(function (w) { return w.week_start === ws; })[0];
    if (hit) return hit;
    if (ws < list[0].week_start) return list[0];
    var prev = list.filter(function (w) { return w.week_start <= ws; });
    return prev[prev.length - 1];
  }

  function renderMovie(iso) {
    var card = $('movie');
    var ws = weekStart(iso);
    var m = moviePick(ws);
    if (!m) { card.hidden = true; return; }
    var when = new Date(m.week_start + 'T12:00:00Z').toLocaleDateString('en-US',
      { timeZone: 'UTC', month: 'long', day: 'numeric' });
    $('movieWeek').textContent = (m.week_start > ws ? 'Coming up: week of ' : 'Week of ') + when +
      (m.type === 'show' ? ' \u00b7 Show' : '');
    var t = $('movieTitle');
    t.textContent = m.title + ' ';
    if (m.year) t.appendChild(el('span', 'yr', '(' + m.year + ')'));
    $('movieRating').textContent = m.rating;
    $('movieSource').textContent = m.source;
    $('movieLink').href = m.review_url;
    card.hidden = false;
  }

  function isHolyDay(iso) {
    // Weekday holy days of obligation in the USA (romcal flag), excluding Sundays,
    // Christmas (parishes post a separate schedule) and the US rule that lifts the
    // obligation for Jan 1, Aug 15 and Nov 1 when they fall on a Saturday or Monday.
    var days = dayInfo[iso];
    if (!days) return false;
    var dow = new Date(iso + 'T12:00:00Z').getUTCDay();
    if (dow === 0) return false;
    return days.some(function (d) {
      if (!d.isHolyDayOfObligation) return false;
      if (d.id === 'nativity_of_the_lord') return false;
      var md = iso.slice(5);
      if ((md === '01-01' || md === '08-15' || md === '11-01') && (dow === 6 || dow === 1)) return false;
      return true;
    });
  }

  function renderParish(iso) {
    var card = $('parish');
    if (!parish || !parish.name) { card.hidden = true; return; }
    var dow = new Date(iso + 'T12:00:00Z').getUTCDay();
    var holy = isHolyDay(iso);
    var tagText = iso === todayISO() ? 'Today' : new Date(iso + 'T12:00:00Z').toLocaleDateString('en-US', { timeZone: 'UTC', weekday: 'short' });
    $('parishName').textContent = parish.name + (parish.location_label ? ', ' + parish.location_label : '');
    $('parishMap').textContent = parish.address_lines.join(', ');
    $('parishMap').href = parish.maps_url;
    $('parishTel').textContent = parish.phone_display;
    $('parishTel').href = 'tel:' + parish.phone_tel;
    var box = $('parishTimes');
    box.className = 'ptimes';
    box.textContent = '';
    parish.sections.forEach(function (sec) {
      box.appendChild(el('h3', null, sec.heading.replace(/:$/, '')));
      var ul = el('ul');
      sec.lines.forEach(function (ln) {
        var li = el('li', null, ln.text);
        var hit = (ln.days && ln.days.indexOf(dow) !== -1 && !(holy && sec.heading.indexOf('Weekly') === 0 && dow !== 0 && dow !== 6)) || (ln.holy_day && holy);
        if (hit) { li.className = 'hl'; li.appendChild(el('span', 'tag', ln.holy_day ? 'Holy day' : tagText)); }
        ul.appendChild(li);
      });
      box.appendChild(ul);
    });
    var b = parish.bulletin || {};
    var btn = $('bulletinBtn');
    // Use the dated PDF only if it is for this week (dated within 7 days before
    // or after the shown date); otherwise open the parish's bulletin page.
    var fresh = b.latest_url && b.latest_date && Math.abs(diffDays(b.latest_date, iso)) <= 7 && diffDays(b.latest_date, todayISO()) >= -7;
    btn.href = fresh ? b.latest_url : b.listing_url;
    btn.textContent = fresh ? "This week's bulletin" : "This week's bulletin (parish bulletin page)";
    $('bulletinAll').href = b.listing_url;
    $('parishSite').href = parish.website;
    $('parishNote').textContent = 'Times from the parish website, checked ' +
      new Date(parish.checked + 'T12:00:00Z').toLocaleDateString('en-US', { timeZone: 'UTC', month: 'long', day: 'numeric', year: 'numeric' }) +
      ' \u2014 always confirm on the parish site.' + (b.latest_label && fresh ? ' Bulletin: ' + b.latest_label + '.' : '');
    card.hidden = false;
  }

  fetch('data/parish.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : {}; })
    .catch(function () { return {}; })
    .then(function (data) { parish = data || {}; if (current) renderParish(current); });

  fetch('data/movies.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : {}; })
    .catch(function () { return {}; })
    .then(function (data) { movies = data || {}; if (current) renderMovie(current); });

  fetch('readings.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : {}; })
    .catch(function () { return {}; })
    .then(function (data) { readings = data || {}; if (current) renderReadings(current); });


  // ---- Art for today ----
  var art = null;
  var FAV_KEY = 'dailyBread.artFavorites';
  function getFavs() {
    try { var v = JSON.parse(localStorage.getItem(FAV_KEY) || '[]'); return Array.isArray(v) ? v : []; }
    catch (e) { return []; }
  }
  function setFavs(list) { try { localStorage.setItem(FAV_KEY, JSON.stringify(list)); } catch (e) {} }
  function isFav(iso) { return getFavs().indexOf(iso) >= 0; }
  function toggleFav(iso) {
    var f = getFavs(), i = f.indexOf(iso);
    if (i >= 0) f.splice(i, 1); else f.unshift(iso);
    setFavs(f);
    return i < 0;
  }
  function artFor(iso) { return art && art.days && art.days[iso]; }
  function capText(a) {
    var line1 = [a.artist, a.date].filter(Boolean).join(', ');
    return [line1, a.medium, a.museum].filter(Boolean);
  }
  function fillCap(node, a) {
    node.textContent = '';
    capText(a).forEach(function (t, i) {
      if (i) node.appendChild(document.createElement('br'));
      node.appendChild(el('span', i ? 'mu' : '', t));
    });
  }
  function chosenText(a) {
    if (a.match === 'gospel' && a.gospel) return 'Chosen for the Gospel: ' + a.gospel;
    var parts = [];
    if (a.chosen_for) parts.push('Chosen for: ' + a.chosen_for);
    if (a.gospel) parts.push('Gospel: ' + a.gospel);
    return parts.join(' \u00b7 ');
  }
  function setHeart(btn, on) {
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    btn.innerHTML = on ? '&#9829;' : '&#9825;';
    btn.setAttribute('aria-label', on ? 'Remove from favorites' : 'Save to favorites');
  }
  function renderArt(iso) {
    var a = artFor(iso), card = $('art');
    if (!a) { card.hidden = true; return; }
    card.hidden = false;
    var img = $('artImg');
    img.src = a.image;
    img.alt = a.title + (a.artist ? ', ' + a.artist : '');
    if (a.width && a.height) { img.width = a.width; img.height = a.height; }
    $('artTitle').textContent = a.title;
    fillCap($('artCap'), a);
    $('artChosen').textContent = chosenText(a);
    var ex = $('artExcerpt');
    if (a.excerpt) {
      ex.hidden = false;
      $('artExcerptText').textContent = '\u201c' + a.excerpt + '\u201d';
      $('artExcerptCr').textContent = a.excerpt_credit || '';
    } else ex.hidden = true;
    $('artLink').href = a.object_url;
    document.querySelector('#art .label').textContent = diffDays(iso, todayISO()) === 0 ? 'Art for today' : 'Art for this day';
    setHeart($('artHeart'), isFav(iso));
  }
  function openLightbox(src, alt) {
    $('lbImg').src = src; $('lbImg').alt = alt || '';
    $('lightbox').hidden = false;
    document.body.style.overflow = 'hidden';
  }
  function closeLightbox() {
    $('lightbox').hidden = true;
    if ($('favs').hidden) document.body.style.overflow = '';
  }
  var favSel = null;
  function renderFavs() {
    var list = getFavs().filter(function (d) { return artFor(d); });
    var grid = $('favGrid');
    grid.textContent = '';
    $('favEmpty').hidden = list.length > 0;
    list.forEach(function (d) {
      var a = artFor(d);
      var b = el('button');
      b.setAttribute('aria-label', a.title + ' (' + prettyDate(d) + ')');
      var im = el('img');
      im.src = a.thumb || a.image; im.alt = ''; im.loading = 'lazy';
      b.appendChild(im);
      b.addEventListener('click', function () { showFavDetail(d); });
      grid.appendChild(b);
    });
    if (favSel && list.indexOf(favSel) < 0 && !$('favDetail').hidden) {
      // keep detail visible so it can be re-hearted
    }
  }
  function showFavDetail(d) {
    favSel = d;
    var a = artFor(d);
    $('favDetail').hidden = false;
    $('fdImg').src = a.image; $('fdImg').alt = a.title;
    $('fdTitle').textContent = a.title;
    fillCap($('fdCap'), a);
    $('fdChosen').textContent = prettyDate(d) + ' \u00b7 ' + chosenText(a);
    $('fdDay').href = '#' + d;
    $('fdLink').href = a.object_url;
    setHeart($('fdHeart'), isFav(d));
    $('favDetail').scrollIntoView({ block: 'start', behavior: 'smooth' });
  }
  function openFavs() {
    favSel = null;
    $('favDetail').hidden = true;
    renderFavs();
    $('favs').hidden = false;
    document.body.style.overflow = 'hidden';
  }
  function closeFavs() {
    $('favs').hidden = true;
    document.body.style.overflow = '';
  }
  $('artOpen').addEventListener('click', function () {
    var a = artFor(current); if (a) openLightbox(a.image, a.title);
  });
  $('fdImg').addEventListener('click', function () {
    var a = artFor(favSel); if (a) openLightbox(a.image, a.title);
  });
  $('lightbox').addEventListener('click', closeLightbox);
  $('artHeart').addEventListener('click', function () {
    if (!artFor(current)) return;
    setHeart($('artHeart'), toggleFav(current));
  });
  $('fdHeart').addEventListener('click', function () {
    if (!favSel) return;
    setHeart($('fdHeart'), toggleFav(favSel));
    renderFavs();
    if (favSel === current) setHeart($('artHeart'), isFav(current));
  });
  $('favBtn').addEventListener('click', openFavs);
  $('favClose').addEventListener('click', closeFavs);
  $('fdDay').addEventListener('click', function () { closeFavs(); });
  fetch('data/art.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : {}; })
    .catch(function () { return {}; })
    .then(function (data) { art = data || {}; if (current) renderArt(current); });

  var saints = null;
  function renderSaint(iso) {
    var card = $('saint');
    var d = saints && saints[iso];
    if (!d) { card.hidden = true; return; }
    card.hidden = false;
    document.querySelector('#saint .label').textContent = diffDays(iso, todayISO()) === 0 ? 'Saint of the day' : 'Saint of this day';
    $('saintName').textContent = d.name;
    var also = $('saintAlso');
    if (d.also && d.also.length) { also.hidden = false; also.textContent = 'Also today: ' + d.also.join('; '); }
    else also.hidden = true;
    var ex = $('saintExcerpt'), box = $('saintText');
    box.textContent = '';
    if (d.excerpt && d.excerpt.length) {
      ex.hidden = false;
      d.excerpt.forEach(function (t) { var p = el('p'); p.textContent = t; box.appendChild(p); });
      var a = $('saintCe');
      a.href = d.ce_url;
      a.textContent = (d.ce_title || 'Read the entry') + ' \u2197';
    } else ex.hidden = true;
    var fm = $('saintFm');
    fm.textContent = '';
    (d.fm || []).forEach(function (l, i, arr) {
      var a = el('a');
      a.className = 'review';
      a.href = l.url; a.target = '_blank'; a.rel = 'noopener';
      a.textContent = (arr.length > 1 ? 'Read more at Franciscan Media: ' + l.title : 'Read more at Franciscan Media') + ' \u2197';
      fm.appendChild(a);
    });
  }
  fetch('data/saints.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : {}; })
    .catch(function () { return {}; })
    .then(function (data) { saints = (data && data.days) || {}; if (current) renderSaint(current); });

  var prayers = null;
  function isEaster(iso) {
    var days = dayInfo[iso];
    return !!(days && days[0] && (days[0].seasons || []).indexOf('EASTER_TIME') >= 0);
  }
  function prayerById(id) {
    return prayers && prayers.filter(function (p) { return p.id === id; })[0];
  }
  function marianId(iso) { return isEaster(iso) ? 'regina-caeli' : 'angelus'; }
  function segs(parent, list) {
    list.forEach(function (sg) {
      var n = sg.b ? el('strong', null, sg.t) : sg.i ? el('em', null, sg.t) : document.createTextNode(sg.t);
      parent.appendChild(n);
    });
  }
  function renderPrayers() {
    var box = $('prayList');
    if (!prayers || !current) return;
    box.textContent = '';
    var easter = isEaster(current);
    // Regina Caeli replaces the Angelus in the Easter season.
    var show = prayers.filter(function (p) { return p.id === (easter ? 'regina-caeli' : 'angelus') || (p.id !== 'angelus' && p.id !== 'regina-caeli'); });
    show.forEach(function (p) {
      var d = el('details', 'prayer');
      d.id = 'prayer-' + p.id;
      d.appendChild(el('summary', null, p.title));
      if (p.id === 'regina-caeli') d.appendChild(el('span', 'season-tag', 'Easter season'));
      if (p.link_only) {
        var lb = el('a', 'review plink', (p.button || 'Pray the ' + p.title + ' at USCCB') + ' \u2197');
        lb.href = p.source_url; lb.target = '_blank'; lb.rel = 'noopener';
        d.appendChild(lb);
        d.appendChild(el('p', 'pnotice plabel', p.label || ''));
        box.appendChild(d);
        return;
      }
      var tx = el('div', 'ptext');
      p.paragraphs.forEach(function (para) {
        var pe = el('p');
        para.forEach(function (line) { var ln = el('span', 'ln'); segs(ln, line); pe.appendChild(ln); });
        tx.appendChild(pe);
      });
      d.appendChild(tx);
      if (p.notice) { var nt = el('p', 'pnotice'); segs(nt, p.notice); d.appendChild(nt); }
      if (p.note) d.appendChild(el('p', 'pnotice psrcnote', p.note));
      var a = el('a', 'psrc', 'Source: USCCB \u2197');
      a.href = p.source_url; a.target = '_blank'; a.rel = 'noopener';
      d.appendChild(a);
      box.appendChild(d);
    });
  }
  function renderPrayShort(iso) {
    var b = $('prayShort');
    var p = prayerById(marianId(iso));
    if (!p || !dayInfo[iso]) { b.hidden = true; return; }
    b.hidden = false;
    b.textContent = 'Pray the ' + p.title + (p.link_only ? ' at USCCB' : '') + ' \u203A';
  }
  function openPrayers(focusId) {
    renderPrayers();
    $('prayers').hidden = false;
    document.body.style.overflow = 'hidden';
    $('prayers').scrollTop = 0;
    if (focusId) { var d = $('prayer-' + focusId); if (d) d.open = true; }
  }
  function closePrayers() {
    $('prayers').hidden = true;
    document.body.style.overflow = '';
  }
  $('prayBtn').addEventListener('click', function () { openPrayers(); });
  $('prayShort').addEventListener('click', function () {
    var p = prayerById(marianId(current));
    if (p && p.link_only) window.open(p.source_url, '_blank', 'noopener');
    else openPrayers(marianId(current));
  });
  $('prayClose').addEventListener('click', closePrayers);
  fetch('data/prayers.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : {}; })
    .catch(function () { return {}; })
    .then(function (data) { prayers = (data && data.prayers) || []; if (current) renderPrayShort(current); });

  // Historic Writings (internal id: deepdive): links out only; no text from the works is stored.
  // Archaeology Finds: data/discovery.json — own overlay + static /archaeology/.
  var deepdive = null;
  var discovery = null;
  function ddLink(cls, ln) {
    var a = el('a', cls, ln.label + ' \u2197');
    a.href = ln.url; a.target = '_blank'; a.rel = 'noopener';
    return a;
  }
  function ddLegendBadge() {
    var b = el('span', 'dd-legend', 'legend');
    b.title = 'Legend — not verified history';
    return b;
  }
  function ddMeanwhileStrip(entries, funList) {
    entries = entries || [];
    funList = funList || [];
    if (!entries.length && !funList.length) return null;
    var det = document.createElement('details');
    det.className = 'dd-meanwhile';
    var sum = document.createElement('summary');
    sum.textContent = 'Meanwhile in the world';
    det.appendChild(sum);
    if (funList.length) {
      var funBox = el('div', 'dd-fun-in-strip');
      var label = el('p', 'dd-fun-label', '\u2726 Fun overlaps');
      funBox.appendChild(label);
      funList.forEach(function (f) {
        var card = el('div', 'dd-fun-card');
        var top = el('div', 'dd-fun-card-top');
        top.appendChild(el('span', 'dd-fun-title', f.title || ''));
        if (f.legend) top.appendChild(ddLegendBadge());
        card.appendChild(top);
        card.appendChild(el('p', 'dd-fun-detail', f.detail || ''));
        var srcs = f.sources || (f.source ? [f.source] : []);
        if (srcs.length) {
          var row = el('p', 'dd-fun-srcs');
          srcs.forEach(function (u, i) {
            if (i) row.appendChild(document.createTextNode(' \u00b7 '));
            var a = el('a', null, 'source');
            a.href = u; a.target = '_blank'; a.rel = 'noopener';
            row.appendChild(a);
          });
          card.appendChild(row);
        }
        funBox.appendChild(card);
      });
      det.appendChild(funBox);
    }
    if (entries.length) {
      var scroller = el('div', 'dd-meanwhile-scroll');
      entries.forEach(function (e) {
        var card = el('div', 'dd-meanwhile-card');
        var top = el('div', 'dd-meanwhile-top');
        top.appendChild(el('span', 'dd-meanwhile-date', e.date || ''));
        if (e.legend) top.appendChild(ddLegendBadge());
        card.appendChild(top);
        card.appendChild(el('p', 'dd-meanwhile-text', e.text || ''));
        if (e.source) {
          var a = el('a', 'dd-meanwhile-src', 'source');
          a.href = e.source; a.target = '_blank'; a.rel = 'noopener';
          card.appendChild(a);
        }
        scroller.appendChild(card);
      });
      det.appendChild(scroller);
    }
    return det;
  }
  function ddItemMeanwhile(mw) {
    if (!mw || !mw.text) return null;
    var p = el('p', 'dd-item-mw');
    var ico = el('span', 'dd-item-mw-ico', '\uD83C\uDF0D');
    ico.setAttribute('aria-hidden', 'true');
    p.appendChild(ico);
    p.appendChild(document.createTextNode(' ' + mw.text + ' '));
    if (mw.legend) p.appendChild(ddLegendBadge());
    if (mw.source) {
      var a = el('a', 'dd-item-mw-src', 'source');
      a.href = mw.source; a.target = '_blank'; a.rel = 'noopener';
      p.appendChild(document.createTextNode(' '));
      p.appendChild(a);
    }
    return p;
  }
  function discoveryByPeriod() {
    var map = {};
    if (!discovery || !discovery.items) return map;
    discovery.items.forEach(function (it) {
      var p = it.period || '';
      if (!map[p]) map[p] = [];
      map[p].push(it);
    });
    return map;
  }
  function discoveryLinksForWriting(wid) {
    if (!discovery || !discovery.items) return [];
    return discovery.items.filter(function (it) {
      return (it.connects_to || []).indexOf(wid) >= 0;
    });
  }
  function ensureDiscovery() {
    if (discovery && discovery.items) return Promise.resolve(discovery);
    return fetch('data/discovery.json', { cache: 'no-cache' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; })
      .then(function (disc) {
        if (disc && disc.items) discovery = disc;
        return discovery;
      });
  }
  function ensureDeepDive() {
    if (deepdive && deepdive.groups) return Promise.resolve(deepdive);
    return fetch('data/deepdive.json', { cache: 'no-cache' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; })
      .then(function (data) {
        if (data && data.groups) deepdive = data;
        return deepdive;
      });
  }
  function renderDiscoveryCard(it, opts) {
    opts = opts || {};
    var card = el('article', 'dd-disc-card');
    card.id = 'disc-' + it.id;
    var fig = el('figure', 'dd-disc-fig');
    if (it.image && it.image.src) {
      var img = document.createElement('img');
      img.src = it.image.src;
      img.alt = it.image.alt || it.name || '';
      img.loading = 'lazy';
      img.decoding = 'async';
      fig.appendChild(img);
      var credit = el('figcaption', 'dd-disc-credit', '');
      var bits = [];
      if (it.image.credit) bits.push(it.image.credit);
      if (it.image.license) bits.push(it.image.license);
      credit.appendChild(document.createTextNode(bits.join(' \u00b7 ')));
      if (it.image.license_url) {
        credit.appendChild(document.createTextNode(' \u00b7 '));
        var la = el('a', null, 'license');
        la.href = it.image.license_url; la.target = '_blank'; la.rel = 'noopener';
        credit.appendChild(la);
      }
      fig.appendChild(credit);
    }
    card.appendChild(fig);
    card.appendChild(el('h4', 'dd-disc-name', it.name || ''));
    if (it.type) card.appendChild(el('p', 'dd-disc-type', it.type));
    if (it.date) card.appendChild(el('p', 'dd-disc-date', it.date));
    if (it.caution) {
      var caut = document.createElement('details');
      caut.className = 'dd-caution';
      var csum = document.createElement('summary');
      csum.textContent = '\u24d8 Read with care';
      caut.appendChild(csum);
      caut.appendChild(el('p', 'dd-caution-body', it.caution));
      card.appendChild(caut);
    }
    if (it.line) card.appendChild(el('p', 'dd-disc-line', it.line));
    if (it.found || it.now) {
      var meta = el('p', 'dd-disc-meta', '');
      if (it.found) meta.appendChild(document.createTextNode('Found: ' + it.found));
      if (it.found && it.now) meta.appendChild(document.createTextNode(' \u00b7 '));
      if (it.now) meta.appendChild(document.createTextNode('Now: ' + it.now));
      card.appendChild(meta);
    }
    if (it.bible_refs && it.bible_refs.length) {
      card.appendChild(el('p', 'dd-disc-refs', 'Bible: ' + it.bible_refs.join('; ')));
    }
    if (it.evidence && (it.evidence.shows || it.evidence.infer || it.evidence.debated)) {
      var ev = document.createElement('details');
      ev.className = 'dd-disc-ev';
      var es = document.createElement('summary');
      es.textContent = 'Evidence shows / Scholars infer / Still debated';
      ev.appendChild(es);
      var body = el('div', 'dd-disc-ev-body');
      if (it.evidence.shows) {
        var p1 = el('p', null, '');
        p1.appendChild(el('strong', null, 'Evidence shows: '));
        p1.appendChild(document.createTextNode(it.evidence.shows));
        body.appendChild(p1);
      }
      if (it.evidence.infer) {
        var p2 = el('p', null, '');
        p2.appendChild(el('strong', null, 'Scholars infer: '));
        p2.appendChild(document.createTextNode(it.evidence.infer));
        body.appendChild(p2);
      }
      if (it.evidence.debated) {
        var p3 = el('p', null, '');
        p3.appendChild(el('strong', null, 'Still debated: '));
        p3.appendChild(document.createTextNode(it.evidence.debated));
        body.appendChild(p3);
      }
      ev.appendChild(body);
      card.appendChild(ev);
    }
    if (it.sources && it.sources.length) {
      var srcRow = el('p', 'dd-disc-srcs');
      it.sources.forEach(function (s) {
        var a = el('a', null, (s.label || 'Source') + ' \u2197');
        a.href = s.url; a.target = '_blank'; a.rel = 'noopener';
        srcRow.appendChild(a);
      });
      card.appendChild(srcRow);
    }
    // Cross-link into Historic Writings
    if (opts.withWriteLink) {
      var connects = it.connects_to || [];
      var ddPeriod = it.deepdive_period;
      var target = connects.length ? ('dd-' + connects[0]) : (ddPeriod ? ('dd-' + ddPeriod) : null);
      if (target) {
        var wl = el('a', 'dd-writelink', 'Read the writings from this time');
        wl.href = 'deep-dive/#' + target;
        wl.addEventListener('click', function (e) {
          if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
          e.preventDefault();
          var fromLabel = it.name || ARCH_LABEL;
          navigateOverlay('deepdive', {
            anchor: target,
            back: snapshotBack('archaeology', 'disc-' + it.id, fromLabel)
          });
        });
        card.appendChild(wl);
      }
    }
    return card;
  }
  function renderDeepDive() {
    var box = $('ddList');
    if (!deepdive) return;
    box.textContent = '';
    $('ddIntro').textContent = deepdive.intro || '';
    var titleEl = $('ddTitle');
    if (titleEl) titleEl.textContent = DD_LABEL;

    if (deepdive.groups && deepdive.groups.length) {
      var jump = el('nav', 'dd-jump');
      jump.setAttribute('aria-label', 'Jump to period');
      deepdive.groups.forEach(function (g) {
        var a = el('a', 'dd-chip', g.title.split('\u00b7')[0].trim());
        a.href = '#dd-' + g.id;
        a.addEventListener('click', function (e) {
          e.preventDefault();
          var t = document.getElementById('dd-' + g.id);
          if (t) t.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
        jump.appendChild(a);
      });
      box.appendChild(jump);
    }

    deepdive.groups.forEach(function (g) {
      var sec = el('section', 'dd-group');
      sec.id = 'dd-' + g.id;
      sec.appendChild(el('h3', null, g.title));

      if (g.questions && g.questions.length) {
        var det = document.createElement('details');
        det.className = 'dd-questions';
        var sum = document.createElement('summary');
        sum.textContent = 'Guiding questions';
        det.appendChild(sum);
        var ul = el('ul', 'dd-qlist');
        g.questions.forEach(function (q) {
          ul.appendChild(el('li', null, q));
        });
        det.appendChild(ul);
        sec.appendChild(det);
      }

      if (g.note) sec.appendChild(el('p', 'dd-gnote', g.note));

      var strip = ddMeanwhileStrip(g.meanwhile, g.fun_overlaps);
      if (strip) sec.appendChild(strip);

      if (g.evidence) {
        var ev = el('div', 'dd-evidence');
        if (g.evidence.shows) {
          var p1 = el('p', null, '');
          p1.appendChild(el('strong', null, 'Evidence shows: '));
          p1.appendChild(document.createTextNode(g.evidence.shows));
          ev.appendChild(p1);
        }
        if (g.evidence.infer) {
          var p2 = el('p', null, '');
          p2.appendChild(el('strong', null, 'Historians infer: '));
          p2.appendChild(document.createTextNode(g.evidence.infer));
          ev.appendChild(p2);
        }
        if (g.evidence.unknown) {
          var p3 = el('p', null, '');
          p3.appendChild(el('strong', null, 'Still unknown: '));
          p3.appendChild(document.createTextNode(g.evidence.unknown));
          ev.appendChild(p3);
        }
        sec.appendChild(ev);
      }

      g.items.forEach(function (it) {
        var c = el('article', 'dd-item');
        c.id = 'dd-' + it.id;
        c.appendChild(el('h4', null, it.title));
        var by = el('p', 'dd-by', it.author);
        c.appendChild(by);
        var meta = el('div', 'dd-meta');
        if (it.date) meta.appendChild(el('span', 'dd-date', it.date));
        if (it.category) meta.appendChild(el('span', 'dd-cat', it.category));
        if (it.caution) {
          var caut = document.createElement('details');
          caut.className = 'dd-caution';
          var csum = document.createElement('summary');
          csum.textContent = '\u24d8 Read with care';
          caut.appendChild(csum);
          caut.appendChild(el('p', 'dd-caution-body', it.caution));
          meta.appendChild(caut);
        }
        if (meta.childNodes.length) c.appendChild(meta);
        c.appendChild(el('p', 'dd-line', it.line));
        var mwl = ddItemMeanwhile(it.meanwhile);
        if (mwl) c.appendChild(mwl);
        if (it.flag) c.appendChild(el('p', 'dd-flag', it.flag));
        var parts = it.links.filter(function (l) { return l.kind === 'part'; });
        it.links.forEach(function (l) { if (l.kind === 'primary') c.appendChild(ddLink('review dd-primary', l)); });
        if (parts.length) {
          if (it.links_heading) c.appendChild(el('p', 'dd-ph', it.links_heading));
          var row = el('div', 'dd-parts');
          parts.forEach(function (l) { row.appendChild(ddLink('dd-part', l)); });
          c.appendChild(row);
        }
        it.links.forEach(function (l) {
          if (l.kind === 'secondary') c.appendChild(ddLink('dd-sec', l));
        });
        // Quiet jump into Archaeology Finds for related artifacts
        var related = discoveryLinksForWriting(it.id);
        if (related.length) {
          var first = related[0];
          var jump = el('a', 'dd-leftbehind', 'See what they left behind');
          jump.href = 'archaeology/#disc-' + first.id;
          jump.addEventListener('click', function (e) {
            if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
            e.preventDefault();
            var fromLabel = (it.author && it.title) ? (it.author + ', ' + it.title) : (it.title || DD_LABEL);
            navigateOverlay('archaeology', {
              anchor: 'disc-' + first.id,
              openEvidence: true,
              back: snapshotBack('deepdive', 'dd-' + it.id, fromLabel)
            });
          });
          c.appendChild(jump);
        }
        sec.appendChild(c);
      });
      box.appendChild(sec);
    });
    var d = deepdive.checked ? new Date(deepdive.checked + 'T12:00:00') : null;
    $('ddChecked').textContent = d ? 'Links checked ' + d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) + '.' : '';
  }
  function archChipLabel(title) {
    var t = (title || '').split('\u00b7')[0].trim();
    if (t.indexOf('Ancient Israel') === 0) return 'Ancient Israel';
    if (t.indexOf('The world of the Gospels') === 0) return 'Gospels world';
    return t;
  }
  function renderArchaeology() {
    var box = $('archList');
    if (!discovery) return;
    box.textContent = '';
    $('archIntro').textContent = discovery.intro || '';
    var titleEl = $('archTitle');
    if (titleEl) titleEl.textContent = (discovery.label || ARCH_LABEL);

    var groups = discovery.groups || [];
    var by = discoveryByPeriod();
    if (groups.length) {
      var jump = el('nav', 'dd-jump');
      jump.setAttribute('aria-label', 'Jump to group');
      groups.forEach(function (g) {
        if (!(by[g.id] || []).length) return;
        var a = el('a', 'dd-chip', archChipLabel(g.title));
        a.href = '#arch-' + g.id;
        a.addEventListener('click', function (e) {
          e.preventDefault();
          var t = document.getElementById('arch-' + g.id);
          if (t) t.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
        jump.appendChild(a);
      });
      box.appendChild(jump);
    }
    groups.forEach(function (g) {
      var list = by[g.id] || [];
      if (!list.length) return;
      var sec = el('section', 'dd-group');
      sec.id = 'arch-' + g.id;
      sec.appendChild(el('h3', null, g.title));
      if (g.note) sec.appendChild(el('p', 'dd-gnote', g.note));
      var subgroups = g.subgroups || [];
      if (subgroups.length) {
        var bySub = {};
        list.forEach(function (it) {
          var sg = it.subgroup || '';
          if (!bySub[sg]) bySub[sg] = [];
          bySub[sg].push(it);
        });
        subgroups.forEach(function (sg) {
          var subItems = bySub[sg.id] || [];
          if (!subItems.length) return;
          var sub = el('p', 'arch-sub', sg.title);
          sub.id = 'arch-sub-' + sg.id;
          sec.appendChild(sub);
          subItems.forEach(function (it) {
            sec.appendChild(renderDiscoveryCard(it, { withWriteLink: true }));
          });
        });
      } else {
        list.forEach(function (it) {
          sec.appendChild(renderDiscoveryCard(it, { withWriteLink: true }));
        });
      }
      box.appendChild(sec);
    });
    var d = discovery.checked ? new Date(discovery.checked + 'T12:00:00') : null;
    $('archChecked').textContent = d ? 'Links checked ' + d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) + '.' : '';
  }

  var ddRoot = $('deepdive');
  var archRoot = $('archaeology');
  var ddTopBtn = $('ddTop');
  var DD_TOP_SHOW = 280;
  function ddPreferReducedMotion() {
    try { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; }
  }
  function activeOverlayRoot() {
    if (archRoot && !archRoot.hidden) return archRoot;
    if (ddRoot && !ddRoot.hidden) return ddRoot;
    return null;
  }
  function updateDdTopBtn() {
    if (!ddTopBtn) return;
    var root = activeOverlayRoot();
    if (!root) { ddTopBtn.hidden = true; return; }
    ddTopBtn.hidden = root.scrollTop < DD_TOP_SHOW;
  }
  function scrollActiveOverlayTop() {
    var root = activeOverlayRoot();
    if (!root) return;
    var behavior = ddPreferReducedMotion() ? 'auto' : 'smooth';
    if (typeof root.scrollTo === 'function') root.scrollTo({ top: 0, behavior: behavior });
    else root.scrollTop = 0;
  }
  if (ddTopBtn) {
    ddTopBtn.addEventListener('click', function () { scrollActiveOverlayTop(); });
  }
  ddRoot.addEventListener('scroll', updateDdTopBtn, { passive: true });
  if (archRoot) archRoot.addEventListener('scroll', updateDdTopBtn, { passive: true });

  // --- History-aware overlay navigation (browser back + in-app Back pill) ---
  var applyingHistory = false;
  var pendingBack = null; // {overlay,anchor,label,scroll} while showing a destination

  function histState() {
    try { return history.state && history.state.db ? history.state : null; } catch (e) { return null; }
  }
  function ensureHomeHist() {
    var st = histState();
    if (st) return;
    try {
      history.replaceState({ db: 1, overlay: null }, '', location.href);
    } catch (e) {}
  }
  function snapshotBack(overlay, anchor, label) {
    var root = overlay === 'archaeology' ? archRoot : ddRoot;
    return {
      overlay: overlay,
      anchor: anchor || null,
      label: label || (overlay === 'archaeology' ? ARCH_LABEL : DD_LABEL),
      scroll: root ? root.scrollTop : 0
    };
  }
  function saveCurrentOverlayScroll() {
    var st = histState();
    if (!st || !st.overlay || applyingHistory) return;
    var root = st.overlay === 'archaeology' ? archRoot : ddRoot;
    if (!root || root.hidden) return;
    var next = {
      db: 1,
      overlay: st.overlay,
      anchor: st.anchor || null,
      scroll: root.scrollTop,
      back: st.back || null
    };
    try { history.replaceState(next, '', location.href); } catch (e) {}
  }
  function updateBackPill(back) {
    pendingBack = back || null;
    [['ddBackWrap', 'ddBack'], ['archBackWrap', 'archBack']].forEach(function (pair) {
      var wrap = $(pair[0]), btn = $(pair[1]);
      if (!wrap || !btn) return;
      if (!pendingBack) {
        wrap.hidden = true;
        btn.textContent = '';
        return;
      }
      var label = pendingBack.label || (pendingBack.overlay === 'archaeology' ? ARCH_LABEL : DD_LABEL);
      btn.textContent = '\u2190 Back to ' + label;
      wrap.hidden = false;
    });
  }
  function hideOverlaysVisual() {
    ddRoot.hidden = true;
    if (archRoot) archRoot.hidden = true;
    document.body.style.overflow = '';
    updateBackPill(null);
    updateDdTopBtn();
  }
  function showOverlayVisual(kind, opts) {
    opts = opts || {};
    var isArch = kind === 'archaeology';
    if (isArch && !archRoot) return Promise.resolve();
    if (isArch) {
      ddRoot.hidden = true;
      archRoot.hidden = false;
    } else {
      if (archRoot) archRoot.hidden = true;
      ddRoot.hidden = false;
    }
    document.body.style.overflow = 'hidden';
    var root = isArch ? archRoot : ddRoot;
    if (!opts.restoreScroll) root.scrollTop = 0;
    updateBackPill(opts.back || null);
    updateDdTopBtn();
    var load = isArch
      ? ensureDiscovery().then(function () {
          if (discovery) renderArchaeology();
          else $('archList').textContent = 'Couldn\u2019t load Archaeology Finds. Check your connection and try again.';
        })
      : Promise.all([ensureDeepDive(), ensureDiscovery()]).then(function () {
          if (deepdive) renderDeepDive();
          else $('ddList').textContent = 'Couldn\u2019t load the Historic Writings list. Check your connection and try again.';
        });
    return load.then(function () {
      updateDdTopBtn();
      function place() {
        if (typeof opts.scroll === 'number') {
          root.scrollTop = opts.scroll;
        } else if (opts.anchor) {
          var t = document.getElementById(opts.anchor);
          if (t) {
            if (opts.openEvidence) {
              var det = t.querySelector('.dd-disc-ev');
              if (det) det.open = true;
            }
            t.scrollIntoView({ behavior: opts.instant ? 'auto' : 'smooth', block: 'start' });
          }
        }
        updateDdTopBtn();
        if (typeof opts.after === 'function') opts.after();
      }
      setTimeout(place, opts.instant ? 20 : 40);
    });
  }
  // Public open helpers (header / Escape / tests): push history unless applying popstate
  function openDeepDive(after) {
    navigateOverlay('deepdive', { after: after, fromHeader: true });
  }
  function openArchaeology(after) {
    navigateOverlay('archaeology', { after: after, fromHeader: true });
  }
  function navigateOverlay(kind, opts) {
    opts = opts || {};
    if (applyingHistory) {
      return showOverlayVisual(kind, opts);
    }
    ensureHomeHist();
    // Persist scroll on the entry we're leaving (Today or other overlay)
    var cur = histState();
    if (cur && cur.overlay) saveCurrentOverlayScroll();
    else {
      try {
        history.replaceState({ db: 1, overlay: null }, '', location.href);
      } catch (e) {}
    }
    var st = {
      db: 1,
      overlay: kind,
      anchor: opts.anchor || null,
      scroll: typeof opts.scroll === 'number' ? opts.scroll : 0,
      back: opts.back || null
    };
    try { history.pushState(st, '', location.href); } catch (e) {}
    return showOverlayVisual(kind, opts);
  }
  function applyHistState(st) {
    applyingHistory = true;
    try {
      if (!st || !st.overlay) {
        hideOverlaysVisual();
        return;
      }
      showOverlayVisual(st.overlay, {
        anchor: st.anchor || null,
        scroll: typeof st.scroll === 'number' ? st.scroll : undefined,
        back: st.back || null,
        instant: true,
        restoreScroll: typeof st.scroll === 'number'
      });
    } finally {
      // clear flag after paint/scroll settle
      setTimeout(function () { applyingHistory = false; }, 80);
    }
  }
  function closeOverlayViaHistory() {
    var st = histState();
    if (st && st.overlay && !applyingHistory) {
      try { history.back(); return; } catch (e) {}
    }
    hideOverlaysVisual();
    try {
      history.replaceState({ db: 1, overlay: null }, '', location.href);
    } catch (e2) {}
  }
  function closeDeepDive() { closeOverlayViaHistory(); }
  function closeArchaeology() { closeOverlayViaHistory(); }

  window.addEventListener('popstate', function (e) {
    var st = (e.state && e.state.db) ? e.state : { db: 1, overlay: null };
    applyHistState(st);
  });

  // ddBtn / archBtn are real links to static pages for crawlers and no-JS readers;
  // with JS, a plain click opens the overlay. Modified clicks still follow the link.
  $('ddBtn').addEventListener('click', function (e) {
    if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    openDeepDive();
  });
  $('ddBtn').addEventListener('keydown', function (e) {
    if (e.key === ' ') { e.preventDefault(); openDeepDive(); }
  });
  $('ddClose').addEventListener('click', closeDeepDive);
  if ($('archBtn')) {
    $('archBtn').addEventListener('click', function (e) {
      if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      openArchaeology();
    });
    $('archBtn').addEventListener('keydown', function (e) {
      if (e.key === ' ') { e.preventDefault(); openArchaeology(); }
    });
  }
  if ($('archClose')) $('archClose').addEventListener('click', closeArchaeology);
  function wireBackPill(id) {
    var btn = $(id);
    if (!btn) return;
    btn.addEventListener('click', function () {
      if (pendingBack) {
        try { history.back(); } catch (e) { applyHistState({ db: 1, overlay: pendingBack.overlay, anchor: pendingBack.anchor, scroll: pendingBack.scroll, back: null }); }
      }
    });
  }
  wireBackPill('ddBack');
  wireBackPill('archBack');
  if ($('ddBtn')) $('ddBtn').textContent = DD_LABEL;
  if ($('archBtn')) $('archBtn').textContent = ARCH_LABEL;

    $('prev').addEventListener('click', function () { location.hash = addDays(current, -1); });
  $('next').addEventListener('click', function () { location.hash = addDays(current, 1); });
  $('todayBtn').addEventListener('click', function () {
    history.replaceState(null, '', location.pathname + location.search);
    show(todayISO());
  });
  window.addEventListener('hashchange', function () {
    if (location.hash === '#parish') return; // old bookmarks/links to the parish card anchor
    show(isoFromHash() || current || todayISO());
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { if (!$('lightbox').hidden) closeLightbox(); else if (!$('favs').hidden) closeFavs(); else if (!$('prayers').hidden) closePrayers(); else if (archRoot && !archRoot.hidden) closeArchaeology(); else if (!$('deepdive').hidden) closeDeepDive(); return; }
    if (!$('lightbox').hidden || !$('favs').hidden || !$('prayers').hidden || !$('deepdive').hidden || (archRoot && !archRoot.hidden)) return;
    if (e.key === 'ArrowLeft') $('prev').click();
    if (e.key === 'ArrowRight') $('next').click();
  });

  try {
    window.DB_openDeepDive = openDeepDive;
    window.DB_openArchaeology = openArchaeology;
    window.DB_navigateOverlay = navigateOverlay;
  } catch (e) {}

  show(isoFromHash() || todayISO());
})();
