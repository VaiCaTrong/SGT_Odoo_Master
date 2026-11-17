/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class Crm002Workspace extends Component {
    static template = "sgt_crm_campaign.Workspace";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true, busy: false, is_admin: false,
            funnels: [], departments: [], selected: "", deptId: false, userId: false,
            expanded: {}, board: null, modal: false, tab: "permissions",
            settings: null, settingsDeptId: 0, selectedCodes: [],
            filterCode: "hunter", filterMode: "tag", filterTagId: 0, filterSourceId: 0,
        });
        this.dragLeadId = false;
        onWillStart(async () => this.initialize());
    }

    errorMessage(error) {
        return error?.data?.message || error?.message || "Không tải được dữ liệu CRM-002.";
    }

    async initialize() {
        this.state.loading = true;
        try {
            const init = await this.orm.call("sgt.crm002.service", "bootstrap", []);
            this.state.is_admin = init.is_admin;
            this.state.funnels = init.funnels;
            this.state.departments = init.departments;
            const requested = this.props.action?.params?.crm002_funnel;
            this.state.selected = init.funnels.some((f) => f.code === requested)
                ? requested : (init.funnels.some((f) => f.code === this.state.selected)
                    ? this.state.selected : (init.funnels[0]?.code || ""));
            if (init.is_admin) {
                const deptId = Number(this.props.action?.params?.crm002_department_id || 0);
                const userId = Number(this.props.action?.params?.crm002_user_id || 0);
                this.state.deptId = deptId && init.departments.some(d => d.id === deptId) ? deptId : false;
                this.state.userId = userId && init.departments.some(d => d.members.some(m => m.id === userId)) ? userId : false;
                if (this.state.userId) this.state.deptId = false;
            }
            await this.loadBoard();
            const openSettings = this.props.action?.params?.crm002_open_settings;
            if (init.is_admin && ["filters", "permissions"].includes(openSettings)) {
                await this.openSettings(openSettings);
            }
        } catch (err) {
            this.notification.add(this.errorMessage(err), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    get selectedFunnel() {
        return this.state.funnels.find((f) => f.code === this.state.selected);
    }

    cardsFor(stageKey) {
        return (this.state.board?.cards || []).filter((c) => c.stage === stageKey);
    }

    async loadBoard(append = false) {
        if (!this.state.selected) {
            this.state.board = null;
            return;
        }
        this.state.busy = true;
        try {
            const previous = this.state.board;
            const offset = append && previous ? previous.cards.length : 0;
            const result = await this.orm.call(
                "sgt.crm002.service", "board", [this.state.selected], {
                    department_id: this.state.deptId || false,
                    user_id: this.state.userId || false,
                    offset, limit: 100,
                }
            );
            if (append && previous) {
                result.cards = [...previous.cards, ...result.cards];
            }
            this.state.board = result;
        } catch (err) {
            this.notification.add(this.errorMessage(err), { type: "danger" });
            if (!append) {
                this.state.board = null;
            }
        } finally {
            this.state.busy = false;
        }
    }

    async selectFunnel(code) {
        if (this.state.busy) return;
        const funnel = this.state.funnels.find((f) => f.code === code);
        if (!funnel) return;
        if (funnel.is_main) {
            await this.openNativePipeline();
            return;
        }
        this.state.selected = code;
        await this.loadBoard();
    }

    async selectAllStaff() {
        this.state.deptId = false;
        this.state.userId = false;
        await this.loadBoard();
    }

    async selectDepartment(dept) {
        if (!this.state.is_admin) return;
        this.state.deptId = dept.id;
        this.state.userId = false;
        this.state.expanded[dept.id] = true;
        await this.loadBoard();
    }

    toggleDepartment(deptId) {
        this.state.expanded[deptId] = !this.state.expanded[deptId];
    }

    async selectPerson(person) {
        if (!this.state.is_admin) return;
        this.state.deptId = false;
        this.state.userId = person.id;
        await this.loadBoard();
    }

    get staffLabel() {
        if (this.state.userId) {
            for (const dept of this.state.departments) {
                const found = dept.members.find((p) => p.id === this.state.userId);
                if (found) return found.name;
            }
        }
        if (this.state.deptId) {
            return this.state.departments.find((d) => d.id === this.state.deptId)?.name || "Department";
        }
        return "All";
    }

    openLead(card) {
        // Odoo Form opens under original CRM ACL; never sudo, never duplicate.
        this.action.doAction({
            type: "ir.actions.act_window", name: card.name, res_model: "crm.lead",
            res_id: card.id, views: [[false, "form"]], target: "current",
        });
    }

    openNativePipeline() {
        // Main CRM pipeline stays 100% native (including CRM-001 card timing).
        // Our inherited Kanban controller adds the same left sidebar.
        this.action.doAction("crm.crm_lead_action_pipeline", {
            additionalContext: {
                crm002_department_id: this.state.is_admin ? (this.state.deptId || false) : false,
                crm002_user_id: this.state.is_admin ? (this.state.userId || false) : false,
            },
        });
    }

    dragStart(ev, card) {
        if (this.state.board?.is_main || card.closed) {
            ev.preventDefault();
            return;
        }
        this.dragLeadId = card.id;
        ev.dataTransfer.setData("text/plain", String(card.id));
        ev.dataTransfer.effectAllowed = "move";
    }

    allowDrop(ev) {
        if (!this.state.board?.is_main) ev.preventDefault();
    }

    async dropOn(ev, key) {
        if (this.state.board?.is_main) return;
        ev.preventDefault();
        const id = Number(ev.dataTransfer.getData("text/plain") || this.dragLeadId);
        this.dragLeadId = false;
        if (id) await this.moveStage(id, key);
    }

    async moveStage(leadId, key) {
        if (!this.state.selected || this.state.busy) return;
        this.state.busy = true;
        try {
            await this.orm.call("sgt.crm002.service", "move", [this.state.selected, leadId, key]);
            await this.loadBoard();
        } catch (err) {
            this.notification.add(this.errorMessage(err), { type: "danger" });
        } finally {
            this.state.busy = false;
        }
    }

    async openSettings(tab = "permissions") {
        if (!this.state.is_admin) return;
        this.state.modal = true;
        this.state.tab = tab;
        try {
            this.state.settings = await this.orm.call("sgt.crm002.service", "settings", []);
            this.state.settingsDeptId = this.state.settings.departments[0]?.id || 0;
            this.loadPermissionSelection();
            this.state.filterCode = this.state.settings.funnels.find((f) => !f.is_main)?.code || "hunter";
            this.loadFilterSelection();
        } catch (err) {
            this.notification.add(this.errorMessage(err), { type: "danger" });
            this.state.modal = false;
        }
    }

    loadPermissionSelection() {
        const depId = Number(this.state.settingsDeptId);
        this.state.selectedCodes = (this.state.settings?.funnels || [])
            .filter((f) => f.department_ids.includes(depId)).map((f) => f.code);
    }

    changeSettingsDepartment(ev) {
        this.state.settingsDeptId = Number(ev.target.value) || 0;
        this.loadPermissionSelection();
    }

    togglePermission(code, checked) {
        this.state.selectedCodes = checked
            ? [...new Set([...this.state.selectedCodes, code])]
            : this.state.selectedCodes.filter((c) => c !== code);
    }

    async savePermissions() {
        if (!this.state.settingsDeptId) return;
        this.state.busy = true;
        try {
            await this.orm.call("sgt.crm002.service", "save_permissions", [
                Number(this.state.settingsDeptId), this.state.selectedCodes,
            ]);
            this.notification.add("Đã lưu phân quyền Department.", { type: "success" });
            this.state.settings = await this.orm.call("sgt.crm002.service", "settings", []);
            this.loadPermissionSelection();
        } catch (err) {
            this.notification.add(this.errorMessage(err), { type: "danger" });
        } finally {
            this.state.busy = false;
        }
    }

    loadFilterSelection() {
        const cfg = this.state.settings?.funnels.find((f) => f.code === this.state.filterCode);
        if (!cfg) return;
        this.state.filterMode = cfg.filter_mode;
        const fromName = this.state.settings.tags.find((t) => t.name === cfg.initial_tag_name);
        this.state.filterTagId = cfg.tag_id || fromName?.id || 0;
        this.state.filterSourceId = cfg.source_id || 0;
    }

    changeFilterFunnel(ev) {
        this.state.filterCode = ev.target.value;
        this.loadFilterSelection();
    }

    changeFilterTag(ev) {
        this.state.filterTagId = Number(ev.target.value) || 0;
    }

    changeFilterSource(ev) {
        this.state.filterSourceId = Number(ev.target.value) || 0;
    }

    async saveFilter() {
        this.state.busy = true;
        try {
            await this.orm.call("sgt.crm002.service", "save_filter", [
                this.state.filterCode, this.state.filterMode,
                Number(this.state.filterTagId) || false, Number(this.state.filterSourceId) || false,
            ]);
            this.notification.add("Đã lưu cấu hình Tag/Source.", { type: "success" });
            this.state.settings = await this.orm.call("sgt.crm002.service", "settings", []);
            await this.loadBoard();
        } catch (err) {
            this.notification.add(this.errorMessage(err), { type: "danger" });
        } finally {
            this.state.busy = false;
        }
    }
}

registry.category("actions").add("sgt_crm002.workspace", Crm002Workspace);
