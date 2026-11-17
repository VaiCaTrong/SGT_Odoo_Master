import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

/** Sửa nhanh file .txt ngay trên web */
export class ArgoTextEditorDialog extends Component {
    static template = "argo_documents.TextEditorDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        title: String,
        content: String,
        onSave: Function,
    };

    setup() {
        this.state = useState({ content: this.props.content, saving: false, dirty: false });
        this.textarea = useRef("textarea");
        onMounted(() => this.textarea.el?.focus());
    }

    onInput(ev) {
        this.state.content = ev.target.value;
        this.state.dirty = true;
    }

    onKeydown(ev) {
        if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "s") {
            ev.preventDefault();
            this.save();
        }
    }

    async save() {
        this.state.saving = true;
        try {
            await this.props.onSave(this.state.content);
            this.props.close();
        } finally {
            this.state.saving = false;
        }
    }
}

/** Chọn phòng ban và/hoặc người được xem thư mục */
export class ArgoShareDialog extends Component {
    static template = "argo_documents.ShareDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        folderName: String,
        users: Array,
        departments: { type: Array, optional: true },
        selected: Array,
        selectedDepartments: { type: Array, optional: true },
        inherited: Array,
        accessMode: { type: String, optional: true },
        publicLevel: { type: String, optional: true },
        userGrants: { type: Array, optional: true },
        departmentGrants: { type: Array, optional: true },
        onSave: Function,
    };

    setup() {
        const selectedDepartments = this.props.selectedDepartments || [];
        this.state = useState({
            mode: this.props.accessMode && this.props.accessMode !== "legacy"
                ? this.props.accessMode
                : this.props.selected.length || selectedDepartments.length ? "restricted" : "public",
            publicLevel: this.props.publicLevel || "view",
            userLevels: Object.fromEntries((this.props.userGrants || []).map((p) => [p.id, p.level])),
            departmentLevels: Object.fromEntries((this.props.departmentGrants || []).map((p) => [p.id, p.level])),
            selected: new Set(this.props.selected),
            selectedDepartments: new Set(selectedDepartments),
            search: "",
            searchDepartment: "",
            saving: false,
        });
    }

    get departments() {
        return this.props.departments || [];
    }

    get filteredUsers() {
        const q = this.state.search.trim().toLowerCase();
        return q ? this.props.users.filter((u) => u.name.toLowerCase().includes(q)) : this.props.users;
    }

    get filteredDepartments() {
        const q = this.state.searchDepartment.trim().toLowerCase();
        return q ? this.departments.filter((d) => d.name.toLowerCase().includes(q)) : this.departments;
    }

    /** Có chọn phòng ban nhưng không phòng nào có nhân viên gắn tài khoản: chỉ quản lý kho thấy thư mục. */
    get emptyDepartmentsWarning() {
        if (!this.state.selectedDepartments.size) {
            return false;
        }
        const chosen = this.departments.filter((d) => this.state.selectedDepartments.has(d.id));
        return !this.state.selected.size && chosen.length > 0 && chosen.every((d) => !d.user_count);
    }

    get canSave() {
        return !this.state.saving
            && (this.state.mode !== "restricted" || this.state.selected.size + this.state.selectedDepartments.size > 0);
    }

    toggle(user) {
        if (this.state.selected.has(user.id)) {
            this.state.selected.delete(user.id);
            delete this.state.userLevels[user.id];
        } else {
            this.state.selected.add(user.id);
            this.state.userLevels[user.id] = "view";
        }
    }

    toggleDepartment(department) {
        if (this.state.selectedDepartments.has(department.id)) {
            this.state.selectedDepartments.delete(department.id);
            delete this.state.departmentLevels[department.id];
        } else {
            this.state.selectedDepartments.add(department.id);
            this.state.departmentLevels[department.id] = "view";
        }
    }

    async save() {
        if (!this.canSave) {
            return;
        }
        this.state.saving = true;
        try {
            const userIds = this.state.mode === "restricted" ? [...this.state.selected] : [];
            const departmentIds = this.state.mode === "restricted" ? [...this.state.selectedDepartments] : [];
            const userGrants = userIds.map((id) => ({ id, level: this.state.userLevels[id] || "view" }));
            const departmentGrants = departmentIds.map((id) => ({ id, level: this.state.departmentLevels[id] || "view" }));
            await this.props.onSave(userIds, departmentIds, this.state.mode,
                this.state.publicLevel, userGrants, departmentGrants);
            this.props.close();
        } finally {
            this.state.saving = false;
        }
    }
}

/** Ô nhập đổi tên tại chỗ (giống Windows: chọn sẵn phần tên, không chọn đuôi file) */
export class ArgoRenameInput extends Component {
    static template = "argo_documents.RenameInput";
    static props = {
        value: String,
        isFile: { type: Boolean, optional: true },
        onCommit: Function,
        onCancel: Function,
        multiline: { type: Boolean, optional: true },
    };

    setup() {
        this.input = useRef("input");
        this.done = false;
        onMounted(() => {
            const el = this.input.el;
            if (!el) {
                return;
            }
            el.focus();
            const dot = this.props.value.lastIndexOf(".");
            el.setSelectionRange(0, this.props.isFile && dot > 0 ? dot : this.props.value.length);
        });
    }

    onKeydown(ev) {
        ev.stopPropagation();
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.commit();
        } else if (ev.key === "Escape") {
            ev.preventDefault();
            this.done = true;
            this.props.onCancel();
        }
    }

    async commit() {
        if (this.done || !this.input.el) {
            return;
        }
        this.done = true;
        const ok = await this.props.onCommit(this.input.el.value);
        if (ok === false && this.input.el) {
            this.done = false; // lỗi (trùng tên...) -> cho sửa tiếp
            this.input.el.focus();
        }
    }
}

/** Update_010: chọn Deal nhận ảnh khi folder dùng chung cho nhiều Deal (cùng MST) */
export class ArgoCrmTargetDialog extends Component {
    static template = "argo_documents.CrmTargetDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        leads: Array,
        summary: String,
        onConfirm: Function,
    };

    setup() {
        const first = this.props.leads.find((l) => l.can_write);
        this.state = useState({ leadId: first ? first.id : false, busy: false });
    }

    choose(lead) {
        if (lead.can_write) {
            this.state.leadId = lead.id;
        }
    }

    async confirm() {
        if (!this.state.leadId || this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            this.props.close();
            await this.props.onConfirm(this.state.leadId);
        } finally {
            this.state.busy = false;
        }
    }
}
