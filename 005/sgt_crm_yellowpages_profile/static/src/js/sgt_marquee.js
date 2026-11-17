/* CRM-005 Update_013 (+ Update_019, Update_037): "read the cut-off text" on hover.
 *
 * Plain script (no import/export, no Odoo module, no RPC, no data access).
 * When the mouse rests on a text that is wider than its box (an input of the Yellow Pages
 * profile card, or a truncated line of a Kanban card) inside an element marked with the
 * class `sgt_marq`, the text slides slowly to the left until its last characters are shown,
 * waits, slides back, and repeats until the mouse leaves.
 * Only the horizontal scroll position (scrollLeft) is touched; the content is never changed.
 * Any error is swallowed: the worst case is that a text does not move.
 *
 * Update_037 (Kanban): hovering anywhere within a CRM opportunity card animates
 * its overflowed company name; leaving the whole card stops/resets it. Existing
 * form-field behavior remains unchanged.
 *
 * Update_019 (editing): the moment the user clicks into a text box (or tabs into it) the
 * movement stops for good and the text STAYS where it is, so the caret lands exactly where the
 * click was and the user can edit.  While a text box has the focus it never slides again, however
 * the mouse moves over it, leaves or comes back.  After the focus is gone it slides on hover again. */
(function () {
    'use strict';
    var SPEED = 40;        /* pixels per second: slow enough to read */
    var START_DELAY = 350; /* ms before moving once the mouse rests on the text */
    var HOLD = 700;        /* ms pause at both ends */
    var RUN_CLASS = 'sgt-marq-run';

    if (window.__sgtMarqueeInstalled) {
        return;
    }
    window.__sgtMarqueeInstalled = true;

    var reduce = false;
    try {
        reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (e) { reduce = false; }

    var active = null; /* {el, card, raf, timer} */

    function isOverflowing(el) {
        if (!el || el.nodeType !== 1) { return false; }
        if (el.scrollWidth - el.clientWidth <= 2) { return false; }
        if (el.tagName === 'INPUT') {
            var t = (el.getAttribute('type') || 'text').toLowerCase();
            return ['text', 'email', 'url', 'tel', 'search', ''].indexOf(t) !== -1;
        }
        var ox = window.getComputedStyle(el).overflowX;
        return ox === 'hidden' || ox === 'auto' || ox === 'scroll';
    }

    /* A Kanban card is the hover trigger, not just its company-name element.
       Scope the special case tightly to CRM opportunities so legacy form-field
       marquees continue to react only to direct hover. */
    function findCompanyCard(node) {
        if (!node || node.nodeType !== 1 || !node.closest) { return null; }
        var card = node.closest('.o_kanban_record');
        if (!card || !card.closest('.o_opportunity_kanban')) { return null; }
        return card.querySelector('.sgt_crm005_kanban_company_name.sgt_marq') ? card : null;
    }

    /* innermost overflowing element between the hovered node and the marked scope */
    function findTarget(node) {
        if (!node || node.nodeType !== 1) { return null; }
        var card = findCompanyCard(node);
        if (card) {
            var company = card.querySelector('.sgt_crm005_kanban_company_name.sgt_marq');
            return isOverflowing(company) ? company : null;
        }
        var scope = node.closest('.sgt_marq');
        if (!scope) { return null; }
        var el = node;
        while (el) {
            if (isOverflowing(el)) { return el; }
            if (el === scope) { break; }
            el = el.parentElement;
        }
        /* hovered a field wrapper: look for the input inside it */
        var inner = node.querySelector && node.querySelector('input');
        if (inner && isOverflowing(inner)) { return inner; }
        return null;
    }

    /* a text box the user can type into */
    function isEditable(el) {
        return !!el && el.nodeType === 1 &&
            (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable);
    }

    /* true while the element (or something inside it) has the keyboard focus */
    function hasFocus(el) {
        var fe = document.activeElement;
        return !!fe && (fe === el || el.contains(fe));
    }

    /* keep=true: stay where the text is now (the user is about to edit it);
       otherwise the text goes back to its start. */
    function stop(keep) {
        if (!active) { return; }
        try {
            if (active.raf) { window.cancelAnimationFrame(active.raf); }
            if (active.timer) { window.clearTimeout(active.timer); }
            active.el.classList.remove(RUN_CLASS);
            if (!keep && !hasFocus(active.el)) { active.el.scrollLeft = 0; }
        } catch (e) { /* ignore */ }
        active = null;
    }

    function run(state) {
        var el = state.el;
        var max = el.scrollWidth - el.clientWidth;
        if (max <= 2) { stop(); return; }
        var dur = Math.max(1200, (max / SPEED) * 1000);
        var forward = true;
        var t0 = 0;
        el.classList.add(RUN_CLASS);

        function frame(now) {
            if (active !== state) { return; }
            if (!t0) { t0 = now; }
            var k = Math.min(1, (now - t0) / dur);
            el.scrollLeft = (forward ? k : 1 - k) * max;
            if (k < 1) {
                state.raf = window.requestAnimationFrame(frame);
            } else {
                forward = !forward;
                t0 = 0;
                state.raf = 0;
                state.timer = window.setTimeout(function () {
                    state.timer = 0;
                    if (active === state) { state.raf = window.requestAnimationFrame(frame); }
                }, HOLD);
            }
        }
        state.raf = window.requestAnimationFrame(frame);
    }

    function onOver(ev) {
        try {
            if (reduce || ev.buttons) { return; }
            var el = findTarget(ev.target);
            if (!el) { return; }
            if (hasFocus(el)) { return; }   /* being edited: never move it */
            if (active && active.el === el) { return; }
            stop();
            var state = { el: el, card: findCompanyCard(ev.target), raf: 0, timer: 0 };
            active = state;
            state.timer = window.setTimeout(function () {
                state.timer = 0;
                if (active === state) { run(state); }
            }, START_DELAY);
        } catch (e) { /* ignore */ }
    }

    function onOut(ev) {
        try {
            if (!active) { return; }
            var to = ev.relatedTarget;
            if (active.card) {
                /* Ignore movements between logo, text, tags and other elements
                   of this same card; stop only once the pointer leaves the card. */
                if (to && active.card.contains(to)) { return; }
                if (ev.target === active.card || active.card.contains(ev.target)) { stop(); }
                return;
            }
            if (to && active.el.contains(to)) { return; }
            if (ev.target === active.el || active.el.contains(ev.target)) { stop(); }
        } catch (e) { /* ignore */ }
    }

    function onStop() {
        try { stop(); } catch (e) { /* ignore */ }
    }

    /* click / tab into a text: freeze it exactly where it is (no jump back to the start) */
    function onEdit(ev) {
        try {
            var hit = ev.target && ev.target.nodeType === 1 ? ev.target : null;
            if (active && hit && isEditable(active.el) &&
                    (hit === active.el || active.el.contains(hit) || hit.contains(active.el))) {
                stop(true);
            } else {
                stop();
            }
        } catch (e) { /* ignore */ }
    }

    document.addEventListener('mouseover', onOver, true);
    document.addEventListener('mouseout', onOut, true);
    document.addEventListener('mousedown', onEdit, true);
    document.addEventListener('keydown', onEdit, true);
    document.addEventListener('dragstart', onStop, true);
    document.addEventListener('focusin', onEdit, true);
    document.addEventListener('visibilitychange', onStop, true);
})();
