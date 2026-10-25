(function () {
  'use strict';
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
    getCal(+iso.slice(0, 4)).then(function (cal) {
      if (current !== iso) return;
      renderDay(cal[iso] || []);
      dayInfo[iso] = cal[iso] || [];
      renderParish(iso);
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

  function refsList(list) {
    var ul = el('ul', 'refs');
    list.forEach(function (r) {
      var li = el('li');
      li.appendChild(el('span', 'h', r.heading));
      li.appendChild(el('span', 'c', r.citation || '\u2014'));
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
    if (day.title) body.appendChild(el('h2', null, day.title));
    day.masses.forEach(function (m) {
      if (m.name) body.appendChild(el('h3', null, m.name));
      if (m.readings && m.readings.length) body.appendChild(refsList(m.readings));
    });
  }

  function weekStart(iso) {
    var d = new Date(iso + 'T12:00:00Z');
    return addDays(iso, -d.getUTCDay());
  }

  function renderMovie(iso) {
    var card = $('movie');
    var ws = weekStart(iso);
    var m = movies && movies.weeks && movies.weeks.filter(function (w) { return w.week_start === ws; })[0];
    if (!m) { card.hidden = true; return; }
    $('movieWeek').textContent = 'Week of ' + new Date(ws + 'T12:00:00Z').toLocaleDateString('en-US',
      { timeZone: 'UTC', month: 'long', day: 'numeric' }) + (m.type === 'show' ? ' \u00b7 Show' : '');
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

  $('prev').addEventListener('click', function () { location.hash = addDays(current, -1); });
  $('next').addEventListener('click', function () { location.hash = addDays(current, 1); });
  $('todayBtn').addEventListener('click', function () {
    history.replaceState(null, '', location.pathname + location.search);
    show(todayISO());
  });
  window.addEventListener('hashchange', function () {
    if (location.hash === '#parish') return;
    show(isoFromHash() || current || todayISO());
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { if (!$('lightbox').hidden) closeLightbox(); else if (!$('favs').hidden) closeFavs(); return; }
    if (!$('lightbox').hidden || !$('favs').hidden) return;
    if (e.key === 'ArrowLeft') $('prev').click();
    if (e.key === 'ArrowRight') $('next').click();
  });

  show(isoFromHash() || todayISO());
})();
