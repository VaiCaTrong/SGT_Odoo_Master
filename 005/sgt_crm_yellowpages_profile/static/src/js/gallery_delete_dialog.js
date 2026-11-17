/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * CRM-005 Update_067: confirmation box for deleting Image Gallery pictures (one picture from the ×
 * button, or the pictures ticked in "Select images" mode).  It shows the pictures that are about to
 * be deleted so nobody confirms blind.  Pure presentation: the caller passes `confirm`, which makes
 * the protected RPC; nothing is sent until the Delete button is pressed.
 */
export const DELETE_DIALOG_MAX_THUMBS = 24;

export class SGTGalleryDeleteDialog extends Component {
    static template = "sgt_crm_yellowpages_profile.GalleryDeleteDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        title: String,
        thumbs: Array,          // src of the pictures to show (at most DELETE_DIALOG_MAX_THUMBS)
        count: Number,          // how many pictures will be deleted
        total: Number,          // how many pictures the gallery holds
        confirm: Function,
        confirmLabel: String,
    };

    setup() {
        this.state = useState({ busy: false });
        this.env.dialogData.dismiss = () => this.props.close();
    }

    get single() {
        return this.props.count === 1;
    }

    get extra() {
        return Math.max(0, this.props.count - this.props.thumbs.length);
    }

    get deletesAll() {
        return this.props.count > 1 && this.props.count >= this.props.total;
    }

    get message() {
        const n = this.props.count;
        return n === 1
            ? "Delete this picture from the Image Gallery? This change cannot be undone."
            : `Delete these ${n} pictures from the Image Gallery? This change cannot be undone.`;
    }

    async onConfirm() {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            await this.props.confirm();
        } catch (error) {
            this.props.close();
            throw error;
        }
        this.props.close();
    }

    onCancel() {
        if (!this.state.busy) {
            this.props.close();
        }
    }
}
