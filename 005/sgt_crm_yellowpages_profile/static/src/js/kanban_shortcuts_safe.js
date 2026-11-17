/** @odoo-module **/
/**
 * CRM-005 safe Update_061 draft — additive Odoo 19 Kanban quick links.
 * - Never put untrusted URLs directly into href before verifying http(s).
 * - Show Documents only after checking the current user's Documents permissions.
 * - No patching of Odoo's global card handler or global action services.
 */
import { rpc } from "@web/core/network/rpc";

(function () {
    "use strict";
    if (window.__sgtCRM005SafeLinksInstalled) return;
    window.__sgtCRM005SafeLinksInstalled = true;

    const CARD_SELECTOR = ".o_opportunity_kanban .o_kanban_record";
    const LINK_SELECTOR = ".o_opportunity_kanban .sgt_crm005_safe_link[data-sgt-crm005-kind]";
    const DOC_SELECTOR = ".o_opportunity_kanban .sgt_crm005_safe_folder[data-sgt-crm005-documents]";
    const RECORD_LINK_SELECTOR = "a.sgt_crm005_kanban_company[href]";
    const YP_HOSTS = /(^|\.)(trangvangvietnam\.com|trangvang\.vn|yellowpages\.vn|yellowpages\.com\.vn)$/i;
    const FB_HOSTS = /(^|\.)(facebook\.com|fb\.com|fb\.me|m\.facebook\.com)$/i;
    const ZALO_HOSTS = /(^|\.)(zalo\.me|zalo\.com|zaloapp\.com)$/i;
    let queued = false;
    const processed = new WeakSet();

    function validatedUrl(value, kind) {
        if (typeof value !== "string") return null;
        const input = value.trim();
        if (!input || /[\u0000-\u001f\u007f]/.test(input) || input.startsWith("//")) return null;
        const withScheme = /^https?:\/\//i.test(input)
            ? input
            : (/^(www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:[/:?#]|$)/i.test(input) ? `https://${input}` : null);
        if (!withScheme) return null;
        let url;
        try { url = new URL(withScheme); } catch (_) { return null; }
        if (!["http:", "https:"].includes(url.protocol) || !url.hostname || url.username || url.password) return null;
        if (kind === "yellowpages" && !YP_HOSTS.test(url.hostname)) return null;
        if (kind === "facebook" && !FB_HOSTS.test(url.hostname)) return null;
        if (kind === "zalo" && !ZALO_HOSTS.test(url.hostname)) return null;
        if (kind === "website" && (FB_HOSTS.test(url.hostname) || ZALO_HOSTS.test(url.hostname))) return null;
        return url.href;
    }

    function refreshLinks() {
        document.querySelectorAll(LINK_SELECTOR).forEach((link) => {
            if (link.dataset.sgtCrm005Ready) return;
            const candidates = [
                link.getAttribute("data-sgt-crm005-url"),
                link.getAttribute("data-sgt-crm005-alt"),
                link.getAttribute("data-sgt-crm005-alt2"),
            ];
            const href = candidates.map((candidate) => validatedUrl(candidate, link.dataset.sgtCrm005Kind)).find(Boolean);
            link.dataset.sgtCrm005Ready = href ? "1" : "0";
            if (href) {
                link.setAttribute("href", href);
                link.setAttribute("target", "_blank");
                link.setAttribute("rel", "noopener noreferrer");
            }
        });
    }

    async function refreshDocuments() {
        const pending = Array.from(document.querySelectorAll(DOC_SELECTOR))
            .filter((button) => !processed.has(button));
        const idsByButton = new Map();
        pending.forEach((button) => {
            processed.add(button);
            const card = button.closest(CARD_SELECTOR);
            const path = card?.querySelector(RECORD_LINK_SELECTOR)?.getAttribute("href") || "";
            const match = /^\/odoo\/crm\.lead\/([1-9]\d*)$/.exec(path);
            if (match) idsByButton.set(button, Number(match[1]));
        });
        const ids = [...new Set(idsByButton.values())];
        // Batch the request instead of making a separate RPC per Kanban card.
        for (let start = 0; start < ids.length; start += 100) {
            const batch = ids.slice(start, start + 100);
            try {
                const visible = await rpc("/web/dataset/call_kw/crm.lead/crm005_kanban_documents_available", {
                    model: "crm.lead", method: "crm005_kanban_documents_available",
                    args: [batch], kwargs: {},
                });
                const allowed = new Set((visible || []).map(Number));
                for (const [button, leadId] of idsByButton) {
                    if (batch.includes(leadId) && allowed.has(leadId) && button.isConnected) {
                        button.removeAttribute("hidden");
                        button.dataset.sgtCrm005DocReady = "1";
                    }
                }
            } catch (_) {
                // Permission mismatch, offline or missing folder: hide icon;
                // never disclose folder metadata or affect Kanban rendering.
            }
        }
    }

    document.addEventListener("click", (event) => {
        const link = event.target?.closest?.(LINK_SELECTOR);
        if (!link) return;
        if (!link.href || link.dataset.sgtCrm005Ready !== "1") {
            event.preventDefault();
            event.stopImmediatePropagation();
            return;
        }
        // Browser follows verified href and target=_blank natively.
        // The Kanban card's own click handler must not also open the Deal form.
        event.stopPropagation();
    }, true);

    function scan() {
        queued = false;
        refreshLinks();
        void refreshDocuments();
    }
    function schedule() {
        if (queued) return;
        queued = true;
        setTimeout(scan, 80);
    }
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", schedule, { once: true });
    } else {
        schedule();
    }
    const observer = new MutationObserver((changes) => {
        if (changes.some((change) => change.addedNodes.length || change.removedNodes.length)) schedule();
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
})();
