/** @odoo-module **/
// Xinyang Home: B2B experience with Odoo product data. English by default, Vietnamese on request.
import {
    Component,
    onMounted,
    onPatched,
    onWillStart,
    onWillUnmount,
    useEffect,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { VI } from "./i18n";

// Home Manager (Settings > Users > Access Rights > Home) and Settings Administrators see the add/edit buttons.
// The server enforces the same rule (ir.model.access); the buttons are only a convenience.
const MANAGER_GROUP = "sgt_xinyang_welcome.group_home_manager";
const HEATMAP_GROUP = "sgt_xinyang_welcome.group_home_heatmap"; // Settings > Users > Home > Heat Map; Home Managers inherit it
const DASHBOARD_GROUP = "sgt_xinyang_welcome.group_home_dashboard"; // Settings > Users > Home > Dashboard; Home Managers inherit it
const ADMIN_GROUP = "base.group_system";
const MAP_URL = "/sgt_home/map";
const KPI_URL = "/sgt_home/kpi";
// Sections and cards fade up the first time they scroll into view (Update_017). Plain markers on existing elements: the template is untouched.
const REVEAL_SELECTORS = [
    ".credentials-grid > .cred", ".home-extra-fact", ".intro-grid > *", ".value-card", ".home-campaign-card",
    ".section-topline", ".solution-card", ".technical-copy", ".industry-row", ".filter-row", ".product-item",
    ".approach-lead", ".approach-steps > *", ".contact-copy", "form.inquiry",
].join(","); // server page; it checks the same right again
const ASSETS = "/sgt_xinyang_welcome/static/src/home/assets/";
const IMG = "/sgt_xinyang_welcome/static/src/img/";
const AUTOPLAY_MS = 6800;
const DEFAULT_IMAGE_SECONDS = 30; // used until Home > Settings is read, or when it cannot be read
const LANG_KEY = "sgt_xinyang_home_lang";
const LANGS = { en: "en_US", vi: "vi_VN" };
const PRODUCT_FIELDS = ["name", "code", "subtitle", "description", "category", "has_image", "write_date"];

function savedLang() {
    try {
        const value = window.localStorage.getItem(LANG_KEY);
        return value === "vi" ? "vi" : "en";
    } catch {
        return "en";
    }
}
const SAFE_URL = /^(https?:\/\/\S+|\/(?!\/)\S*)$/i;
const SHOWCASE = [
    { image: "poster_silencer.png", name: "Industrial silencer systems" },
    { image: "poster_thermal.png", name: "Temperature-sensing air outlets" },
    { image: "poster_fire.png", name: "Fire and smoke protection" },
];
const CATEGORY_NAMES = {
    air: "AIR DISTRIBUTION",
    silencer: "ACOUSTIC SOLUTIONS",
    fire: "FIRE & SMOKE CONTROL",
    other: "OTHER EQUIPMENT",
};

export class SgtHome extends Component {
    static template = "sgt_xinyang_welcome.Home";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.rootRef = useRef("home");
        this.action = useService("action");
        this.state = useState({
            slides: [], facts: [], products: [],
            heroIndex: 0, category: "all", menuOpen: false,
            selectedProduct: null, canManage: false, canMap: false, canKpi: false, view: "home", mapSrc: "", kpiSrc: "", loaded: false,
            formResult: "", paused: false, lang: savedLang(),
            galleries: {}, imageSeconds: DEFAULT_IMAGE_SECONDS, imgIndex: 0, imgTick: 0, imgHold: false,
        });
        this.timer = null;
        this.closeRef = useRef("productClose");
        this.mapRef = useRef("mapFrame");
        this.kpiRef = useRef("kpiFrame");
        this.opener = null;
        // capture phase: Odoo's hotkey service stops Escape before a bubbling listener would see it
        useExternalListener(window, "keydown", (ev) => this.onKeydown(ev), { capture: true });
        // Automatic picture change in the product popup (seconds come from Home > Settings).
        useEffect(
            () => {
                if (!this.imageAutoplayActive || this.state.imgHold) { return; }
                const id = setTimeout(() => {
                    this.state.imgIndex = (this.state.imgIndex + 1) % this.gallery.length;
                }, this.imageSeconds * 1000);
                return () => clearTimeout(id);
            },
            () => [this.state.selectedProduct && this.state.selectedProduct.id, this.state.imgIndex,
                this.state.imgTick, this.state.imgHold, this.state.imageSeconds, this.state.galleries]
        );
        useEffect(
            () => {
                if (this.state.selectedProduct && this.closeRef.el) {
                    this.closeRef.el.focus();
                }
            },
            () => [Boolean(this.state.selectedProduct)]
        );
        this.reducedMotion = Boolean(window.matchMedia &&
            window.matchMedia("(prefers-reduced-motion: reduce)").matches);
        onWillStart(async () => {
            const [slides, facts, products, images, setting, manager, settingsAdmin, heatmap, dashboard] = await Promise.all([
                // (the last answer is the Heat Map right)
                this.orm.searchRead("sgt.home.slide", [],
                    ["name", "tag", "text", "button_label", "button_url", "theme", "has_image", "write_date"],
                    { order: "sequence, id" }),
                this.orm.searchRead("sgt.home.fact", [], ["name", "value", "accent"],
                    { order: "sequence, id" }),
                this.fetchProducts(this.state.lang),
                // Extra pictures and Home settings must never stop Home from opening.
                this.orm.searchRead("sgt.home.product.image", [], ["product_id", "write_date"],
                    { order: "sequence, id" }).catch(() => []),
                this.orm.searchRead("sgt.home.setting", [], ["autoplay_seconds"], { limit: 1 }).catch(() => []),
                user.hasGroup(MANAGER_GROUP),
                user.hasGroup(ADMIN_GROUP),
                user.hasGroup(HEATMAP_GROUP),
                user.hasGroup(DASHBOARD_GROUP),
            ]);
            this.state.slides = slides;
            this.state.facts = facts;
            this.state.products = products;
            this.state.galleries = this.groupImages(images);
            if (setting && setting.length && Number.isFinite(Number(setting[0].autoplay_seconds))) {
                this.state.imageSeconds = Number(setting[0].autoplay_seconds);
            }
            this.state.canManage = Boolean(manager || settingsAdmin);
            this.state.canMap = Boolean(heatmap || settingsAdmin);
            this.state.canKpi = Boolean(dashboard || settingsAdmin);
            this.state.loaded = true;
        });
        onMounted(() => {
            if (!this.reducedMotion) {
                this.timer = setInterval(() => this.tick(), AUTOPLAY_MS);
            }
            this.setupReveal();
        });
        onPatched(() => this.scanReveal());
        onWillUnmount(() => {
            if (this.revealObserver) {
                this.revealObserver.disconnect();
                this.revealObserver = null;
            }
            if (this.timer) {
                clearInterval(this.timer);
                this.timer = null;
            }
        });
    }

    // ---- language (EN default / VI) ---------------------------------------
    // tr() translates the fixed interface text; product text comes from Odoo in the chosen language.
    tr(text) {
        if (this.state.lang !== "vi") { return text; }
        return Object.prototype.hasOwnProperty.call(VI, text) ? VI[text] : text;
    }
    async fetchProducts(lang) {
        const options = { order: "sequence, id", context: { lang: LANGS[lang] || LANGS.en } };
        try {
            return await this.orm.searchRead("sgt.home.product", [], PRODUCT_FIELDS, options);
        } catch (error) {
            if (lang === "en") { throw error; }
            // Vietnamese not installed or not readable: show the English text instead of a blank page.
            return this.orm.searchRead("sgt.home.product", [], PRODUCT_FIELDS,
                { order: "sequence, id", context: { lang: LANGS.en } });
        }
    }
    async setLang(ev) {
        const lang = ev.currentTarget.dataset.lang === "vi" ? "vi" : "en";
        if (lang === this.state.lang) { return; }
        this.state.lang = lang;
        try { window.localStorage.setItem(LANG_KEY, lang); } catch { /* storage may be blocked */ }
        this.syncMapLang(lang);
        this.syncKpiLang(lang);
        const openId = this.state.selectedProduct && this.state.selectedProduct.id;
        let products;
        try {
            products = await this.fetchProducts(lang);
        } catch {
            return; // keep the products already on screen; the interface text still switched
        }
        if (this.state.lang !== lang) { return; } // a newer click already won
        this.state.products = products;
        if (openId) {
            this.state.selectedProduct = products.find((p) => p.id === openId) || null;
        }
    }
    // ---- product popup: pictures and navigation -------------------------------
    groupImages(rows) {
        const groups = {};
        for (const row of rows || []) {
            const pid = Array.isArray(row.product_id) ? row.product_id[0] : row.product_id;
            (groups[pid] = groups[pid] || []).push(row);
        }
        return groups;
    }
    // Main picture first, then the extra pictures in their order. A product without any picture shows the logo.
    get gallery() {
        const product = this.state.selectedProduct;
        if (!product) { return []; }
        const items = [];
        const v = this.productVersion(product);
        if (product.has_image) {
            items.push({ key: "main", thumb: `/web/image/sgt.home.product/${product.id}/image/128x128?unique=${v}`,
                full: `/web/image/sgt.home.product/${product.id}/image/1024x1024?unique=${v}` });
        }
        for (const extra of this.state.galleries[product.id] || []) {
            const ev = String(extra.write_date || "").replace(/\D/g, "");
            items.push({ key: "img" + extra.id, thumb: `/web/image/sgt.home.product.image/${extra.id}/image/128x128?unique=${ev}`,
                full: `/web/image/sgt.home.product.image/${extra.id}/image/1024x1024?unique=${ev}` });
        }
        if (!items.length) { items.push({ key: "logo", thumb: this.logoXinyang, full: this.logoXinyang }); }
        return items;
    }
    get currentImage() {
        const list = this.gallery;
        return list[Math.min(this.state.imgIndex, list.length - 1)] || { full: this.logoXinyang };
    }
    get imageSeconds() {
        const n = Number(this.state.imageSeconds);
        return Number.isFinite(n) && n > 0 ? n : 0;
    }
    get imageAutoplayActive() {
        return Boolean(this.state.selectedProduct) && this.gallery.length > 1 && this.imageSeconds > 0 && !this.reducedMotion;
    }
    get imageBarKey() {
        return [this.state.selectedProduct && this.state.selectedProduct.id, this.state.imgIndex, this.state.imgTick].join("-");
    }
    get imageBarStyle() { return `animation-duration:${this.imageSeconds}s`; }
    resetImages() { this.state.imgIndex = 0; this.state.imgTick += 1; this.state.imgHold = false; }
    setImage(ev) {
        const i = Number(ev.currentTarget.dataset.index);
        if (i >= 0 && i < this.gallery.length) { this.state.imgIndex = i; this.state.imgTick += 1; }
    }
    prevImage() { this.stepImage(-1); }
    nextImage() { this.stepImage(1); }
    stepImage(delta) {
        const n = this.gallery.length;
        if (n < 2) { return; }
        this.state.imgIndex = (((this.state.imgIndex + delta) % n) + n) % n;
        this.state.imgTick += 1;
    }
    holdImages() { this.state.imgHold = true; }
    releaseImages() { this.state.imgHold = false; }
    get productNav() {
        const list = this.visibleProducts;
        const current = this.state.selectedProduct;
        if (!current || list.length < 2) { return null; }
        const i = list.findIndex((p) => p.id === current.id);
        if (i < 0) { return null; }
        const n = list.length;
        return { prev: list[(i - 1 + n) % n], next: list[(i + 1) % n], pos: i + 1, total: n };
    }
    get catalogUrl() { return ASSETS + "xinyang_catalog.pdf"; }
    get logoXinyang() { return IMG + "logo_xinyang.png"; }
    get logoJoint() { return IMG + "logo_saigontrade_xinyang_v3.png"; }
    get heroImageUrl() { return ASSETS + SHOWCASE[this.state.heroIndex].image; }
    get heroName() { return this.tr(SHOWCASE[this.state.heroIndex].name); }
    get heroIndexText() { return String(this.state.heroIndex + 1).padStart(2, "0"); }
    get visibleProducts() {
        return this.state.category === "all" ? this.state.products :
            this.state.products.filter((p) => p.category === this.state.category);
    }
    categoryName(key) { return this.tr(CATEGORY_NAMES[key] || "PRODUCT SERIES"); }
    heroTabClass(i) { return Number(i) === this.state.heroIndex ? "hero-tab active" : "hero-tab"; }
    tick() {
        if (!this.state.paused && !document.hidden && !this.state.selectedProduct) {
            this.nextHero();
        }
    }
    goHero(i) { this.state.heroIndex = ((i % SHOWCASE.length) + SHOWCASE.length) % SHOWCASE.length; }
    setHero(ev) { this.goHero(Number(ev.currentTarget.dataset.index)); }
    prevHero() { this.goHero(this.state.heroIndex - 1); }
    nextHero() { this.goHero(this.state.heroIndex + 1); }
    pause() { this.state.paused = true; }
    resume() { this.state.paused = false; }
    toggleMenu() { this.state.menuOpen = !this.state.menuOpen; }
    // ---- Scroll reveal (Update_017) ------------------------------------------------------------------------
    // Elements below the fold start transparent (only while data-rv-on is set on the root) and rise in when they enter the screen.
    // Without IntersectionObserver, or when the system asks for reduced motion, nothing is hidden and nothing moves.
    setupReveal() {
        const root = this.rootRef.el;
        if (!root || this.reducedMotion || typeof IntersectionObserver === "undefined") { return; }
        this.revealObserver = new IntersectionObserver((entries) => {
            const hits = entries.filter((e) => e.isIntersecting).sort((a, b) =>
                (a.boundingClientRect.top - b.boundingClientRect.top) || (a.boundingClientRect.left - b.boundingClientRect.left));
            hits.forEach((entry, i) => {   // elements that appear together arrive one after another
                entry.target.style.setProperty("--rv-d", `${Math.min(i, 6) * 70}ms`);
                entry.target.setAttribute("data-in", "");
                this.revealObserver.unobserve(entry.target);
            });
        }, { threshold: 0, rootMargin: "0px 0px -8% 0px" });
        root.setAttribute("data-rv-on", "1");
        this.scanReveal();
    }
    scanReveal() {
        const root = this.rootRef.el;
        if (!this.revealObserver || !root) { return; }
        for (const el of root.querySelectorAll(REVEAL_SELECTORS)) {
            if (!el.hasAttribute("data-rv")) {
                el.setAttribute("data-rv", "");
                this.revealObserver.observe(el);
            }
        }
    }

    // ---- Heat Map (XINYANG MAP) ---------------------------------------------------
    // Opens the map page (same origin, inside this Home) in place of the Home sections. Only people with the right see the link.
    openMap(ev) {
        ev.preventDefault();
        if (!this.state.canMap) { return; }
        this.state.menuOpen = false;
        this.state.selectedProduct = null;
        this.state.mapSrc = `${MAP_URL}?lang=${this.state.lang}`;
        this.state.view = "map";
    }
    // Dashboard (4 main KPIs): same idea as the map, a page of this server shown in place of the Home sections.
    openKpi(ev) {
        ev.preventDefault();
        if (!this.state.canKpi) { return; }
        this.state.menuOpen = false;
        this.state.selectedProduct = null;
        if (this.state.view !== "kpi") {
            this.state.kpiSrc = `${KPI_URL}?lang=${this.state.lang}`;
            this.state.view = "kpi";
        }
    }
    syncKpiLang(lang) {
        try {
            const api = this.kpiRef.el && this.kpiRef.el.contentWindow && this.kpiRef.el.contentWindow.XINYANG_KPI;
            if (api && typeof api.setLang === "function") { api.setLang(lang); }
        } catch { /* the frame is still loading: it opened with ?lang= already */ }
    }
    // The map keeps its own state (filters, zoom): switch only its language, do not reload the frame.
    syncMapLang(lang) {
        try {
            const api = this.mapRef.el && this.mapRef.el.contentWindow && this.mapRef.el.contentWindow.XINYANG_I18N;
            if (api && typeof api.setLang === "function") { api.setLang(lang, { noSave: true }); }
        } catch { /* the frame is still loading: it opened with ?lang= already */ }
    }
    onNavigate(ev) {
        const target = ev.currentTarget.getAttribute("href") || "";
        if (!/^#[a-z0-9_-]+$/i.test(target)) { return; }
        ev.preventDefault();
        this.state.menuOpen = false;
        if (this.state.view !== "home") {
            this.state.view = "home";
            setTimeout(() => this.rootRef.el?.querySelector(target)?.scrollIntoView(), 60);
            return;
        }
        this.rootRef.el?.querySelector(target)?.scrollIntoView({ behavior: this.reducedMotion ? "instant" : "smooth" });
    }
    onFilter(ev) { this.state.category = ev.currentTarget.dataset.category || "all"; }
    openSolution(ev) {
        ev.preventDefault();
        this.state.category = ev.currentTarget.dataset.category || "all";
        this.rootRef.el?.querySelector("#products")?.scrollIntoView({ behavior: "smooth" });
    }
    productVersion(product) { return String(product.write_date || "").replace(/\D/g, ""); }
    // Grid thumbnails are resized by the server (560 px); the enlarged view uses the full picture.
    thumbUrl(product) {
        if (!product || !product.has_image) { return this.logoXinyang; }
        return `/web/image/sgt.home.product/${product.id}/image/560x560?unique=${this.productVersion(product)}`;
    }
    slideImageUrl(slide) {
        const version = String(slide.write_date || "").replace(/\D/g, "");
        return `/web/image/sgt.home.slide/${slide.id}/image?unique=${version}`;
    }
    // ---- product details (enlarged view) ---------------------------------
    openProduct(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        const product = this.state.products.find((p) => p.id === id) || null;
        if (product) {
            this.opener = ev.currentTarget;
            this.resetImages();
            this.state.selectedProduct = product;
        }
    }
    closeProduct() {
        if (!this.state.selectedProduct) { return; }
        this.state.selectedProduct = null;
        this.resetImages();
        const opener = this.opener;
        this.opener = null;
        if (opener && opener.isConnected) { opener.focus(); }
    }
    onBackdrop(ev) {
        if (ev.target === ev.currentTarget) { this.closeProduct(); }
    }
    productPrev() { this.stepProduct(-1); }
    productNext() { this.stepProduct(1); }
    stepProduct(delta) {
        const list = this.visibleProducts;
        const current = this.state.selectedProduct;
        if (!current || list.length < 2) { return; }
        const i = list.findIndex((p) => p.id === current.id);
        if (i < 0) { return; }
        this.resetImages();
        this.state.selectedProduct = list[(((i + delta) % list.length) + list.length) % list.length];
    }
    get canStep() { return Boolean(this.productNav); }
    onKeydown(ev) {
        if (!this.state.selectedProduct) { return; }
        if (ev.key === "Escape") {
            ev.preventDefault();
            ev.stopImmediatePropagation();
            this.closeProduct();
        } else if (ev.key === "ArrowRight") {
            this.stepProduct(1);
        } else if (ev.key === "ArrowLeft") {
            this.stepProduct(-1);
        }
    }
    safeHref(url) { const u = (url || "").trim(); return SAFE_URL.test(u) ? u : false; }
    isExternal(url) { return /^https?:\/\//i.test((url || "").trim()); }
    manageProducts() {
        if (this.state.canManage) {
            this.action.doAction("sgt_xinyang_welcome.action_sgt_home_product");
        }
    }
    addProduct() {
        if (!this.state.canManage) { return; }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: this.tr("New product"),
            res_model: "sgt.home.product",
            views: [[false, "form"]],
            target: "current",
        });
    }
    editProduct(ev) {
        if (!this.state.canManage) { return; }
        const id = Number(ev.currentTarget.dataset.id);
        const product = this.state.products.find((p) => p.id === id);
        if (!product) { return; }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: product.name,
            res_model: "sgt.home.product",
            res_id: product.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
    onInquiry(ev) {
        ev.preventDefault();
        const d = new FormData(ev.currentTarget);
        const items = [
            ["Name", d.get("name")], ["Company", d.get("company")],
            ["Email", d.get("email")], ["Phone", d.get("phone")],
            ["Product area", d.get("type")], ["Requirements", d.get("request")],
        ];
        const body = items.map(([key, value]) => `${key}: ${String(value || "").slice(0, 3000)}`).join("\n");
        this.state.formResult = this.tr("An email draft is being prepared. No information was stored in Odoo.");
        window.location.href = "mailto:jsxyjd@jsxyjd.net?subject=" +
            encodeURIComponent("Xinyang product enquiry") + "&body=" + encodeURIComponent(body);
    }
}

registry.category("actions").add("sgt_xinyang_home", SgtHome);
