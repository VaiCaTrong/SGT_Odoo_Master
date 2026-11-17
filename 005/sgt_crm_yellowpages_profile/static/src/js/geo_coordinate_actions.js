/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Display Copy / Google Maps actions next to CRM-005's existing editable floats.
 * No RPC, Contact write, database field or third-party geocoding is involved.
 */
export class Crm005GeoActions extends Component {
    static template = "sgt_crm_yellowpages_profile.GeoCoordinateActions";
    static props = { ...standardFieldProps };
    static supportedTypes = ["selection"];

    setup() {
        this.notification = useService("notification");
    }

    get coordinates() {
        const data = this.props.record?.data || {};
        const lat = Number(data.x_yp_latitude);
        const lon = Number(data.x_yp_longitude);
        if (!Number.isFinite(lat) || !Number.isFinite(lon) ||
            Math.abs(lat) > 90 || Math.abs(lon) > 180 ||
            (lat === 0 && lon === 0)) {
            return null;
        }
        return `${lat}, ${lon}`;
    }

    get mapUrl() {
        if (!this.coordinates) return "";
        return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(this.coordinates)}`;
    }

    async copyCoordinates(event) {
        event.preventDefault();
        event.stopPropagation();
        const value = this.coordinates;
        if (!value) return;
        try {
            if (!navigator.clipboard?.writeText) throw new Error("Clipboard API unavailable");
            await navigator.clipboard.writeText(value);
            this.notification.add("Coordinates copied", { type: "success" });
            return;
        } catch {
            // Chromium fallback on contexts that deny Clipboard API.
            const el = document.createElement("textarea");
            el.value = value;
            el.setAttribute("readonly", "");
            el.style.position = "fixed";
            el.style.left = "-9999px";
            document.body.appendChild(el);
            let copied = false;
            try {
                el.select();
                copied = document.execCommand("copy");
            } catch {
                copied = false;
            } finally {
                el.remove();
            }
            if (copied) {
                this.notification.add("Coordinates copied", { type: "success" });
            } else {
                this.notification.add(`Could not copy automatically. Coordinates: ${value}`,
                    { type: "warning", sticky: true });
            }
        }
    }
}

registry.category("fields").add("sgt_crm005_geo_actions", {
    component: Crm005GeoActions,
    supportedTypes: ["selection"],
});
