import {
    Component,
    onWillStart,
    onWillUnmount,
    useEffect,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { FileModel } from "@web/core/file_viewer/file_model";

import { ArgoCrmTargetDialog, ArgoRenameInput, ArgoShareDialog, ArgoTextEditorDialog } from "./dialogs";
import {
    NEW_FILE_ITEMS,
    TYPE_ICON,
    TYPE_LABEL,
    accessLabels,
    collectDroppedFiles,
    formatDate,
    humanSize,
    itemKey,
    parseKey,
    storageGet,
    storageSet,
} from "./utils";

const FOLDER_MODEL = "argo.document.folder";
const DOC_MODEL = "argo.document";
const DND_TYPE = "application/x-argo-items";
const UPLOAD_CONCURRENCY = 3;
const IMAGE_RAW_LIMIT_MB = 100; // ảnh được nén trên server nên cho phép file gốc nặng hơn

export class ArgoExplorer extends Component {
    static template = "argo_documents.Explorer";
    static components = { ArgoRenameInput };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.action = useService("action");
        this.fileViewer = useFileViewer();
        this.rootRef = useRef("root");
        this.fileInput = useRef("fileInput");
        this.dirInput = useRef("dirInput");
        this.replaceInput = useRef("replaceInput");

        this.TYPE_ICON = TYPE_ICON;
        this.TYPE_LABEL = TYPE_LABEL;
        this.NEW_FILE_ITEMS = NEW_FILE_ITEMS;
        this.humanSize = humanSize;
        this.formatDate = formatDate;
        this.itemKey = itemKey;

        const isMobile = window.innerWidth < 768;
        this.isTouch = window.matchMedia?.("(pointer: coarse)").matches || false;
        this.state = useState({
            config: {},
            tree: [],
            expanded: storageGet("expanded", {}),
            folderId: false,
            trash: false,
            data: { folder: {}, breadcrumb: [], folders: [], files: [] },
            selection: {},
            anchorKey: null,
            view: storageGet("view", "grid"),
            sortBy: storageGet("sortBy", "name"),
            sortAsc: storageGet("sortAsc", true),
            search: "",
            clipboard: null,
            menu: null,
            dropdown: null, // 'new' | 'upload' | 'sort' | 'view'
            renaming: null,
            uploads: [],
            uploadPanelOpen: false,
            dragOver: false,
            dropTarget: null,
            loading: false,
            showDetails: !isMobile && storageGet("details", true),
            sidebarOpen: !isMobile,
            back: [],
            forward: [],
        });
        this.draggingItems = null;
        this.replaceTarget = null;
        this.searchTimer = null;

        onWillStart(async () => {
            const initialFolder = this.props.action?.context?.active_id || false;
            const [config] = await Promise.all([this.orm.call(FOLDER_MODEL, "explorer_config", []), this.loadTree()]);
            this.state.config = config;
            this.state.folderId = initialFolder;
            await this.load().catch(() => {
                this.state.folderId = false;
                return this.load();
            });
        });

        useExternalListener(window, "click", () => this.closeMenus(), { capture: false });
        useExternalListener(window, "resize", () => this.closeMenus());
        useExternalListener(window, "keydown", (ev) => {
            if (ev.key === "Escape") {
                this.closeMenus();
            }
        });
        onWillUnmount(() => clearTimeout(this.searchTimer));

        // Giữ menu chuột phải nằm trọn trong màn hình
        useEffect(
            (menu) => {
                const el = menu && this.rootRef.el?.querySelector(".o_gx_context");
                if (!el) {
                    return;
                }
                const r = el.getBoundingClientRect();
                const x = Math.max(4, Math.min(menu.x, window.innerWidth - r.width - 8));
                const y = Math.max(4, Math.min(menu.y, window.innerHeight - r.height - 8));
                el.style.left = `${x}px`;
                el.style.top = `${y}px`;
                el.classList.toggle("o_gx_sub_up", y + r.height > window.innerHeight - 240);
                el.classList.toggle("o_gx_sub_left", x + r.width * 2 > window.innerWidth - 8);
            },
            () => [this.state.menu]
        );
    }

    // ------------------------------------------------------------------
    // Dữ liệu
    // ------------------------------------------------------------------
    async loadTree() {
        this.state.tree = await this.orm.call(FOLDER_MODEL, "explorer_tree", []);
    }

    async load() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(FOLDER_MODEL, "explorer_list", [], {
                folder_id: this.state.folderId || false,
                search: this.state.search.trim() || null,
                trash: this.state.trash,
            });
            this.state.data = data;
            // bỏ chọn các mục không còn trong danh sách
            const keys = new Set(this.items.map(itemKey));
            for (const key of Object.keys(this.state.selection)) {
                if (!keys.has(key)) {
                    delete this.state.selection[key];
                }
            }
            this.expandAncestors();
            this.props.updateActionState?.({ active_id: this.state.folderId || false });
        } finally {
            this.state.loading = false;
        }
    }

    async refresh({ tree = false } = {}) {
        await Promise.all([this.load(), tree ? this.loadTree() : null]);
    }

    get items() {
        const { folders, files } = this.state.data;
        const dir = this.state.sortAsc ? 1 : -1;
        const by = this.state.sortBy;
        const cmp = (a, b) => {
            let r = 0;
            if (by === "date") {
                r = (a.write_date || "").localeCompare(b.write_date || "");
            } else if (by === "size") {
                r = (a.size || 0) - (b.size || 0);
            } else if (by === "type") {
                r = (a.file_type || "").localeCompare(b.file_type || "");
            }
            if (!r) {
                r = a.name.localeCompare(b.name, "vi", { numeric: true, sensitivity: "base" });
            }
            return r * dir;
        };
        return [...[...folders].sort(cmp), ...[...files].sort(cmp)];
    }

    get selectedItems() {
        return this.items.filter((it) => this.state.selection[itemKey(it)]);
    }

    get selectedCount() {
        return Object.keys(this.state.selection).length;
    }

    /** Chuỗi quyền xem của thư mục đang mở: phòng ban + người dùng (hoặc phần kế thừa từ thư mục cha). */
    get folderAccessText() {
        const f = this.state.data && this.state.data.folder;
        if (!f || !f.restricted) {
            return "";
        }
        const own = f.allowed_users.length || f.allowed_departments.length;
        return (own
            ? accessLabels(f.allowed_departments, f.allowed_users)
            : accessLabels(f.inherited_departments, f.inherited_users)
        ).join(", ");
    }

    get canCopyImage() {
        const items = this.selectedItems;
        return !this.state.trash && items.length === 1 && items[0].kind === "file"
            && items[0].file_type === "image" && !!items[0].attachment_id;
    }

    get selectedSize() {
        return this.selectedItems.reduce((s, it) => s + (it.size || 0), 0);
    }

    get totalSize() {
        return this.items.reduce((s, it) => s + (it.size || 0), 0);
    }

    get savedBytes() {
        return this.state.data.files.reduce(
            (s, f) => s + (f.original_size > f.size ? f.original_size - f.size : 0),
            0
        );
    }

    get treeRows() {
        const byParent = {};
        for (const node of this.state.tree) {
            (byParent[node.parent_id || 0] ||= []).push(node);
        }
        const rows = [];
        const walk = (parentId, depth) => {
            for (const node of byParent[parentId] || []) {
                const hasChildren = !!byParent[node.id];
                const expanded = !!this.state.expanded[node.id];
                rows.push({ ...node, depth, hasChildren, expanded });
                if (hasChildren && expanded) {
                    walk(node.id, depth + 1);
                }
            }
        };
        walk(0, 1);
        return rows.filter((row) => !this._isInCrmTree(row.id));
    }

    _isInCrmTree(folderId) {
        const crmId = Number(this.state.config.crm_root_folder_id || 0);
        if (!crmId) return false;
        const byId = new Map(this.state.tree.map((item) => [item.id, item]));
        let id = folderId;
        const seen = new Set();
        while (id && !seen.has(id)) {
            if (id === crmId) return true;
            seen.add(id);
            id = byId.get(id)?.parent_id || false;
        }
        return false;
    }

    get crmTreeRows() {
        const crmId = Number(this.state.config.crm_root_folder_id || 0);
        if (!crmId) return [];
        const byParent = {};
        for (const node of this.state.tree) {
            (byParent[node.parent_id || 0] ||= []).push(node);
        }
        const rows = [];
        const walk = (id, depth) => {
            for (const node of byParent[id] || []) {
                const hasChildren = !!byParent[node.id];
                const expanded = !!this.state.expanded[node.id];
                rows.push({ ...node, depth, hasChildren, expanded });
                if (hasChildren && expanded) walk(node.id, depth + 1);
            }
        };
        if (this.state.expanded[crmId]) walk(crmId, 1);
        return rows;
    }

    get isCrmLocation() {
        return (this.state.data.breadcrumb || []).some(
            (c) => c.id === this.state.config.crm_root_folder_id
        );
    }

    expandAncestors() {
        // mở các thư mục cha + chính thư mục đang xem trên cây (giống Windows)
        for (const crumb of this.state.data.breadcrumb || []) {
            this.state.expanded[crumb.id] = true;
        }
    }

    // ------------------------------------------------------------------
    // Điều hướng
    // ------------------------------------------------------------------
    currentLocation() {
        return { folderId: this.state.folderId, trash: this.state.trash };
    }

    async navigate(folderId, { trash = false, pushHistory = true } = {}) {
        if (folderId === this.state.folderId && trash === this.state.trash && !this.state.search) {
            return;
        }
        if (pushHistory) {
            this.state.back.push(this.currentLocation());
            this.state.forward = [];
        }
        this.state.folderId = folderId || false;
        this.state.trash = trash;
        this.state.search = "";
        this.state.selection = {};
        this.state.renaming = null;
        if (window.innerWidth < 768) {
            this.state.sidebarOpen = false;
        }
        try {
            await this.load();
        } catch (e) {
            this.state.folderId = false;
            await this.load();
            throw e;
        }
    }

    goBack() {
        const loc = this.state.back.pop();
        if (loc) {
            this.state.forward.push(this.currentLocation());
            this.navigate(loc.folderId, { trash: loc.trash, pushHistory: false });
        }
    }

    goForward() {
        const loc = this.state.forward.pop();
        if (loc) {
            this.state.back.push(this.currentLocation());
            this.navigate(loc.folderId, { trash: loc.trash, pushHistory: false });
        }
    }

    goUp() {
        if (this.state.trash) {
            return this.navigate(false);
        }
        // CRM Information là root độc lập, không phải con của Company Information.
        if (this.state.folderId === this.state.config.crm_root_folder_id) {
            return;
        }
        const crumbs = this.state.data.breadcrumb;
        if (crumbs.length >= 2) {
            this.navigate(crumbs[crumbs.length - 2].id);
        } else if (this.state.folderId) {
            this.navigate(false);
        }
    }

    toggleNode(node, ev) {
        ev?.stopPropagation();
        this.state.expanded[node.id] = !this.state.expanded[node.id];
        storageSet("expanded", { ...this.state.expanded });
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value;
        clearTimeout(this.searchTimer);
        this.searchTimer = setTimeout(() => this.load(), 350);
    }

    clearSearch() {
        this.state.search = "";
        this.load();
    }

    // ------------------------------------------------------------------
    // Chọn mục
    // ------------------------------------------------------------------
    isSelected(item) {
        return !!this.state.selection[itemKey(item)];
    }

    onItemClick(ev, item) {
        ev.stopPropagation();
        this.closeMenus();
        this.rootRef.el?.focus({ preventScroll: true });
        const key = itemKey(item);
        if (ev.shiftKey && this.state.anchorKey) {
            const keys = this.items.map(itemKey);
            const a = keys.indexOf(this.state.anchorKey);
            const b = keys.indexOf(key);
            if (a >= 0 && b >= 0) {
                if (!(ev.ctrlKey || ev.metaKey)) {
                    this.state.selection = {};
                }
                for (const k of keys.slice(Math.min(a, b), Math.max(a, b) + 1)) {
                    this.state.selection[k] = true;
                }
                return;
            }
        }
        if (this.isTouch && !(ev.ctrlKey || ev.metaKey) && this.selectedCount <= 1 && !this.state.renaming) {
            // Điện thoại/máy tính bảng: chạm 1 lần là mở (nhấn giữ để mở menu)
            this.state.selection = { [key]: true };
            this.state.anchorKey = key;
            this.openItem(item);
            return;
        }
        if (ev.ctrlKey || ev.metaKey) {
            if (this.state.selection[key]) {
                delete this.state.selection[key];
            } else {
                this.state.selection[key] = true;
            }
        } else {
            this.state.selection = { [key]: true };
        }
        this.state.anchorKey = key;
    }

    onBlankClick() {
        this.closeMenus();
        this.rootRef.el?.focus({ preventScroll: true });
        if (!this.state.renaming) {
            this.state.selection = {};
        }
    }

    selectAll() {
        this.state.selection = Object.fromEntries(this.items.map((it) => [itemKey(it), true]));
    }

    // ------------------------------------------------------------------
    // Mở / xem
    // ------------------------------------------------------------------
    fileModel(file) {
        return Object.assign(new FileModel(), {
            id: file.attachment_id,
            name: file.name,
            mimetype: file.mimetype,
            checksum: file.checksum,
            type: "binary",
        });
    }

    openItem(item) {
        if (!item) {
            return;
        }
        if (item.kind === "folder") {
            if (!this.state.trash) {
                this.navigate(item.id);
            }
            return;
        }
        if (this.state.trash) {
            return this.openProperties(item);
        }
        if (item.file_type === "note") {
            return this.openNote(item);
        }
        if (item.file_type === "text" && item.text_editable && item.mimetype === "text/plain") {
            return this.openTextEditor(item);
        }
        const model = this.fileModel(item);
        if (model.isViewable) {
            const files = this.state.data.files.map((f) => (f.id === item.id ? model : this.fileModel(f)));
            this.fileViewer.open(model, files);
        } else {
            this.downloadItems([item]);
        }
    }

    viewItem(item) {
        const model = this.fileModel(item);
        if (model.isViewable) {
            this.fileViewer.open(model, [model]);
        } else {
            this.downloadItems([item]);
        }
    }

    openNote(item) {
        this.dialog.add(FormViewDialog, {
            resModel: DOC_MODEL,
            resId: item.id,
            viewId: this.state.config.note_view_id,
            title: "Ghi chú",
            size: "xl",
            onRecordSaved: () => this.refresh(),
        });
    }

    async openTextEditor(item) {
        const res = await this.orm.call(DOC_MODEL, "explorer_get_text", [[item.id]]);
        this.dialog.add(ArgoTextEditorDialog, {
            title: item.name,
            content: res.content || "",
            onSave: async (content) => {
                await this.orm.call(DOC_MODEL, "explorer_save_text", [[item.id], content]);
                this.notification.add(`Đã lưu "${item.name}"`, { type: "success" });
                await this.refresh();
            },
        });
    }

    async toggleFolderLock(item) {
        this.closeMenus();
        if (!this.state.config.is_manager || item?.kind !== 'folder' || this.state.trash) return;
        try {
            const response = await this.orm.call(FOLDER_MODEL, 'explorer_toggle_folder_lock',
                [item.id, !Boolean(item.is_locked)]);
            this.notification.add(response.is_locked ? 'Đã Lock Folder — không thể xóa.' : 'Đã Unlock Folder.',
                { type: 'success' });
            await this.refresh({ tree: true });
        } catch (error) {
            this.notification.add(error?.data?.message || error?.message || 'Không thay đổi được Lock Folder.',
                { type: 'danger' });
        }
    }

    openProperties(item) {
        this.dialog.add(FormViewDialog, {
            resModel: item.kind === "folder" ? FOLDER_MODEL : DOC_MODEL,
            resId: item.id,
            title: item.kind === "folder" ? "Thuộc tính thư mục" : "Thuộc tính file",
            onRecordSaved: () => this.refresh({ tree: item.kind === "folder" }),
        });
    }

    downloadUrl(file) {
        const name = file.file_type === "note" && !/\.html?$/i.test(file.name) ? `${file.name}.html` : file.name;
        return `/web/content/${file.attachment_id}?download=true&filename=${encodeURIComponent(name)}`;
    }

    downloadItems(items) {
        items = items || this.selectedItems;
        if (!items.length) {
            return;
        }
        let url;
        if (items.length === 1 && items[0].kind === "file") {
            url = this.downloadUrl(items[0]);
        } else {
            const payload = items.map((it) => ({ kind: it.kind, id: it.id }));
            url = `/argo_documents/zip?items=${encodeURIComponent(JSON.stringify(payload))}`;
            const name = items.length === 1 ? items[0].name : this.state.data.folder.name;
            url += `&name=${encodeURIComponent(name || "Kho-tai-lieu")}`;
        }
        const a = document.createElement("a");
        a.href = url;
        a.rel = "noopener";
        document.body.appendChild(a);
        a.click();
        a.remove();
    }

    // Clipboard hệ điều hành: khác với clipboard nội bộ của Explorer (Ctrl+C/Ctrl+V).
    // Chỉ chép ảnh khi người dùng bấm nút; dùng quyền đọc file sẵn có của Odoo.
    async copyImageToClipboard(file = this.selectedItems[0]) {
        this.closeMenus();
        if (this.state.trash || !file || file.kind !== "file" || file.file_type !== "image") {
            return;
        }
        const attachmentId = Number(file.attachment_id);
        if (!Number.isSafeInteger(attachmentId) || attachmentId <= 0) {
            this.notification.add("Không xác định được file ảnh để sao chép", { type: "warning" });
            return;
        }
        if (!window.isSecureContext || !navigator.clipboard?.write || !window.ClipboardItem ||
            (ClipboardItem.supports && !ClipboardItem.supports("image/png"))) {
            this.notification.add("Trình duyệt không hỗ trợ sao chép ảnh; hãy dùng Tải xuống để gửi file", { type: "warning" });
            return;
        }

        // Truyền Promise trong ClipboardItem để lệnh clipboard.write() được gọi
        // ngay trong thao tác click, tránh mất quyền tương tác người dùng.
        const imagePng = (async () => {
            const response = await fetch(`/web/content/${attachmentId}?download=false`, {
                credentials: "same-origin",
                cache: "no-store",
            });
            if (!response.ok) {
                throw new Error("Không đọc được ảnh với quyền hiện tại");
            }
            const blob = await response.blob();
            if (!/^image\/(png|jpeg|webp|gif)$/i.test(blob.type) || blob.size > 25 * 1024 * 1024) {
                throw new Error("Định dạng hoặc dung lượng ảnh chưa được hỗ trợ");
            }
            if (blob.type === "image/png") {
                return blob;
            }
            const bitmap = await createImageBitmap(blob);
            try {
                if (bitmap.width * bitmap.height > 24000000) {
                    throw new Error("Kích thước ảnh quá lớn để sao chép; hãy tải xuống");
                }
                const canvas = document.createElement("canvas");
                canvas.width = bitmap.width;
                canvas.height = bitmap.height;
                canvas.getContext("2d").drawImage(bitmap, 0, 0);
                const png = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
                if (!png) {
                    throw new Error("Không chuyển được ảnh sang PNG");
                }
                return png;
            } finally {
                bitmap.close?.();
            }
        })();
        try {
            await navigator.clipboard.write([new ClipboardItem({ "image/png": imagePng })]);
            this.notification.add("Đã sao chép ảnh. Có thể thử Ctrl+V vào Zalo, email hoặc ứng dụng hỗ trợ dán ảnh.", {
                type: "success",
            });
        } catch (error) {
            this.notification.add(
                `Không thể sao chép ảnh (${error?.message || "clipboard bị chặn"}). Dùng Tải xuống để gửi file.`,
                { type: "warning" }
            );
        }
    }

    thumbUrl(file) {
        return `/web/image/argo.document/${file.id}/thumbnail?unique=${file.checksum || ""}`;
    }

    compressionText(file) {
        if (!(file.original_size > file.size)) {
            return "";
        }
        const pct = Math.round((1 - file.size / file.original_size) * 100);
        return `Đã nén ${humanSize(file.original_size)} → ${humanSize(file.size)} (-${pct}%)`;
    }

    // ------------------------------------------------------------------
    // Tạo mới / đổi tên
    // ------------------------------------------------------------------
    async newFolder() {
        this.closeMenus();
        if (!this.canCreateHere) {
            return;
        }
        const res = await this.orm.call(FOLDER_MODEL, "explorer_create_folder", [this.state.folderId || false]);
        await this.refresh({ tree: true });
        const key = `folder:${res.id}`;
        this.state.selection = { [key]: true };
        this.state.renaming = key;
        this.scrollIntoView(key);
    }

    async newFile(kind) {
        this.closeMenus();
        if (!this.canUploadHere) {
            return;
        }
        const res = await this.orm.call(DOC_MODEL, "explorer_new_file", [this.state.folderId || false, kind]);
        await this.refresh();
        const key = `file:${res.id}`;
        this.state.selection = { [key]: true };
        if (kind === "note") {
            this.openNote(res);
        } else {
            this.state.renaming = key;
            this.scrollIntoView(key);
        }
    }

    startRename(item) {
        this.closeMenus();
        item = item || this.selectedItems[0];
        if (!item || this.state.trash || !item.can_edit) {
            return;
        }
        this.state.selection = { [itemKey(item)]: true };
        this.state.renaming = itemKey(item);
    }

    async commitRename(item, value) {
        value = (value || "").trim();
        if (!value || value === item.name) {
            this.state.renaming = null;
            return true;
        }
        try {
            await this.orm.call(FOLDER_MODEL, "explorer_rename", [item.kind, item.id, value]);
        } catch (e) {
            this.notification.add(e.data?.message || e.message || "Không đổi tên được", { type: "danger" });
            return false;
        }
        this.state.renaming = null;
        await this.refresh({ tree: item.kind === "folder" });
        return true;
    }

    cancelRename() {
        this.state.renaming = null;
    }

    scrollIntoView(key) {
        setTimeout(() => {
            const el = this.rootRef.el?.querySelector(`[data-key="${key}"]`);
            el?.scrollIntoView({ block: "nearest" });
        }, 50);
    }

    // ------------------------------------------------------------------
    // Cắt / chép / dán / xóa
    // ------------------------------------------------------------------
    payload(items) {
        return (items || this.selectedItems).map((it) => ({ kind: it.kind, id: it.id }));
    }

    setClipboard(mode) {
        this.closeMenus();
        const items = this.payload();
        if (!items.length) {
            return;
        }
        this.state.clipboard = { mode, items, sourceFolder: this.state.folderId };
        this.notification.add(
            `${mode === "cut" ? "Đã cắt" : "Đã sao chép"} ${items.length} mục — mở thư mục đích rồi bấm Dán (Ctrl+V)`,
            { type: "info" }
        );
    }

    isCut(item) {
        const cb = this.state.clipboard;
        return cb?.mode === "cut" && cb.items.some((i) => i.kind === item.kind && i.id === item.id);
    }

    async paste(targetId) {
        this.closeMenus();
        const cb = this.state.clipboard;
        if (!cb || this.state.trash) {
            return;
        }
        const target = targetId === undefined ? this.state.folderId || false : targetId;
        if (cb.mode === "cut") {
            await this.orm.call(FOLDER_MODEL, "explorer_move", [cb.items, target]);
            this.state.clipboard = null;
        } else {
            await this.orm.call(FOLDER_MODEL, "explorer_copy", [cb.items, target]);
        }
        await this.refresh({ tree: true });
    }

    async moveItems(items, targetId, copy = false) {
        if (!items.length) {
            return;
        }
        await this.orm.call(FOLDER_MODEL, copy ? "explorer_copy" : "explorer_move", [items, targetId || false]);
        this.notification.add(`${copy ? "Đã sao chép" : "Đã chuyển"} ${items.length} mục`, { type: "success" });
        await this.refresh({ tree: true });
    }

    trashItems(items) {
        this.closeMenus();
        items = items || this.selectedItems;
        if (!items.length || !items.every((item) => item.can_delete)) {
            return;
        }
        if (this.state.trash) {
            return this.deleteForever(items);
        }
        const label = items.length === 1 ? `"${items[0].name}"` : `${items.length} mục`;
        this.dialog.add(ConfirmationDialog, {
            title: "Chuyển vào Thùng rác",
            body: `Chuyển ${label} vào Thùng rác? Có thể khôi phục trong ${this.state.config.trash_days || 30} ngày.`,
            confirmLabel: "Xóa",
            confirmClass: "btn-danger",
            confirm: async () => {
                await this.orm.call(FOLDER_MODEL, "explorer_trash", [this.payload(items)]);
                this.state.selection = {};
                await this.refresh({ tree: items.some((i) => i.kind === "folder") });
            },
            cancel: () => {},
        });
    }

    async restoreItems(items) {
        this.closeMenus();
        items = items || this.selectedItems;
        if (!items.length || !items.every((item) => item.can_delete)) {
            return;
        }
        await this.orm.call(FOLDER_MODEL, "explorer_restore", [this.payload(items)]);
        this.notification.add(`Đã khôi phục ${items.length} mục`, { type: "success" });
        this.state.selection = {};
        await this.refresh({ tree: true });
    }

    deleteForever(items) {
        this.closeMenus();
        items = items || this.selectedItems;
        if (!items.length || !items.every((item) => item.can_delete)) {
            return;
        }
        this.dialog.add(ConfirmationDialog, {
            title: "Xóa vĩnh viễn",
            body: `Xóa vĩnh viễn ${items.length} mục? Thao tác này KHÔNG thể hoàn tác và sẽ giải phóng dung lượng.`,
            confirmLabel: "Xóa vĩnh viễn",
            confirmClass: "btn-danger",
            confirm: async () => {
                await this.orm.call(FOLDER_MODEL, "explorer_delete_forever", [this.payload(items)]);
                this.state.selection = {};
                await this.refresh();
            },
            cancel: () => {},
        });
    }

    emptyTrash() {
        this.closeMenus();
        this.dialog.add(ConfirmationDialog, {
            title: "Dọn sạch Thùng rác",
            body: "Xóa vĩnh viễn toàn bộ mục trong Thùng rác? Không thể hoàn tác.",
            confirmLabel: "Dọn sạch",
            confirmClass: "btn-danger",
            confirm: async () => {
                await this.orm.call(FOLDER_MODEL, "explorer_empty_trash", []);
                await this.refresh();
            },
            cancel: () => {},
        });
    }

    // ------------------------------------------------------------------
    // Update_010: cập nhật ảnh Documents -> Image Gallery của Deal (CRM-005)
    // ------------------------------------------------------------------
    /** Thư mục đang mở nằm trong cây CRM Information (không tính chính thư mục gốc CRM). */
    get inCrmFolder() {
        const rootId = this.state.config.crm_root_folder_id;
        const fid = this.state.folderId;
        if (!rootId || !fid || fid === rootId || this.state.trash || this.state.search) {
            return false;
        }
        return (this.state.data.breadcrumb || []).some((b) => b.id === rootId);
    }

    /**
     * Mục tiêu của nút "Cập nhật ảnh lên CRM" theo vùng chọn hiện tại.
     * - Chọn 1 thư mục: mọi ảnh trong thư mục đó.
     * - Chọn file: chỉ các ảnh đang chọn (file không phải ảnh bị bỏ qua).
     * - Không chọn gì: mọi ảnh trong thư mục đang mở.
     * Trả về null khi không áp dụng (CRM-005 chưa cài, ngoài cây CRM, thùng rác, tìm kiếm...).
     */
    get pushInfo() {
        if (!this.state.config.crm_push_available || !this.inCrmFolder) {
            return null;
        }
        const sel = this.selectedItems;
        if (sel.length === 1 && sel[0].kind === "folder") {
            return { label: "Cập nhật ảnh lên CRM", folderId: sel[0].id, documentIds: null };
        }
        if (sel.length) {
            const images = sel.filter((it) => it.kind === "file" && it.file_type === "image");
            if (!images.length) {
                return null;
            }
            return {
                label: images.length === 1 ? "Cập nhật ảnh này lên CRM" : `Cập nhật ${images.length} ảnh lên CRM`,
                folderId: this.state.folderId,
                documentIds: images.map((it) => it.id),
            };
        }
        const count = (this.state.data.files || []).filter((f) => f.file_type === "image").length;
        if (!count) {
            return null;
        }
        return { label: `Cập nhật ảnh lên CRM (${count} ảnh)`, folderId: this.state.folderId, documentIds: null };
    }

    /** Mục menu cho nút phải trên cây thư mục: chỉ nhánh CRM Information. */
    get treePushAvailable() {
        return Boolean(this.state.config.crm_push_available);
    }

    pushFromInfo() {
        const info = this.pushInfo;
        if (info) {
            return this.pushImagesToCrm(info.folderId, info.documentIds);
        }
    }

    async pushImagesToCrm(folderId, documentIds) {
        this.closeMenus();
        if (this.pushing || !folderId) {
            return;
        }
        let targets;
        try {
            targets = await this.orm.call(FOLDER_MODEL, "explorer_crm_targets", [folderId]);
        } catch (error) {
            this.notification.add(error?.data?.message || error?.message || "Không đọc được Deal gắn với thư mục.",
                { type: "danger" });
            return;
        }
        const leads = targets.leads || [];
        if (!leads.length) {
            this.notification.add("Thư mục này chưa gắn với Deal nào mà bạn có quyền xem.", { type: "warning" });
            return;
        }
        const writable = leads.filter((l) => l.can_write);
        if (!writable.length) {
            this.notification.add("Bạn không có quyền sửa Deal gắn với thư mục này.", { type: "warning" });
            return;
        }
        if (leads.length === 1) {
            return this._runPush(folderId, leads[0].id, documentIds);
        }
        this.dialog.add(ArgoCrmTargetDialog, {
            leads,
            summary: documentIds ? `${documentIds.length} ảnh đã chọn` : "Mọi ảnh trong thư mục",
            onConfirm: (leadId) => this._runPush(folderId, leadId, documentIds),
        });
    }

    async _runPush(folderId, leadId, documentIds) {
        this.pushing = true;
        try {
            const res = await this.orm.call(FOLDER_MODEL, "explorer_push_images_to_crm",
                [folderId, leadId, documentIds || false]);
            const parts = [`Thêm mới: ${res.added || 0} ảnh`];
            parts.push(`Bỏ qua (đã có): ${res.duplicate || 0}`);
            const failed = (res.skipped || []).length;
            parts.push(`Lỗi/bỏ qua: ${failed}`);
            if (res.not_image) {
                parts.push(`Không phải ảnh: ${res.not_image}`);
            }
            if (res.truncated) {
                parts.push(`Chỉ lấy ${res.limit} ảnh đầu tiên`);
            }
            this.notification.add(`Đã cập nhật Image Gallery của Deal #${leadId}. ${parts.join(" · ")}`, {
                type: failed || res.truncated ? "warning" : "success",
                sticky: Boolean(failed),
            });
            if (failed) {
                const lines = res.skipped.slice(0, 6).map((s) => `${s.name}: ${s.reason}`);
                this.notification.add(lines.join(" | "), { type: "warning" });
            }
        } catch (error) {
            this.notification.add(error?.data?.message || error?.message || "Không cập nhật được ảnh lên CRM.",
                { type: "danger" });
        } finally {
            this.pushing = false;
        }
    }

    // ------------------------------------------------------------------
    // Quyền xem
    // ------------------------------------------------------------------
    async openShare(folderItem) {
        this.closeMenus();
        const folderId = folderItem ? folderItem.id : this.state.folderId;
        if (!folderId) {
            return;
        }
        const [users, departments, data] = await Promise.all([
            this.orm.call(FOLDER_MODEL, "explorer_users", []),
            this.orm.call(FOLDER_MODEL, "explorer_departments", []),
            this.orm.call(FOLDER_MODEL, "explorer_list", [], { folder_id: folderId }),
        ]);
        if (!data.folder.can_share) {
            this.notification.add("Bạn chưa được Admin cấp quyền quản lý chia sẻ thư mục này.", {
                type: "warning",
            });
            return;
        }
        // Các role Admin đã tự có toàn quyền: không hiển thị hoặc gửi lại
        // các grant cũ của Admin khi lưu quyền cho User/Phòng ban.
        const selectableUsers = new Set(users.map((u) => u.id));
        const selectableDepartments = new Set(departments.map((d) => d.id));
        this.dialog.add(ArgoShareDialog, {
            folderName: data.folder.name,
            users,
            departments,
            selected: data.folder.allowed_users.filter((u) => selectableUsers.has(u.id)).map((u) => u.id),
            selectedDepartments: data.folder.allowed_departments.filter((d) => selectableDepartments.has(d.id)).map((d) => d.id),
            inherited: accessLabels(
                data.folder.inherited_departments.filter((d) => selectableDepartments.has(d.id)),
                data.folder.inherited_users.filter((u) => selectableUsers.has(u.id))),
            accessMode: data.folder.access_mode,
            publicLevel: data.folder.public_level,
            userGrants: data.folder.user_grants.filter((u) => selectableUsers.has(u.id)),
            departmentGrants: data.folder.department_grants.filter((d) => selectableDepartments.has(d.id)),
            onSave: async (userIds, departmentIds, mode, publicLevel, userGrants, departmentGrants) => {
                await this.orm.call(FOLDER_MODEL, "explorer_set_access", [
                    folderId, userIds, departmentIds, mode, publicLevel, userGrants, departmentGrants,
                ]);
                this.notification.add("Đã cập nhật phân quyền folder", { type: "success" });
                await this.refresh({ tree: true });
            },
        });
    }

    // ------------------------------------------------------------------
    // Upload
    // ------------------------------------------------------------------
    pickFiles() {
        this.closeMenus();
        this.fileInput.el.value = "";
        this.fileInput.el.click();
    }

    pickFolder() {
        this.closeMenus();
        this.dirInput.el.value = "";
        this.dirInput.el.click();
    }

    pickReplace(item) {
        this.closeMenus();
        this.replaceTarget = item || this.selectedItems[0];
        this.replaceInput.el.value = "";
        this.replaceInput.el.click();
    }

    // Ctrl+V từ Windows/macOS: nhận file hoặc ảnh chụp màn hình từ clipboard.
    // Không can thiệp ô tìm kiếm, text editor hay biểu mẫu Odoo.
    onSystemPaste(ev) {
        const target = ev.target;
        const tag = target?.tagName;
        if (this.state.renaming || tag === "INPUT" || tag === "TEXTAREA" || target?.isContentEditable) {
            return;
        }
        if (this.state.trash) {
            return;
        }
        const clipboard = ev.clipboardData;
        const files = clipboard?.files?.length
            ? [...clipboard.files]
            : [...(clipboard?.items || [])]
                .filter((item) => item.kind === "file")
                .map((item) => item.getAsFile())
                .filter(Boolean);
        if (files.length) {
            ev.preventDefault();
            ev.stopPropagation();
            const entries = files.map((file, index) => {
                // Ảnh chụp clipboard thường mang tên image.png hoặc không có tên.
                const ext = file.type === "image/jpeg" ? "jpg" : file.type === "image/webp" ? "webp" : "png";
                const generic = !file.name || /^image\.(png|jpg|jpeg|webp)$/i.test(file.name);
                const name = generic ? `Anh-dan-${Date.now()}-${index + 1}.${ext}` : file.name;
                return { file: generic ? new File([file], name, { type: file.type, lastModified: Date.now() }) : file,
                    relPath: "" };
            });
            this.uploadFiles(entries, this.state.folderId || false).catch((error) => {
                this.notification.add(error?.message || "Không tải lên được nội dung clipboard", { type: "danger" });
            });
            return;
        }
        // Không có file hệ điều hành: giữ nguyên thao tác dán nội bộ Explorer.
        if (this.state.clipboard) {
            ev.preventDefault();
            ev.stopPropagation();
            this.paste().catch((error) => {
                this.notification.add(error?.message || "Không thể dán mục trong Explorer", { type: "danger" });
            });
        }
    }

    onFilesPicked(ev) {
        const files = [...ev.target.files].map((file) => ({ file, relPath: "" }));
        this.uploadFiles(files, this.state.folderId || false);
    }

    onFolderPicked(ev) {
        const files = [...ev.target.files].map((file) => {
            const parts = (file.webkitRelativePath || file.name).split("/");
            parts.pop();
            return { file, relPath: parts.join("/") };
        });
        this.uploadFiles(files, this.state.folderId || false);
    }

    onReplacePicked(ev) {
        const file = ev.target.files[0];
        if (file && this.replaceTarget) {
            this.uploadFiles([{ file, relPath: "" }], this.state.folderId || false, this.replaceTarget.id);
        }
    }

    validateFile(file) {
        const max = (this.state.config.max_file_mb || 25) * 1024 * 1024;
        const isImage = (file.type || "").startsWith("image/");
        const limit = isImage && this.state.config.image_compress ? IMAGE_RAW_LIMIT_MB * 1024 * 1024 : max;
        if (file.size > limit) {
            return `Vượt giới hạn ${Math.round(limit / 1024 / 1024)} MB (file nặng ${humanSize(file.size)})`;
        }
        return null;
    }

    async uploadFiles(entries, folderId, replaceId = null, extraDirs = []) {
        if (this.state.trash) {
            this.notification.add("Không thể tải lên vào Thùng rác", { type: "warning" });
            return;
        }
        if (!entries.length && !extraDirs.length) {
            return;
        }
        // 1. Tạo trước cây thư mục (upload cả thư mục)
        const dirs = [...new Set([...extraDirs, ...entries.map((e) => e.relPath).filter(Boolean)])];
        let dirMap = {};
        if (dirs.length) {
            dirMap = await this.orm.call(FOLDER_MODEL, "explorer_ensure_paths", [folderId, dirs]);
            this.loadTree();
        }
        // 2. Hàng đợi upload
        const jobs = entries.map((e) => {
            const job = {
                id: `${Date.now()}-${Math.random()}`,
                name: e.relPath ? `${e.relPath}/${e.file.name}` : e.file.name,
                size: e.file.size,
                progress: 0,
                status: "queued",
                error: "",
                result: null,
            };
            const err = this.validateFile(e.file);
            if (err) {
                job.status = "error";
                job.error = err;
            }
            return { job, file: e.file, folder: e.relPath ? dirMap[e.relPath] : folderId };
        });
        this.state.uploads.push(...jobs.map((j) => j.job));
        this.state.uploadPanelOpen = true;
        const queue = jobs.filter((j) => j.job.status === "queued");
        const worker = async () => {
            while (queue.length) {
                const item = queue.shift();
                await this.uploadOne(item, replaceId);
            }
        };
        await Promise.all(Array.from({ length: Math.min(UPLOAD_CONCURRENCY, queue.length) }, worker));
        await this.refresh({ tree: !!dirs.length });
        const failed = jobs.filter((j) => j.job.status === "error").length;
        if (failed) {
            this.notification.add(`${failed} file tải lên không thành công — xem chi tiết ở bảng tải lên`, {
                type: "warning",
            });
        }
    }

    uploadOne({ job, file, folder }, replaceId) {
        // state proxy để giao diện cập nhật tiến trình
        const live = this.state.uploads.find((u) => u.id === job.id) || job;
        return new Promise((resolve) => {
            const form = new FormData();
            form.append("ufile", file, file.name);
            form.append("folder_id", folder || "");
            if (replaceId) {
                form.append("replace_id", replaceId);
            }
            form.append("csrf_token", odoo.csrf_token);
            const xhr = new XMLHttpRequest();
            xhr.open("POST", "/argo_documents/upload");
            live.status = "uploading";
            xhr.upload.onprogress = (ev) => {
                if (ev.lengthComputable) {
                    live.progress = Math.round((ev.loaded / ev.total) * 100);
                }
            };
            xhr.onload = () => {
                let res;
                try {
                    res = JSON.parse(xhr.responseText);
                } catch {
                    res = { ok: false, error: `Lỗi máy chủ (${xhr.status})` };
                }
                if (xhr.status === 413) {
                    res = { ok: false, error: "File quá lớn so với giới hạn của máy chủ" };
                }
                if (res.ok) {
                    live.status = "done";
                    live.progress = 100;
                    live.result = res.file;
                } else {
                    live.status = "error";
                    live.error = res.error || "Lỗi không xác định";
                }
                resolve();
            };
            xhr.onerror = () => {
                live.status = "error";
                live.error = "Mất kết nối khi tải lên";
                resolve();
            };
            xhr.send(form);
        });
    }

    get uploadSummary() {
        const ups = this.state.uploads;
        const done = ups.filter((u) => u.status === "done");
        const errors = ups.filter((u) => u.status === "error").length;
        const running = ups.filter((u) => u.status === "uploading" || u.status === "queued").length;
        const saved = done.reduce(
            (s, u) => s + (u.result && u.result.original_size > u.result.size ? u.result.original_size - u.result.size : 0),
            0
        );
        return { total: ups.length, done: done.length, errors, running, saved };
    }

    clearUploads() {
        this.state.uploads = this.state.uploads.filter((u) => u.status === "uploading" || u.status === "queued");
        if (!this.state.uploads.length) {
            this.state.uploadPanelOpen = false;
        }
    }

    // ------------------------------------------------------------------
    // Kéo thả
    // ------------------------------------------------------------------
    isExternalDrag(ev) {
        return !this.draggingItems && [...(ev.dataTransfer?.types || [])].includes("Files");
    }

    onItemDragStart(ev, item) {
        if (this.state.trash || this.state.renaming) {
            ev.preventDefault();
            return;
        }
        if (!this.isSelected(item)) {
            this.state.selection = { [itemKey(item)]: true };
        }
        this.draggingItems = this.payload();
        ev.dataTransfer.setData(DND_TYPE, JSON.stringify(this.draggingItems));
        ev.dataTransfer.setData("text/plain", this.selectedItems.map((i) => i.name).join("\n"));
        ev.dataTransfer.effectAllowed = "copyMove";
    }

    onItemDragEnd() {
        this.draggingItems = null;
        this.state.dropTarget = null;
        this.state.dragOver = false;
    }

    canDropOn(folderId) {
        if (this.state.trash) {
            return false;
        }
        if (!this.draggingItems) {
            return true;
        }
        return !this.draggingItems.some((i) => i.kind === "folder" && i.id === folderId);
    }

    onTargetDragOver(ev, folderId, targetKey) {
        if (!this.canDropOn(folderId)) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        ev.dataTransfer.dropEffect = this.draggingItems ? (ev.ctrlKey ? "copy" : "move") : "copy";
        this.state.dropTarget = targetKey;
        this.state.dragOver = this.isExternalDrag(ev);
    }

    onTargetDragLeave(ev, targetKey) {
        if (this.state.dropTarget === targetKey && !ev.currentTarget.contains(ev.relatedTarget)) {
            this.state.dropTarget = null;
        }
    }

    onMainDragOver(ev) {
        if (this.state.trash) {
            return;
        }
        if (this.isExternalDrag(ev)) {
            ev.preventDefault();
            ev.dataTransfer.dropEffect = "copy";
            this.state.dragOver = true;
            this.state.dropTarget = null;
        } else if (this.draggingItems && this.state.search) {
            ev.preventDefault(); // kéo từ kết quả tìm kiếm vào thư mục hiện tại
        }
    }

    onMainDragLeave(ev) {
        if (!ev.currentTarget.contains(ev.relatedTarget)) {
            this.state.dragOver = false;
        }
    }

    async onDrop(ev, folderId) {
        ev.preventDefault();
        ev.stopPropagation();
        this.state.dragOver = false;
        this.state.dropTarget = null;
        if (this.state.trash) {
            return;
        }
        const target = folderId === undefined ? this.state.folderId || false : folderId;
        const internal = ev.dataTransfer.getData(DND_TYPE);
        if (internal) {
            const items = JSON.parse(internal).filter((i) => !(i.kind === "folder" && i.id === target));
            this.draggingItems = null;
            await this.moveItems(items, target, ev.ctrlKey || ev.metaKey);
            return;
        }
        const { files, dirs } = await collectDroppedFiles(ev.dataTransfer);
        await this.uploadFiles(files, target, null, dirs);
    }

    // ------------------------------------------------------------------
    // Menu chuột phải / dropdown
    // ------------------------------------------------------------------
    closeMenus() {
        if (this.state.menu) {
            this.state.menu = null;
        }
        if (this.state.dropdown) {
            this.state.dropdown = null;
        }
    }

    toggleDropdown(name, ev) {
        ev.stopPropagation();
        this.state.menu = null;
        this.state.dropdown = this.state.dropdown === name ? null : name;
    }

    openMenu(ev, item) {
        ev.preventDefault();
        ev.stopPropagation();
        this.rootRef.el?.focus({ preventScroll: true });
        this.state.dropdown = null;
        if (item && !this.isSelected(item)) {
            this.state.selection = { [itemKey(item)]: true };
            this.state.anchorKey = itemKey(item);
        }
        if (!item) {
            this.state.selection = {};
        }
        this.state.menu = { x: ev.clientX, y: ev.clientY, type: item ? "item" : "blank" };
    }

    /** Update_010: menu chuột phải cho cây thư mục bên trái (trước đây hiện menu mặc định của trình duyệt). */
    openTreeMenu(ev, node) {
        ev.preventDefault();
        ev.stopPropagation();
        this.rootRef.el?.focus({ preventScroll: true });
        this.state.dropdown = null;
        this.state.menu = { x: ev.clientX, y: ev.clientY, type: "tree", node: { id: node.id, name: node.name } };
    }

    menuAction(fn, ...args) {
        this.closeMenus();
        return fn.call(this, ...args);
    }

    setView(view) {
        this.state.view = view;
        storageSet("view", view);
        this.closeMenus();
    }

    setSort(by) {
        if (this.state.sortBy === by) {
            this.state.sortAsc = !this.state.sortAsc;
        } else {
            this.state.sortBy = by;
            this.state.sortAsc = by === "name" || by === "type";
        }
        storageSet("sortBy", this.state.sortBy);
        storageSet("sortAsc", this.state.sortAsc);
        this.closeMenus();
    }

    openAdminList() {
        this.action.doAction("argo_documents.action_argo_document");
    }

    toggleDetails() {
        this.state.showDetails = !this.state.showDetails;
        storageSet("details", this.state.showDetails);
    }

    // ------------------------------------------------------------------
    // Bàn phím
    // ------------------------------------------------------------------
    onKeydown(ev) {
        const tag = ev.target.tagName;
        if (this.state.renaming || tag === "INPUT" || tag === "TEXTAREA" || ev.target.isContentEditable) {
            return;
        }
        const ctrl = ev.ctrlKey || ev.metaKey;
        const key = ev.key;
        const sel = this.selectedItems;
        let handled = true;
        if (key === "Delete") {
            if (ev.shiftKey || this.state.trash) {
                this.deleteForever(sel);
            } else {
                this.trashItems(sel);
            }
        } else if (key === "F2") {
            this.startRename();
        } else if (key === "Enter" && sel.length === 1) {
            this.openItem(sel[0]);
        } else if (key === "Backspace" || (ev.altKey && key === "ArrowLeft")) {
            this.goBack();
        } else if (ev.altKey && key === "ArrowRight") {
            this.goForward();
        } else if (ev.altKey && key === "ArrowUp") {
            this.goUp();
        } else if (ctrl && key.toLowerCase() === "a") {
            this.selectAll();
        } else if (ctrl && key.toLowerCase() === "c") {
            this.setClipboard("copy");
        } else if (ctrl && key.toLowerCase() === "x") {
            this.setClipboard("cut");
        } else if (ctrl && key.toLowerCase() === "v") {
            // Cho sự kiện paste xử lý cả clipboard hệ điều hành và clipboard nội bộ.
            handled = false;
        } else if (ctrl && ev.shiftKey && key.toLowerCase() === "n") {
            this.newFolder();
        } else if (key === "Escape") {
            this.state.selection = {};
        } else if (key === "ArrowDown" || key === "ArrowRight" || key === "ArrowUp" || key === "ArrowLeft") {
            this.moveFocus(key === "ArrowDown" || key === "ArrowRight" ? 1 : -1, ev.shiftKey);
        } else {
            handled = false;
        }
        if (handled) {
            ev.preventDefault();
        }
    }

    moveFocus(delta, extend) {
        const items = this.items;
        if (!items.length) {
            return;
        }
        const keys = items.map(itemKey);
        const current = this.state.anchorKey ? keys.indexOf(this.state.anchorKey) : -1;
        const next = Math.max(0, Math.min(keys.length - 1, current + delta));
        const key = keys[next];
        if (extend) {
            this.state.selection[key] = true;
        } else {
            this.state.selection = { [key]: true };
        }
        this.state.anchorKey = key;
        this.scrollIntoView(key);
    }

    // ------------------------------------------------------------------
    // Hiển thị
    // ------------------------------------------------------------------
    get detailsItem() {
        const sel = this.selectedItems;
        return sel.length === 1 ? sel[0] : null;
    }

    get emptyText() {
        if (this.state.search) {
            return "Không tìm thấy mục nào khớp.";
        }
        if (this.state.trash) {
            return "Thùng rác trống.";
        }
        return "Thư mục trống. Kéo thả file/thư mục từ máy tính vào đây, hoặc bấm Mới / Tải lên.";
    }

    get canCreateHere() {
        return !this.state.trash && Boolean(this.state.data.folder?.can_create_folder);
    }

    get canUploadHere() {
        return !this.state.trash && Boolean(this.state.data.folder?.can_upload_file);
    }

    get canEditSelection() {
        const items = this.selectedItems;
        return items.length > 0 && items.every((item) => item.can_edit);
    }

    get canDeleteSelection() {
        const items = this.selectedItems;
        return items.length > 0 && items.every((item) => item.can_delete);
    }

    get canPaste() {
        return !!this.state.clipboard && this.canCreateHere;
    }

    get singleFileSelected() {
        const sel = this.selectedItems;
        return sel.length === 1 && sel[0].kind === "file" ? sel[0] : null;
    }

    typeLabel(item) {
        if (item.kind === "folder") {
            return "Thư mục";
        }
        const ext = item.name.includes(".") ? item.name.split(".").pop().toUpperCase() : "";
        const label = TYPE_LABEL[item.file_type] || "File";
        return ext && item.file_type !== "note" ? `${label} (.${ext.toLowerCase()})` : label;
    }

    iconClass(item) {
        return item.kind === "folder" ? "fa-folder" : TYPE_ICON[item.file_type] || TYPE_ICON.other;
    }
}

registry.category("actions").add("argo_documents.explorer", ArgoExplorer);
