/** @odoo-module **/
/** CRM-002 Update_003: native Odoo Kanban view + CRM-002 sidebar, NOT custom cards. */
import { onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { kanbanView } from "@web/views/kanban/kanban_view";

const COLLAPSE_KEY = "sgt_crm002_sidebar_collapsed";

// localStorage can be unavailable or throw (private window, blocked site data).
function readCollapsed() {
    try {
        return window.localStorage.getItem(COLLAPSE_KEY) === "1";
    } catch (_error) {
        return false;
    }
}

function writeCollapsed(value) {
    try {
        window.localStorage.setItem(COLLAPSE_KEY, value ? "1" : "0");
    } catch (_error) {
        /* the sidebar still works for this session */
    }
}

const viewRegistry = registry.category("views");
const crmKanbanView = viewRegistry.get("crm_kanban");

function withCrm002Sidebar(Base) {
    return class extends Base {
        static template = "sgt_crm_campaign.PipelineKanbanView";
        setup() {
            super.setup();
            this.crm002Orm = useService("orm");
            this.crm002Notification = useService("notification");
            this.crm002Action = useService("action");
            this.crm002State = useState({
                loading: true, isAdmin: false, groups: [], departments: [],
                deptId: false, userId: false,
                expanded: {}, open: {data: true, sale: true, mm: true},
                collapsed: readCollapsed(), error: "",
            });
            this.crm002StaffGroupId = null;
            onWillStart(async () => {
                try {
                    const data = await this.crm002Orm.call("sgt.crm002.service", "bootstrap", []);
                    this.crm002State.isAdmin = !!data.is_admin;
                    this.crm002State.groups = data.groups || [];
                    this.crm002State.departments = data.is_admin ? (data.departments || []) : [];
                    const ctx = this.props.context || {};
                    if (data.is_admin && ctx.crm002_department_id) {
                        const dept = this.crm002State.departments.find(d => d.id === Number(ctx.crm002_department_id));
                        if (dept) this.crm002ChooseDepartment(dept);
                    } else if (data.is_admin && ctx.crm002_user_id) {
                        const person = this.crm002State.departments.flatMap(d => d.members)
                            .find(p => p.id === Number(ctx.crm002_user_id));
                        if (person) this.crm002ChoosePerson(person);
                    }
                } catch (error) {
                    this.crm002State.error = "Không tải được Sidebar CRM-002.";
                    this.crm002Notification.add(error?.data?.message || error?.message || this.crm002State.error, {type: "warning"});
                } finally {
                    this.crm002State.loading = false;
                }
            });
        }
        get className() {
            return `${super.className || ""} sgt002-native-kanban${this.crm002State.collapsed ? " sgt002-collapsed" : ""}`;
        }
        get crm002ActiveCode() {
            return this.props.context?.sgt_crm002_funnel_code || "mm";
        }
        crm002ToggleCollapse() {
            this.crm002State.collapsed = !this.crm002State.collapsed;
            writeCollapsed(this.crm002State.collapsed);
        }
        crm002ToggleGroup(key) {
            this.crm002State.open[key] = this.crm002State.open[key] === false;
        }
        async crm002SelectFunnel(funnel) {
            if (!funnel || funnel.is_main || funnel.group === "mm") return this.crm002SelectMain();
            try {
                const action = await this.crm002Orm.call("sgt.crm002.service", "open_intake", [funnel.code], {
                    department_id: this.crm002State.isAdmin ? (this.crm002State.deptId || false) : false,
                    user_id: this.crm002State.isAdmin ? (this.crm002State.userId || false) : false,
                });
                return this.crm002Action.doAction(action);
            } catch (err) {
                this.crm002Notification.add(err?.data?.message || err?.message || "Không mở được phễu.", {type: "danger"});
            }
        }
        async crm002SelectMain() {
            return this.crm002Action.doAction("crm.crm_lead_action_pipeline", {
                additionalContext: {
                    crm002_department_id: this.crm002State.isAdmin ? (this.crm002State.deptId || false) : false,
                    crm002_user_id: this.crm002State.isAdmin ? (this.crm002State.userId || false) : false,
                    // Update_015: Administrator does not get "My Pipeline" applied automatically;
                    // other users keep the stock My Pipeline default of the action.
                    ...(this.crm002State.isAdmin ? {search_default_assigned_to_me: 0} : {}),
                },
            });
        }
        async crm002OpenSettings() {
            if (!this.crm002State.isAdmin) return;
            // Funnels, Sale stages and hand-off rules: native Odoo list/form.
            return this.crm002Action.doAction("sgt_crm_campaign.action_crm002_funnel_config");
        }
        async crm002OpenPermissions() {
            if (!this.crm002State.isAdmin) return;
            // Department entitlement per funnel (same as before, now includes the new funnels).
            return this.crm002Action.doAction("sgt_crm_campaign.action_crm002_permissions");
        }
        crm002ToggleDepartment(id) {
            this.crm002State.expanded[id] = !this.crm002State.expanded[id];
        }
        crm002ClearStaffSearch() {
            const search = this.env.searchModel;
            if (!search) return;
            if (this.crm002StaffGroupId !== null) {
                search.deactivateGroup(this.crm002StaffGroupId);
                this.crm002StaffGroupId = null;
            }
            const myFilters = Object.values(search.searchItems || {}).filter(
                item => item.name === "assigned_to_me" && item.type === "filter"
            );
            const activeIds = new Set((search.query || []).map(q => q.searchItemId));
            for (const item of myFilters) {
                if (activeIds.has(item.id)) search.deactivateGroup(item.groupId);
            }
        }
        crm002ApplyStaff(label, userIds) {
            if (!this.crm002State.isAdmin) return;
            const search = this.env.searchModel;
            if (!search) return;
            this.crm002ClearStaffSearch();
            const nextGroup = search.nextGroupId;
            search.createNewFilters([{
                description: `CRM-002: ${label}`,
                domain: [["user_id", "in", userIds.length ? userIds : [0]]],
            }]);
            this.crm002StaffGroupId = nextGroup;
        }
        crm002ChooseAll() {
            if (!this.crm002State.isAdmin) return;
            this.crm002State.deptId = false;
            this.crm002State.userId = false;
            this.crm002ClearStaffSearch();
        }
        crm002ChooseDepartment(dept) {
            if (!this.crm002State.isAdmin) return;
            this.crm002State.deptId = dept.id;
            this.crm002State.userId = false;
            this.crm002State.expanded[dept.id] = true;
            this.crm002ApplyStaff(dept.name, dept.members.map(p => p.id));
        }
        crm002ChoosePerson(person) {
            if (!this.crm002State.isAdmin) return;
            this.crm002State.deptId = false;
            this.crm002State.userId = person.id;
            this.crm002ApplyStaff(person.name, [person.id]);
        }
    };
}

const Crm002PipelineController = withCrm002Sidebar(crmKanbanView.Controller);
const Crm002IntakeController = withCrm002Sidebar(kanbanView.Controller);
viewRegistry.add("sgt_crm002_pipeline", {...crmKanbanView, Controller: Crm002PipelineController});
viewRegistry.add("sgt_crm002_intake", {...kanbanView, Controller: Crm002IntakeController});
