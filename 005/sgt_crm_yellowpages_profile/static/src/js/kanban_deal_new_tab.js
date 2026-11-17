/** @odoo-module **/
/**
 * CRM-005 Update_059: open the exact Deal in a new tab from its Kanban card.
 *
 * Odoo 19 KanbanCompiler turns <a type="open"> without an href into href="#"
 * and routes normal clicks through its record-opening handler. We now expose a
 * real link (/odoo/crm.lead/ID) but keep native Odoo type="open" on plain clicks.
 *
 * Scoped to the opportunity Kanban only. Do not patch global KanbanRecord,
 * Odoo's router, or other modules. No RPC, ORM field, or DB schema changes.
 */
(function () {
    "use strict";
    if (window.__sgtCRM005KanbanNewTabInstalled) {
        return;
    }
    window.__sgtCRM005KanbanNewTabInstalled = true;

    const CARD = ".o_opportunity_kanban .o_kanban_record";
    const COMPANY_LINK = "a.sgt_crm005_kanban_company[href]";
    const ACTION_CONTROL = [
        "a", "button", "input", "select", "textarea", "label",
        "[role='button']", "[contenteditable]", ".dropdown", ".oe_kanban_action",
        "[data-bs-toggle]", ".o_record_selection_tooltip",
    ].join(",");

    function infoFromTarget(target) {
        if (!target || typeof target.closest !== "function") {
            return null;
        }
        const card = target.closest(CARD);
        if (!card) {
            return null;
        }
        const link = card.querySelector(COMPANY_LINK);
        if (!link) {
            return null;
        }
        // Prevent accidentally opening another host / an untrusted external URL.
        const path = link.getAttribute("href") || "";
        if (!/^\/odoo\/crm\.lead\/[1-9]\d*$/.test(path)) {
            return null;
        }
        return { card, link, url: new URL(path, window.location.origin).href };
    }

    function isOtherControl(target, link) {
        const control = target.closest(ACTION_CONTROL);
        return control && control !== link;
    }

    function openInNewTab(info, event) {
        event.preventDefault();
        event.stopImmediatePropagation();
        // Synchronous user-gesture call: popup blockers generally allow it.
        window.open(info.url, "_blank", "noopener,noreferrer");
    }

    document.addEventListener("click", function (event) {
        if (event.defaultPrevented || event.button !== 0 || event.altKey || event.shiftKey) {
            return;
        }
        const info = infoFromTarget(event.target);
        if (!info || isOtherControl(event.target, info.link)) {
            return;
        }
        const insideCompanyLink = info.link.contains(event.target);
        if (event.ctrlKey || event.metaKey) {
            if (insideCompanyLink) {
                // Leave browser's standard Ctrl/Cmd+Click to open the REAL href.
                // Stop Odoo's type="open" handler and the global router intercept.
                event.stopImmediatePropagation();
            } else {
                // The remainder of the card is not an HTML link: open it explicitly.
                openInNewTab(info, event);
            }
        } else if (insideCompanyLink) {
            // Ordinary click: avoid browser navigation/duplicate router action.
            // Allow Odoo's type="open" handler to handle the form normally.
            event.preventDefault();
        }
    }, true);

    document.addEventListener("auxclick", function (event) {
        if (event.defaultPrevented || event.button !== 1 || event.altKey || event.shiftKey) {
            return;
        }
        const info = infoFromTarget(event.target);
        if (!info || isOtherControl(event.target, info.link)) {
            return;
        }
        if (info.link.contains(event.target)) {
            // Native middle click on <a href="/odoo/crm.lead/ID">.
            event.stopImmediatePropagation();
        } else {
            openInNewTab(info, event);
        }
    }, true);
})();
