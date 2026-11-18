from odoo import _, models


class CrmLeadMmApprovalButton(models.Model):
    """CRM-005 Update_068: form-button entry for the MM approval of crm_mm_approval_bridge."""

    _inherit = "crm.lead"

    def action_crm005_approve_mm(self):
        """Runs the SAME approval as the old toolbar (`action_approve_mm`: permission check, remote MM card,
        chatter/field sync, move to the configured Won stage) and then shows a green success message and
        softly reloads the form so the stage bar, Deal ID and the box refresh at once."""
        self.ensure_one()
        self.action_approve_mm()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Phê duyệt thành công"),
                "message": _("Đã tạo Match Making (MM ID %(mm)s) và chuyển deal sang %(stage)s.") % {
                    "mm": self.x_mm_remote_id,
                    "stage": self.stage_id.display_name,
                },
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }
