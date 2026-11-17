/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const MODEL = "argo.document.folder";

/**
 * CRM-005: readonly field widget which bridges to Documents-008.
 * Folder/document writes are performed solely through the existing Documents
 * server-side API, not through direct CRM fields or bypassed Odoo permissions.
 */
export class Crm005DocumentsPanel extends Component {
    static template = "sgt_crm_yellowpages_profile.DocumentsPanel";
    static props = { ...standardFieldProps };
    static supportedTypes = ["char"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.uploadInput = useRef("crm005DocumentsInput");
        this.state = useState({
            loading: true, busy: false, configured: false,
            linked: false, folder: null, files: [], truncated: false,
            error: "", reason: "", suggestedName: "", rootName: "CRM Information",
            maxFileMb: 25, pushing: false, gallerySyncing: false, galleryProgress: "",
            gallerySummary: "",
        });
        onWillStart(() => this.reload());
        onWillUpdateProps(async (nextProps) => {
            if (this.leadIdFrom(nextProps) !== this.leadId) {
                await this.reload(this.leadIdFrom(nextProps));
            }
        });
    }

    leadIdFrom(props) {
        const id = Number(props.record?.resId);
        return Number.isSafeInteger(id) && id > 0 ? id : false;
    }

    get leadId() {
        return this.leadIdFrom(this.props);
    }

    get canUpload() {
        return !this.state.busy && !this.state.gallerySyncing && Boolean(this.state.folder?.can_upload);
    }

    get canSyncGallery() {
        return !this.state.busy && !this.state.gallerySyncing &&
            Boolean(this.leadId && this.state.linked && this.state.folder?.can_upload);
    }

    get imageCount() {
        return (this.state.files || []).filter((file) => file.file_type === "image").length;
    }

    get canPushToGallery() {
        return !this.state.busy && !this.state.gallerySyncing && !this.state.pushing &&
            Boolean(this.leadId && this.state.linked && this.state.folder && this.imageCount);
    }

    /**
     * Update_064: copy the images of the linked Documents folder into this Deal's Image Gallery.
     * The server method (Documents-008 Update_010 -> crm.lead.crm005_push_documents_to_gallery)
     * enforces folder read access and Deal write access; nothing is deleted.
     */
    async pushToGallery() {
        if (!this.canPushToGallery) return;
        this.state.pushing = true;
        try {
            const res = await this.orm.call(MODEL, "explorer_push_images_to_crm", [
                this.state.folder.id, this.leadId, false,
            ]);
            const failed = (res.skipped || []).length;
            let message = `Image Gallery: thêm ${res.added || 0} ảnh, có sẵn ${res.duplicate || 0}, lỗi/bỏ qua ${failed}.`;
            if (res.truncated) message += ` Chỉ lấy ${res.limit} ảnh đầu tiên.`;
            this.state.gallerySummary = message +
                (failed ? `\n${res.skipped.slice(0, 8).map((x) => `${x.name}: ${x.reason}`).join("\n")}` : "");
            this.notification.add(message, { type: failed || res.truncated ? "warning" : "success" });
            await this.props.record.load();
        } catch (error) {
            this.showError(error);
        } finally {
            this.state.pushing = false;
        }
    }

    async syncGallery() {
        if (!this.canSyncGallery) return;
        this.state.gallerySyncing = true;
        this.state.gallerySummary = "";
        this.state.galleryProgress = "Đang kiểm tra Image Gallery…";
        const counts = { created: 0, duplicate: 0, failed: 0 };
        const failures = [];
        try {
            const manifest = await this.orm.call("crm.lead", "action_crm005_gallery_sync_manifest", [[this.leadId]]);
            const total = Number(manifest.total || 0);
            if (!total) {
                this.state.gallerySummary = "Image Gallery chưa có ảnh để đồng bộ.";
                return;
            }
            for (let offset = 0; offset < total; offset += 2) {
                this.state.galleryProgress = `Đang đồng bộ ${Math.min(offset + 2, total)}/${total} ảnh…`;
                const batch = await this.orm.call("crm.lead", "action_crm005_sync_gallery_batch", [
                    [this.leadId], offset, manifest.token, 2,
                ]);
                for (const entry of batch.results || []) {
                    if (Object.hasOwn(counts, entry.status)) counts[entry.status]++;
                    if (entry.status === "failed") {
                        failures.push(`#${entry.index}: ${entry.reason || "Không tải được ảnh"}`);
                    }
                }
            }
            const message = `Gallery ${total} ảnh: đã lưu ${counts.created}, có sẵn ${counts.duplicate}, lỗi ${counts.failed}.`;
            this.state.gallerySummary = message + (failures.length ? `\n${failures.slice(0, 8).join("\n")}` : "");
            this.notification.add(message, { type: counts.failed ? "warning" : "success" });
            await this.reload();
        } catch (error) {
            this.state.gallerySummary = "Đồng bộ bị gián đoạn. Các ảnh đã lưu ở lô trước vẫn được giữ; bấm lại để tiếp tục và bỏ qua ảnh trùng.";
            this.showError(error);
        } finally {
            this.state.galleryProgress = "";
            this.state.gallerySyncing = false;
        }
    }

    async reload(id = this.leadId) {
        this.state.loading = true;
        this.state.error = "";
        if (!id) {
            this.state.linked = false;
            this.state.folder = null;
            this.state.files = [];
            this.state.loading = false;
            return;
        }
        try {
            const data = await this.orm.call(MODEL, "explorer_deal_folder_info", [id]);
            this.state.configured = Boolean(data.configured);
            this.state.linked = Boolean(data.linked);
            this.state.folder = data.folder || null;
            this.state.files = data.files || [];
            this.state.truncated = Boolean(data.truncated);
            this.state.reason = data.reason || "";
            this.state.rootName = data.root_name || "CRM Information";
            this.state.suggestedName = data.suggested_name || "";
        } catch (error) {
            this.state.error = error?.data?.message || error?.message || "Không đọc được Documents.";
            this.state.folder = null;
            this.state.files = [];
        } finally {
            this.state.loading = false;
        }
    }

    refresh() {
        return this.reload();
    }

    async createFolder() {
        if (!this.leadId || this.state.busy || this.state.linked || !this.state.suggestedName) {
            return;
        }
        this.state.busy = true;
        try {
            const result = await this.orm.call(MODEL, "explorer_create_deal_folder", [this.leadId]);
            this.notification.add(result.already_exists ?
                "Đã liên kết folder công ty/MST hiện có trong Documents-008." :
                "Đã tạo folder theo tên công ty và MST trong Documents-008.", { type: "success" });
            await this.reload();
        } catch (error) {
            this.showError(error);
        } finally {
            this.state.busy = false;
        }
    }

    openDocuments() {
        if (!this.state.folder?.id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.client",
            tag: "argo_documents.explorer",
            name: "CRM Information · Documents",
            context: { active_id: this.state.folder.id },
        });
    }

    chooseFiles() {
        if (this.canUpload) {
            this.uploadInput.el?.click();
        }
    }

    async onFilesChanged(event) {
        const files = Array.from(event.target.files || []);
        event.target.value = "";
        await this.uploadFiles(files);
    }

    onDragOver(event) {
        if (this.canUpload) {
            event.preventDefault();
            event.dataTransfer.dropEffect = "copy";
        }
    }

    async onDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        if (this.canUpload) {
            await this.uploadFiles(Array.from(event.dataTransfer?.files || []));
        }
    }

    async uploadFiles(files) {
        const folderId = this.state.folder?.id;
        if (!this.canUpload || !folderId || !files.length) {
            return;
        }
        this.state.busy = true;
        let uploaded = 0;
        let failed = 0;
        try {
            for (const file of files) {
                try {
                    const form = new FormData();
                    form.append("ufile", file, file.name);
                    form.append("folder_id", String(folderId));
                    form.append("compress", "1");
                    form.append("csrf_token", window.odoo?.csrf_token || "");
                    const response = await fetch("/argo_documents/upload", {
                        method: "POST", body: form, credentials: "same-origin",
                    });
                    const payload = await response.json();
                    if (!response.ok || !payload.ok) {
                        throw new Error(payload.error || `Upload thất bại (${response.status})`);
                    }
                    uploaded++;
                } catch (error) {
                    failed++;
                    this.notification.add(`${file.name}: ${error?.message || "Upload lỗi"}`, { type: "danger" });
                }
            }
            if (uploaded) {
                this.notification.add(`Đã lưu ${uploaded} file vào Documents-008.`, { type: "success" });
            }
        } finally {
            await this.reload();
            this.state.busy = false;
        }
        return { uploaded, failed };
    }

    fileHref(file) {
        return `/web/content/${Number(file.attachment_id)}?download=true&filename=${encodeURIComponent(file.name || "file")}`;
    }

    fileSize(bytes) {
        const num = Number(bytes || 0);
        if (num < 1024) return `${num} B`;
        if (num < 1024 * 1024) return `${(num / 1024).toFixed(1)} KB`;
        return `${(num / (1024 * 1024)).toFixed(1)} MB`;
    }

    showError(error) {
        this.notification.add(error?.data?.message || error?.message || "Thao tác Documents thất bại.", { type: "danger" });
    }
}

// Odoo 19 Field.template mounts `field.component`. The registry entry must expose
// the component explicitly (as the gallery widget does); passing a class directly
// leaves field.component undefined and crashes every CRM Deal form render.
registry.category("fields").add("sgt_crm005_documents", {
    component: Crm005DocumentsPanel,
    supportedTypes: ["char"],
});
