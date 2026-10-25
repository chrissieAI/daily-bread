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
    getCal(+iso.slice(0, 4)).then(function (cal) {
      if (current !== iso) return;
      renderDay(cal[iso] || []);
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

  fetch('data/movies.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : {}; })
    .catch(function () { return {}; })
    .then(function (data) { movies = data || {}; if (current) renderMovie(current); });

  fetch('readings.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : {}; })
    .catch(function () { return {}; })
    .then(function (data) { readings = data || {}; if (current) renderReadings(current); });

  $('prev').addEventListener('click', function () { location.hash = addDays(current, -1); });
  $('next').addEventListener('click', function () { location.hash = addDays(current, 1); });
  $('todayBtn').addEventListener('click', function () {
    history.replaceState(null, '', location.pathname + location.search);
    show(todayISO());
  });
  window.addEventListener('hashchange', function () { show(isoFromHash() || todayISO()); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft') $('prev').click();
    if (e.key === 'ArrowRight') $('next').click();
  });

  show(isoFromHash() || todayISO());
})();
