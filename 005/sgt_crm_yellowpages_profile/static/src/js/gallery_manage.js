/** @odoo-module **/

import { Component, markup, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { SGTGalleryDeleteDialog, DELETE_DIALOG_MAX_THUMBS } from "./gallery_delete_dialog";

/**
 * CRM-005 Update_034: keep the Update_033 read-only gallery and developer-mode
 * delete operation, adding a lightweight image viewer for *all* users.
 *
 * The lightbox uses native DOM under <body> instead of mounting a second Html
 * editor or re-rendering the (potentially multi-MB) gallery on every zoom.
 * It never writes to Odoo; deletion remains the original protected RPC.
 *
 * Update_066: developer-mode "Select images" mode: tick several pictures (click, Shift+click for a
 * range, Select all) and delete them with ONE protected RPC. Selection lives in a plain Set and is
 * painted straight on the DOM, so ticking never re-parses the (multi-MB) gallery HTML.
 */
const BULK_DELETE_MAX = 500; // keep equal to crm.lead.GALLERY_BULK_DELETE_MAX

export class SGTGalleryManageField extends Component {
    static template = "sgt_crm_yellowpages_profile.GalleryManageField";
    static props = { ...standardFieldProps };
    static supportedTypes = ["html"];

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.deleting = false;
        this.state = useState({ select: false, count: 0 });
        this.selected = new Set();
        this.lastPicked = null;
        this._memo = { html: null, markup: null, total: 0, prefixes: [] };
        this.rootRef = useRef("root");
        onMounted(() => this.paintSelection());
        onPatched(() => this.paintSelection());
        this.viewer = null;
        this.viewerKeydown = null;
        this.viewerImages = [];
        this.viewerIndex = 0;
        this.viewerZoom = 1;
        this.viewerRestoreFocus = null;
        onWillUnmount(() => this.closeViewer());
    }

    get debugEnabled() {
        const query = new URLSearchParams(window.location.search);
        const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
        return (query.has("debug") && query.get("debug") !== "0") ||
            (hash.has("debug") && hash.get("debug") !== "0") ||
            Boolean(window.odoo && window.odoo.debug);
    }

    get canShowDelete() {
        return this.debugEnabled && Boolean(this.props.record.resId) && !this.props.record.isNew;
    }

    get galleryMarkup() {
        const html = this.props.record.data[this.props.name] || "";
        if (!this.canShowDelete || !html) {
            return markup(html);
        }
        // Same HTML => same Markup object, so a re-render caused by ticking a picture does not
        // re-parse or re-insert the gallery.
        if (this._memo.html === html && this._memo.markup) {
            return this._memo.markup;
        }
        // Update_033: do not alter the delete-index/fingerprint logic.
        const holder = document.createElement("div");
        holder.innerHTML = String(html);
        const images = Array.from(holder.querySelectorAll("img"));
        const prefixes = [];
        images.forEach((img, index) => {
            const figure = img.closest("figure");
            let tile;
            if (figure && figure.querySelectorAll("img").length === 1) {
                tile = figure;
                tile.classList.add("sgt_yp_managed_tile");
            } else {
                tile = document.createElement("span");
                tile.className = "sgt_yp_managed_tile sgt_yp_managed_single";
                img.parentNode.insertBefore(tile, img);
                tile.appendChild(img);
            }
            tile.dataset.galleryIndex = String(index);
            // Short fingerprint prevents deleting the wrong image if another tab changed the gallery.
            const prefix = (img.getAttribute("src") || "").slice(0, 128);
            prefixes.push(prefix);
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "sgt_yp_image_remove";
            btn.dataset.galleryIndex = String(index);
            btn.dataset.gallerySrcPrefix = prefix;
            btn.dataset.galleryCount = String(images.length);
            btn.title = "Delete this image";
            btn.setAttribute("aria-label", "Delete this image");
            btn.textContent = "×";
            tile.appendChild(btn);
            // Update_066: tick box, visible only in "Select images" mode.
            const pick = document.createElement("span");
            pick.className = "sgt_yp_image_pick";
            pick.setAttribute("aria-hidden", "true");
            tile.appendChild(pick);
        });
        // Mutate (never reassign) the memo: OWL evaluates template getters on a render context that
        // inherits from the component, so `this._memo = ...` here would only set a throw-away copy.
        Object.assign(this._memo, { html, markup: markup(holder.innerHTML), total: images.length, prefixes });
        return this._memo.markup;
    }

    // ---- Update_066: select several pictures -------------------------------------------------
    /** Update_067: "Select images" is for Administrators (group "Settings") only; the server enforces it too. */
    get canSelect() {
        return Boolean(user.isSystem) && this.canShowDelete && this.galleryMarkup && this._memo.total > 0;
    }

    /** src of the pictures at these gallery indexes (for the confirmation box), at most DELETE_DIALOG_MAX_THUMBS. */
    thumbsFor(indexes) {
        const root = this.rootRef && this.rootRef.el;
        if (!root) return [];
        const wanted = new Set(indexes.slice(0, DELETE_DIALOG_MAX_THUMBS));
        const out = [];
        root.querySelectorAll(".sgt_yp_managed_tile").forEach((tile) => {
            if (wanted.has(Number(tile.dataset.galleryIndex))) {
                const img = tile.querySelector("img");
                if (img) out.push(img.getAttribute("src") || "");
            }
        });
        return out;
    }

    get totalImages() {
        return this._memo.total;
    }

    get selectedCount() {
        return this.state.count;
    }

    get deleteSelectedLabel() {
        return `Delete selected (${this.state.count})`;
    }

    get selectAllLabel() {
        return `Select all (${this._memo.total})`;
    }

    startSelect() {
        this.selected.clear();
        this.lastPicked = null;
        this.state.count = 0;
        this.state.select = true;
    }

    endSelect() {
        this.selected.clear();
        this.lastPicked = null;
        this.state.count = 0;
        this.state.select = false;
    }

    selectAll() {
        this.selected = new Set(Array.from({ length: this._memo.total }, (_, i) => i));
        this.afterSelectionChange();
    }

    clearSelection() {
        this.selected.clear();
        this.lastPicked = null;
        this.afterSelectionChange();
    }

    /** Click on a tile in select mode: toggle it; Shift+click ticks the range from the last pick. */
    toggleTile(index, shift) {
        if (shift && this.lastPicked !== null) {
            const [a, b] = [Math.min(this.lastPicked, index), Math.max(this.lastPicked, index)];
            const wantOn = !this.selected.has(index);
            for (let i = a; i <= b; i++) {
                if (wantOn) this.selected.add(i); else this.selected.delete(i);
            }
        } else if (this.selected.has(index)) {
            this.selected.delete(index);
        } else {
            this.selected.add(index);
        }
        this.lastPicked = index;
        this.afterSelectionChange();
    }

    afterSelectionChange() {
        this.state.count = this.selected.size;
        this.paintSelection();
    }

    /** Paint ticks on the tiles directly (no re-render of the gallery HTML). */
    paintSelection() {
        const root = this.rootRef && this.rootRef.el;
        if (!root) return;
        root.querySelectorAll(".sgt_yp_managed_tile").forEach((tile) => {
            const on = this.selected.has(Number(tile.dataset.galleryIndex));
            tile.classList.toggle("sgt_yp_selected", on);
        });
    }

    confirmDeleteSelected() {
        if (this.deleting || !this.selected.size) return;
        if (this.selected.size > BULK_DELETE_MAX) {
            // Same limit as the server (GALLERY_BULK_DELETE_MAX): say it instead of failing on the RPC.
            this.notification.add(`Select at most ${BULK_DELETE_MAX} pictures at a time.`, { type: "warning" });
            return;
        }
        const indexes = Array.from(this.selected).sort((a, b) => a - b);
        const prefixes = indexes.map((i) => this._memo.prefixes[i] || "");
        const total = this._memo.total;
        const n = indexes.length;
        this.dialog.add(SGTGalleryDeleteDialog, {
            title: n === 1 ? "Delete product image" : "Delete product images",
            thumbs: this.thumbsFor(indexes),
            count: n,
            total,
            confirmLabel: n === 1 ? "Delete 1 image" : `Delete ${n} images`,
            confirm: async () => {
                if (this.deleting) return;
                this.deleting = true;
                try {
                    await this.orm.call("crm.lead", "action_crm005_delete_gallery_images", [
                        [this.props.record.resId], indexes, prefixes, total,
                    ]);
                    this.notification.add(
                        n === 1 ? "Image deleted successfully." : `${n} images deleted successfully.`,
                        { type: "success" });
                    window.location.reload();
                } catch (error) {
                    this.deleting = false;
                    this.notification.add("Could not delete the images. Check permissions or refresh the Deal.", {
                        type: "danger",
                    });
                    throw error;
                }
            },
        });
    }

    /** Gallery click delegation: delete always takes priority over preview. */
    onGalleryClick(event) {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }
        if (this.state.select && this.canShowDelete && !this.deleting) {
            // Select mode: a click anywhere on a picture tile ticks / unticks it.
            const tile = target.closest(".sgt_yp_managed_tile");
            if (tile && event.currentTarget.contains(tile)) {
                event.preventDefault();
                event.stopPropagation();
                this.toggleTile(Number(tile.dataset.galleryIndex), event.shiftKey);
            }
            return;
        }
        const button = target.closest(".sgt_yp_image_remove");
        if (button) {
            event.preventDefault();
            event.stopPropagation();
            if (this.canShowDelete && !this.deleting) {
                this.confirmDelete(button);
            }
            return;
        }
        const image = target.closest("img");
        if (!image || this.deleting || !event.currentTarget.contains(image)) {
            return;
        }
        // An imported image might be wrapped in an <a>: clicking must not
        // navigate away from the Odoo Deal or trigger the parent gallery link.
        event.preventDefault();
        event.stopPropagation();
        this.openViewer(event.currentTarget, image);
    }

    /** Only the image presentation is changed; the RPC is unchanged. */
    confirmDelete(button) {
        const index = Number(button.dataset.galleryIndex);
        const prefix = button.dataset.gallerySrcPrefix || "";
        const count = Number(button.dataset.galleryCount);
        this.dialog.add(SGTGalleryDeleteDialog, {
            title: "Delete product image",
            thumbs: this.thumbsFor([index]),
            count: 1,
            total: count,
            confirmLabel: "Delete image",
            confirm: async () => {
                if (this.deleting) return;
                this.deleting = true;
                try {
                    await this.orm.call("crm.lead", "action_crm005_delete_gallery_image", [
                        [this.props.record.resId], index, prefix, count,
                    ]);
                    this.notification.add("Image deleted successfully.", { type: "success" });
                    window.location.reload();
                } catch (error) {
                    this.deleting = false;
                    this.notification.add("Could not delete image. Check permissions or refresh the Deal.", {
                        type: "danger",
                    });
                    throw error;
                }
            },
        });
    }

    /** Use only the existing gallery DOM; no new backend reads or writes. */
    openViewer(galleryRoot, selectedImage) {
        const images = Array.from(galleryRoot.querySelectorAll("img"));
        const index = images.indexOf(selectedImage);
        if (index < 0) {
            return;
        }
        this.closeViewer();
        this.viewerImages = images.map((image, i) => {
            const figure = image.closest("figure");
            const caption = figure && figure.contains(image)
                ? figure.querySelector("figcaption") : null;
            return {
                // The DOM attribute also supports inline base64; no external requests.
                src: image.currentSrc || image.getAttribute("src") || "",
                title: (caption && caption.textContent.trim()) ||
                    image.getAttribute("alt") || `Image ${i + 1}`,
            };
        });
        this.viewerIndex = index;
        this.viewerZoom = 1;
        this.viewerRestoreFocus = document.activeElement;
        const viewer = document.createElement("div");
        viewer.className = "sgt_yp_lightbox";
        viewer.setAttribute("role", "dialog");
        viewer.setAttribute("aria-modal", "true");
        viewer.setAttribute("aria-label", "Product image viewer");
        viewer.tabIndex = -1;
        viewer.innerHTML = `
            <div class="sgt_yp_lightbox_head">
              <div class="sgt_yp_lightbox_label">
                <div class="sgt_yp_lightbox_title"></div>
                <div class="sgt_yp_lightbox_counter"></div>
              </div>
              <div class="sgt_yp_lightbox_controls">
                <button type="button" data-action="zoomout" title="Zoom out (-)" aria-label="Zoom out">−</button>
                <span class="sgt_yp_lightbox_percent">100%</span>
                <button type="button" data-action="zoomin" title="Zoom in (+)" aria-label="Zoom in">+</button>
                <button type="button" data-action="reset" title="Fit image to screen" aria-label="Reset zoom">↺</button>
                <button type="button" class="sgt_yp_lightbox_close" data-action="close" title="Close (Esc)" aria-label="Close viewer">×</button>
              </div>
            </div>
            <div class="sgt_yp_lightbox_stage">
              <button type="button" class="sgt_yp_lightbox_arrow sgt_yp_lightbox_prev"
                data-action="prev" aria-label="Previous image" title="Previous (Left arrow)">‹</button>
              <img class="sgt_yp_lightbox_image" alt="" draggable="false"/>
              <button type="button" class="sgt_yp_lightbox_arrow sgt_yp_lightbox_next"
                data-action="next" aria-label="Next image" title="Next (Right arrow)">›</button>
            </div>
            <div class="sgt_yp_lightbox_bottom">
              <div class="sgt_yp_lightbox_tip">← → Navigate · Esc Close · + / − Zoom</div>
              <div class="sgt_yp_lightbox_thumbs" aria-label="Gallery thumbnails"></div>
            </div>`;
        viewer.addEventListener("click", (event) => {
            if (!(event.target instanceof Element)) return;
            const actionButton = event.target.closest("button[data-action]");
            if (actionButton) {
                const action = actionButton.dataset.action;
                if (action === "close") this.closeViewer();
                else if (action === "prev") this.changeViewerImage(-1);
                else if (action === "next") this.changeViewerImage(1);
                else if (action === "zoomout") this.setViewerZoom(this.viewerZoom - 0.25);
                else if (action === "zoomin") this.setViewerZoom(this.viewerZoom + 0.25);
                else if (action === "reset") this.setViewerZoom(1);
                return;
            }
            const thumb = event.target.closest("button[data-gallery-index]");
            if (thumb) {
                this.viewerIndex = Number(thumb.dataset.galleryIndex);
                this.viewerZoom = 1;
                this.renderViewer();
                return;
            }
            // Clicking the dark background (not the picture) closes the viewer.
            if (event.target.classList.contains("sgt_yp_lightbox_stage")) {
                this.closeViewer();
            }
        });
        viewer.querySelector(".sgt_yp_lightbox_image").addEventListener("dblclick", () => {
            this.setViewerZoom(this.viewerZoom === 1 ? 2 : 1);
        });
        const thumbs = viewer.querySelector(".sgt_yp_lightbox_thumbs");
        this.viewerImages.forEach((item, i) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "sgt_yp_lightbox_thumb";
            button.dataset.galleryIndex = String(i);
            button.setAttribute("aria-label", `View image ${i + 1}`);
            const thumb = document.createElement("img");
            thumb.src = item.src;
            thumb.alt = "";
            thumb.loading = "lazy";
            button.appendChild(thumb);
            thumbs.appendChild(button);
        });
        this.viewer = viewer;
        document.body.appendChild(viewer);
        this.viewerKeydown = (event) => {
            if (!this.viewer) return;
            if (event.key === "Escape") {
                event.preventDefault();
                this.closeViewer();
            } else if (event.key === "ArrowLeft") {
                event.preventDefault();
                this.changeViewerImage(-1);
            } else if (event.key === "ArrowRight") {
                event.preventDefault();
                this.changeViewerImage(1);
            } else if (event.key === "+" || event.key === "=") {
                event.preventDefault();
                this.setViewerZoom(this.viewerZoom + 0.25);
            } else if (event.key === "-" || event.key === "_") {
                event.preventDefault();
                this.setViewerZoom(this.viewerZoom - 0.25);
            } else if (event.key === "Tab") {
                // Keep keyboard focus within the modal while it is open.
                const buttons = Array.from(this.viewer.querySelectorAll("button"));
                const first = buttons[0];
                const last = buttons[buttons.length - 1];
                if (event.shiftKey && (document.activeElement === first || document.activeElement === this.viewer)) {
                    event.preventDefault();
                    last.focus();
                } else if (!event.shiftKey && document.activeElement === last) {
                    event.preventDefault();
                    first.focus();
                }
            }
        };
        window.addEventListener("keydown", this.viewerKeydown, true);
        viewer.focus();
        this.renderViewer();
    }

    changeViewerImage(step) {
        if (!this.viewer || !this.viewerImages.length) return;
        this.viewerIndex = (this.viewerIndex + step + this.viewerImages.length) % this.viewerImages.length;
        this.viewerZoom = 1;
        this.renderViewer();
    }

    setViewerZoom(value) {
        if (!this.viewer) return;
        this.viewerZoom = Math.max(0.75, Math.min(3, value));
        this.renderViewerZoom();
    }

    renderViewerZoom() {
        if (!this.viewer) return;
        const image = this.viewer.querySelector(".sgt_yp_lightbox_image");
        image.style.transform = `scale(${this.viewerZoom})`;
        this.viewer.querySelector(".sgt_yp_lightbox_percent").textContent =
            `${Math.round(this.viewerZoom * 100)}%`;
        this.viewer.querySelector('button[data-action="zoomout"]').disabled = this.viewerZoom <= 0.75;
        this.viewer.querySelector('button[data-action="zoomin"]').disabled = this.viewerZoom >= 3;
    }

    renderViewer() {
        if (!this.viewer) return;
        const item = this.viewerImages[this.viewerIndex];
        if (!item) return;
        this.viewer.querySelector(".sgt_yp_lightbox_title").textContent = item.title;
        this.viewer.querySelector(".sgt_yp_lightbox_counter").textContent =
            `Image ${this.viewerIndex + 1} of ${this.viewerImages.length}`;
        const image = this.viewer.querySelector(".sgt_yp_lightbox_image");
        image.alt = item.title;
        image.src = item.src;
        this.viewer.querySelectorAll(".sgt_yp_lightbox_thumb").forEach((button, i) => {
            const selected = i === this.viewerIndex;
            button.classList.toggle("is-active", selected);
            button.setAttribute("aria-current", selected ? "true" : "false");
        });
        const activeThumb = this.viewer.querySelector(".sgt_yp_lightbox_thumb.is-active");
        if (activeThumb) activeThumb.scrollIntoView({ block: "nearest", inline: "nearest" });
        this.renderViewerZoom();
    }

    closeViewer() {
        if (this.viewerKeydown) {
            window.removeEventListener("keydown", this.viewerKeydown, true);
            this.viewerKeydown = null;
        }
        if (this.viewer) {
            this.viewer.remove();
            this.viewer = null;
        }
        this.viewerImages = [];
        if (this.viewerRestoreFocus && this.viewerRestoreFocus.isConnected &&
            typeof this.viewerRestoreFocus.focus === "function") {
            this.viewerRestoreFocus.focus();
        }
        this.viewerRestoreFocus = null;
    }
}

registry.category("fields").add("sgt_gallery_manage", {
    component: SGTGalleryManageField,
    supportedTypes: ["html"],
});
