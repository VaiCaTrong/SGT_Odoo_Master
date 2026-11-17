// Run: node tests_update010_js.cjs  — executes the REAL Update_010 JS (extracted text) with fakes.
const fs = require("fs");
const assert = require("assert");
const path = require("path");
const dir = path.join(__dirname, "static/src/explorer");
const src = fs.readFileSync(path.join(dir, "explorer.js"), "utf8");
const a = src.indexOf("// Update_010: cập nhật ảnh Documents");
const b = src.indexOf("// Quyền xem");
assert(a > 0 && b > a, "markers");
// body = from the start of the section comment block to the start of the next comment block
const bodyStart = src.lastIndexOf("    // ----", a);
const bodyEnd = src.lastIndexOf("    // ----", b);
const body = src.slice(bodyStart, bodyEnd);
const Cls = new Function("ArgoCrmTargetDialog", "FOLDER_MODEL",
    `return class T { ${body}
       get selectedItems() { return this._sel || []; }
       closeMenus() { this.closed = (this.closed || 0) + 1; } };`)("DLG", "argo.document.folder");

const ROOT = 1;
function make(over = {}) {
    const t = new Cls();
    t.state = Object.assign({
        config: { crm_push_available: true, crm_root_folder_id: ROOT },
        folderId: 5, trash: false, search: "",
        data: { breadcrumb: [{ id: ROOT }, { id: 5 }], files: [] },
    }, over);
    t.notes = []; t.dialogs = []; t.calls = [];
    t.notification = { add: (m, o) => t.notes.push([m, o]) };
    t.dialog = { add: (c, p) => t.dialogs.push([c, p]) };
    t.orm = { call: async (...a) => { t.calls.push(a); return t.reply(a); } };
    t.reply = () => ({});
    return t;
}
const img = (id) => ({ kind: "file", id, file_type: "image" });
const pdf = (id) => ({ kind: "file", id, file_type: "pdf" });
const fol = (id) => ({ kind: "folder", id });

(async () => {
    // ---- pushInfo
    let t = make({ config: { crm_push_available: false, crm_root_folder_id: ROOT } });
    assert.strictEqual(t.pushInfo, null, "feature off when 005 missing");
    t = make({ folderId: ROOT, data: { breadcrumb: [{ id: ROOT }], files: [img(1)] } }); assert.strictEqual(t.pushInfo, null, "not on the CRM root itself");
    t = make({ trash: true }); assert.strictEqual(t.pushInfo, null);
    t = make({ search: "abc" }); assert.strictEqual(t.pushInfo, null);
    t = make({ folderId: 9, data: { breadcrumb: [{ id: 3 }, { id: 9 }], files: [img(1)] } });
    assert.strictEqual(t.pushInfo, null, "folder outside CRM Information");
    t = make({ config: {} }); assert.strictEqual(t.pushInfo, null);

    t = make(); t._sel = [fol(77)];
    assert.deepStrictEqual(t.pushInfo, { label: "Cập nhật ảnh lên CRM", folderId: 77, documentIds: null });
    t = make(); t._sel = [img(1), pdf(2), img(3), img(4)];
    assert.deepStrictEqual(t.pushInfo, { label: "Cập nhật 3 ảnh lên CRM", folderId: 5, documentIds: [1, 3, 4] });
    t = make(); t._sel = [img(8)];
    assert.strictEqual(t.pushInfo.label, "Cập nhật ảnh này lên CRM");
    t = make(); t._sel = [pdf(2)]; assert.strictEqual(t.pushInfo, null);
    t = make(); t._sel = [fol(1), fol(2)]; assert.strictEqual(t.pushInfo, null, "several folders: not ambiguous-guessed");
    t = make({ data: { breadcrumb: [{ id: ROOT }], files: [img(1), pdf(2), img(3)] } });
    assert.deepStrictEqual(t.pushInfo, { label: "Cập nhật ảnh lên CRM (2 ảnh)", folderId: 5, documentIds: null });
    t = make({ data: { breadcrumb: [{ id: ROOT }], files: [pdf(2)] } });
    assert.strictEqual(t.pushInfo, null, "no image => no button");

    // ---- flow: no lead / no writable lead
    t = make(); t.reply = () => ({ leads: [] });
    await t.pushImagesToCrm(5, null);
    assert.strictEqual(t.calls.length, 1); assert.strictEqual(t.notes[0][1].type, "warning");
    t = make(); t.reply = () => ({ leads: [{ id: 1, can_write: false }] });
    await t.pushImagesToCrm(5, null);
    assert.strictEqual(t.calls.length, 1); assert.match(t.notes[0][0], /quyền sửa Deal/);

    // ---- flow: one lead => straight to push with exact args
    t = make();
    t.reply = (a) => a[1] === "explorer_crm_targets" ? { leads: [{ id: 11, can_write: true }] }
        : { added: 3, duplicate: 1, skipped: [], not_image: 0 };
    await t.pushImagesToCrm(5, [1, 2, 3]);
    assert.deepStrictEqual(t.calls[1], ["argo.document.folder", "explorer_push_images_to_crm", [5, 11, [1, 2, 3]]]);
    assert.match(t.notes[0][0], /Deal #11.*Thêm mới: 3 ảnh.*Bỏ qua \(đã có\): 1/);
    assert.strictEqual(t.notes[0][1].type, "success");
    assert.strictEqual(t.pushing, false);
    // whole folder => documentIds false (not null) on the wire
    t.calls = []; await t.pushImagesToCrm(5, null);
    assert.strictEqual(t.calls[1][2][2], false);

    // ---- flow: several leads => dialog, nothing pushed until confirmed
    t = make();
    t.reply = (a) => a[1] === "explorer_crm_targets"
        ? { leads: [{ id: 11, can_write: true }, { id: 12, can_write: true }] } : { added: 1, skipped: [] };
    await t.pushImagesToCrm(5, [9]);
    assert.strictEqual(t.calls.length, 1); assert.strictEqual(t.dialogs.length, 1);
    assert.strictEqual(t.dialogs[0][0], "DLG");
    assert.strictEqual(t.dialogs[0][1].summary, "1 ảnh đã chọn");
    await t.dialogs[0][1].onConfirm(12);
    assert.deepStrictEqual(t.calls[1][2], [5, 12, [9]]);

    // ---- errors and warnings
    t = make();
    t.reply = (a) => { if (a[1] === "explorer_crm_targets") return { leads: [{ id: 11, can_write: true }] };
        throw { data: { message: "Không có quyền" } }; };
    await t.pushImagesToCrm(5, null);
    assert.strictEqual(t.notes[0][1].type, "danger"); assert.strictEqual(t.notes[0][0], "Không có quyền");
    assert.strictEqual(t.pushing, false, "guard released after error");
    t = make();
    t.reply = (a) => a[1] === "explorer_crm_targets" ? { leads: [{ id: 11, can_write: true }] }
        : { added: 1, duplicate: 0, skipped: [{ name: "x.gif", reason: "Định dạng GIF" }], truncated: true, limit: 200, not_image: 2 };
    await t.pushImagesToCrm(5, null);
    assert.strictEqual(t.notes[0][1].type, "warning"); assert.match(t.notes[0][0], /Không phải ảnh: 2/);
    assert.match(t.notes[0][0], /Chỉ lấy 200/); assert.match(t.notes[1][0], /x\.gif: Định dạng GIF/);
    // re-entrancy guard
    t = make(); t.pushing = true; await t.pushImagesToCrm(5, null); assert.strictEqual(t.calls.length, 0);
    t = make(); await t.pushImagesToCrm(false, null); assert.strictEqual(t.calls.length, 0);

    // ---- dialog class
    const dsrc = fs.readFileSync(path.join(dir, "dialogs.js"), "utf8");
    const i = dsrc.indexOf("export class ArgoCrmTargetDialog");
    const cls = dsrc.slice(i).replace("export class", "class");
    const D = new Function("Component", "useState", "Dialog", `${cls}; return ArgoCrmTargetDialog;`)(class { }, (x) => x, {});
    const mk = (leads) => { const d = new D(); d.props = { leads, close: () => { d.closed = true; }, onConfirm: async (id) => { d.got = id; } }; d.setup(); return d; };
    let d = mk([{ id: 1, can_write: false }, { id: 2, can_write: true }]);
    assert.strictEqual(d.state.leadId, 2, "first writable preselected");
    d.choose({ id: 1, can_write: false }); assert.strictEqual(d.state.leadId, 2, "read-only lead cannot be chosen");
    await d.confirm(); assert.strictEqual(d.got, 2); assert.ok(d.closed); assert.strictEqual(d.state.busy, false);
    d = mk([{ id: 1, can_write: false }]); assert.strictEqual(d.state.leadId, false);
    await d.confirm(); assert.strictEqual(d.got, undefined);
    console.log("JS OK");
})().catch((e) => { console.error(e); process.exit(1); });
