## Update_067 (CRM-005): chọn nhiều ảnh chỉ Admin + hộp xác nhận xóa có ảnh thu nhỏ
Xem `UPDATE_067_NOTES.md`. Xóa nhiều ảnh chỉ Admin (giao diện `user.isSystem` + máy chủ `env.is_system()`); nút × giữ nguyên cho mọi người; hộp `SGTGalleryDeleteDialog` dùng chung cho xóa 1 và xóa nhiều. Manifest 19.0.1.66.0, không field, không migration.

## Update_066 (CRM-005): Image Gallery chọn nhiều ảnh để xóa hàng loạt (chế độ debug)
Xem `UPDATE_066_NOTES.md`. Hàm `crm.lead.action_crm005_delete_gallery_images` (1 lần ghi, kiểm quyền ghi + dấu vân tay từng ảnh), thanh "Select images" trong widget Gallery. Manifest 19.0.1.65.0, không field, không migration.

## Update_065 (CRM-005): sửa lỗi ảnh đẩy từ Documents hiện thành chữ HTML
Xem `UPDATE_065_NOTES.md`. Manifest 19.0.1.64.0; tự sửa thẻ đã hỏng khi bấm cập nhật lại.

## Update_064 (CRM-005): ảnh Documents → Image Gallery, ẩn box rỗng
Xem `UPDATE_064_NOTES.md`. Hàm `crm.lead.crm005_push_documents_to_gallery`, CSS ẩn box Gallery/Partners rỗng, nút xanh trong box Documents. Manifest 19.0.1.63.0, không migration. Làm cặp với Documents-008 Update_010.

## Update_046 (CRM-005): tên công ty Kanban nhỏ hơn và tự xuống dòng

- Tên nằm bên phải logo cùng hàng ngang, **16px trên desktop / 15px trên mobile, in đậm**; tự xuống nhiều dòng, không cắt mất chữ.
- Bỏ hiệu ứng marquee **chỉ với tên công ty trên Kanban**; giữ script cũ cho các field khác.
- Giữ nút New, kéo Deal, khoảng cách Kanban 16px, Documents, Gallery và các tính năng cũ.
- Manifest `19.0.1.45.0`; xem `UPDATE_046_NOTES.md`.

## Update_038 (CRM-005): 16px vertical gap between Opportunity Kanban cards

- Based on Update_037, apply `margin-bottom: 16px !important` to the **real** `.o_kanban_record` inside `.o_opportunity_kanban .o_kanban_group` via existing CRM-005 backend CSS.
- Unlike adding `class="mb-3"` to the XML template, this targets rendered Kanban cards. Only Opportunity Kanban card spacing changes; all form fields, logo, title marquee, read-only navigation, gallery and permissions stay unchanged.
- Manifest `19.0.1.37.0`. No database migration or new dependency. Validate in staging (theme/assets can affect effective visual gap). Details: `UPDATE_038_NOTES.md`.

## Update_037 (CRM-005): larger Kanban company name, card-wide hover

- Building on Update_036, show the company name **20px / 700 bold** on desktop and **18px / 700 bold** on narrower mobile screens, right of the existing 52px / 44px logo.
- Hovering **anywhere on the CRM opportunity Kanban card** (logo, other field, empty area) scrolls the **company name only** if it is truncated; leaving the entire card resets the name. Short names stay still. Respects reduced-motion settings; no new data field or RPC.
- Click the company name/logo to open the Deal form as in Update_036. Kanban stays view/navigation-only; no edits to CRM Sales permissions, CRM-002, form or image gallery.
- Release package Update_037 / manifest `19.0.1.36.0`. Offline validation only until tested on live/staging Odoo Kanban.

## Update_036 — Company name / hover marquee / Kanban view-only (2026-11-07)

- Company name next to the existing Kanban logo is larger (16px desktop / 15px mobile) and bold (700). Long names slide horizontally on mouse hover via the previously installed `sgt_marquee.js`; short names do not animate.
- Click the logo or the company name to open the correct CRM Deal form via Odoo-native `type="open"`.
- Kanban becomes view/navigation-only: disables dragging cards or stage columns, creating/editing/deleting from the Kanban, and the color picker. The clickable activity widget becomes a passive activity-state label; full editing stays available in the Deal form according to existing CRM rights.
- No new fields, schema migrations, ACLs, RPCs, or changes to CRM-002/Extension. See `UPDATE_036_NOTES.md` for tests and staging preflight.

## Update_035 — Company logo in Opportunity Kanban (2026-11-07)

- Shows the CRM-005 company logo to the **left of the company name** on the existing Xinyang Opportunity Kanban card; retains other card fields.
- Logo priority: manual `x_yp_logo_upload`, then extension `x_image`, then neutral grey building icon for missing/broken images. Size 52×52 px (44×44 on narrow screens).
- No new database columns, backend RPC, groups or additional modules. The only Kanban change is a view extension of `crm.crm_case_kanban_view_leads`.
- Prerequisite: the live Kanban still has the `x_company` field row identified in the 2026-10-11 Xinyang Scan. Review `UPDATE_035_NOTES.md` before upgrading; offline tests do not prove production compatibility.

# CRM-005 — Yellow Pages company profile (V01 Update_032)

Addon: `sgt_crm_yellowpages_profile` · version `19.0.1.31.0` · Odoo 19 · depends: `crm`, `crm_sync_contact_odoo2`.
**Install on Demo 2 (xinyangdemo2.sge.vn) first. Do NOT install on Production before Demo 2 passes.**

## What Update_032 changes on top of Update_031 (owner request 2026-10-31 08:32–08:38, mock-ups E1–E4, approved 08:50)
- **New box "Evidence"** below Partners (above the tabs and Detail Fields): pictures pasted by hand — click in the box, **Ctrl+V** (screenshots, pictures copied from Zalo / Facebook...).
  Several pictures allowed; select a picture + Delete to remove it. Always open. Head chip: **No picture yet** (red) / **Picture attached** (green), pure CSS.
- **New field (approved 2026-10-31 08:50): `x_yp_evidence_html`** (Html, editable, `copy=False`). The Chrome extension never writes it; CRM-006 does not push it to the Contact.
- With **CRM-002 Update_025** installed: a Deal without a picture here counts as missing data (bell), and the box is framed in red when the bell is clicked
  or automatically when the Deal is in 5.Match Making / 6.Approved Match Making. Without CRM-002 the box works alone (no red frame).
- No JS, no API, no cron. Version 19.0.1.31.0. Cumulative (021 to 031 included). Upgrade adds one database column (crm_lead.x_yp_evidence_html).
- Check on Demo 2: paste a screenshot (Ctrl+V) into the box, Save, reload: the picture must stay (Odoo stores pasted pictures as attachments of the Deal).

## What Update_031 changes on top of Update_030 (owner request 2026-10-30 16:12, design 3 approved 16:14)
- **Full address on the Company card**: line 1 = Street (with the map pin); line 2 = Street 2, City, **State, ZIP, Country** (new on the card, aligned under the Street text;
  wraps when the form is narrow). Same existing crm.lead fields (`state_id`, `zip`, `country_id`); no new field, no JS. Detail Fields keeps its own copies.
- Why: Contact addresses (CRM-006 / 007, map coordinates) need them. Note (seen on deal 2797): the Chrome extension writes the whole address into Street; Street 2 / City / State / ZIP / Country
  stay empty until filled by hand or until the extension splits the address.
- Version 19.0.1.30.0. Cumulative (021 to 030 included).

## What Update_030 changes on top of Update_029 (owner request 2026-10-30 14:51)
- The "?" of Developer Mode **below the logo (above the upload buttons) stays**; only the "?" inside the logo box remains hidden. CSS only. Version 19.0.1.29.0. Cumulative (021 to 029 included).

## What Update_029 changes on top of Update_028 (owner screenshot 2026-10-30 14:49)
- The words "Change logo" are replaced by a pencil icon (fa-pencil) on the same blue-outline button (the words were overflowing the frame next to the download icon).
  Empty state still says "Upload logo".
- The two "?" of Developer Mode around the logo (inside the logo box and above the upload buttons) are hidden.
- CSS only. Version 19.0.1.28.0. Cumulative (021 to 028 included).

## What Update_028 changes on top of Update_027 (owner screenshot 2026-10-30 14:40, approved mock-up 14:42)
- After an upload the Odoo binary widget prints the start of the file content as text ("iVBC...") and squeezed the button into two lines (and the button text
  was in a serif font because Odoo's `.btn` leaves the font unset). Now: that text is hidden; the button takes the free width; the Odoo `.btn` font is replaced by the form font;
  the button says **Upload logo** when empty and **Change logo** once a picture is uploaded; the clear button is a square blue-outline trash button of the same height.
- CSS only. Version 19.0.1.27.0. Cumulative (021 to 027 included).
- Not verifiable offline: the exact class names of the Odoo 19 binary widget (`.o_select_file_button`, `.o_clear_file_button`, the hidden `input`). If something still looks wrong, send a screenshot.

## What Update_027 changes on top of Update_026 (owner screenshot 2026-10-30 14:38, Developer Mode)
- **Upload logo button text fixed**: on the real form the button was squeezed to ~17 px (Odoo's own `.btn` rules overrode the padding), so the text touched/overflowed the frame
  and looked broken. The button now has a minimum height (2.1 rem), forced padding and display, so the text always sits fully inside the blue frame.
- **Developer Mode**: the "Upload Logo" text label above the button (which repeated the button wording in another spelling) is no longer visible; only its "?" remains.
- CSS only. Version 19.0.1.26.0. Cumulative (021 to 026 included).

## What Update_026 changes on top of Update_025 (owner request 2026-10-30 14:26)
- **Upload logo wording fixed**: the text looked pushed to one side because a blank slot was left for the upload icon. The icon is removed; the text
  "Upload logo" is centred, upright (no italic / transform), semi-bold, normal letter spacing.
- CSS only. Version 19.0.1.25.0. Cumulative (021 to 025 included).

## What Update_025 changes on top of Update_024 (owner request 2026-10-30 14:25)
- **Upload logo button = blue outline only** (blue border + blue text + icon, transparent background; light-blue tint on hover). No filled background.
- CSS only. Version 19.0.1.24.0. Cumulative (021 to 024 included).

## What Update_024 changes on top of Update_023 (owner request 2026-10-30 14:23)
- **Upload logo button restyled**: same colour as the rest of the layout (brand blue #0061BD, white text), full width of the logo column, rounded,
  upload icon + the short wording "Upload logo", darker blue on hover. The small grey text label above it is hidden (kept only so Developer Mode shows the "?").
- CSS/XML only: no new field, no JS. Version 19.0.1.23.0. Cumulative (021 to 023 included).
- Check on Demo 2: the button looks like the picture of the mock-up; after an upload the file control (download / clear icons) is small and blue; clear it -> the extension logo returns.

## What Update_023 changes on top of Update_022 (owner request 2026-10-30 14:15, field approved 14:3x)
Cumulative (also contains Update_021 and Update_022).
- **Manual company logo**: under the logo box of the Company card a small **UPLOAD LOGO** button lets you pick a picture from your computer.
  When a picture is uploaded it is shown in the logo box; when none, the logo link written by the Chrome extension (`x_image`) is shown exactly as before.
  To go back to the extension's logo, clear the uploaded file (trash icon of the upload control).
- **One new field (approved by the owner)**: `x_yp_logo_upload` (Binary, stored as attachment, `copy=False`). Reason: `x_image` is a Char link and cannot receive an
  uploaded file; no existing crm.lead binary field fits (`x_group_image_binary` belongs to `crm_sync_contact_odoo2`). The extension never writes it,
  and `x_image` stays read-only, so nothing manual is overwritten by "Update" in the extension. Registered in `FIELD_REGISTRY_CRM005.csv`.
- No new JS / asset / API. Needs **Upgrade** (creates the field). Same risk as the other `x_yp_*` fields: if a sync cron copies unknown fields to the SGT main Odoo, check it there.
- Check on Demo 2: Upload Logo -> pick a PNG/JPG -> Save: picture appears in the box; clear it: extension logo returns; Developer Mode: "?" on the upload label.

## What Update_022 changes on top of Update_021 (owner request 2026-10-30 11:03)
Cumulative: also contains Update_021 ("?" labels), which production (19.0.1.19.0) has not installed yet.
- **English | Vietnamese introductions are always visible** - no accordion, no button to press. They sit side by side,
  English on the LEFT and Vietnamese on the RIGHT, in two equal columns (`repeat(2, minmax(0,1fr))`) and the same height
  (grid `stretch`; each text area fills its card, min 11 rem).
- The two boxes are now plain `<div>` cards (were `<details>`); the header is a title (no pointer, no fold caret). Labels keep
  their `<label for>` so the Developer-Mode "?" of Update_021 still works. The Vietnamese box still holds the native Notes
  (`description`) field MOVED by xpath (not copied), still editable.
- Narrow form (< 640 px of form width, e.g. Chatter open or phone): the two cards stack, English first.
- Gallery and Partners boxes are unchanged (still foldable `<details>`).
- No new field, no new JS, no new asset. Version 19.0.1.21.0.
- Check on Demo 2: open a Deal; both boxes are visible, same size, English left; type in each and Save; open Chatter /
  shrink the window: they stack; Developer Mode: "?" still shows on both titles.

## What Update_020 changes on top of Update_019 (owner request 2026-10-27 16:27, go 16:41)
- **Company card is full width** (own row); the Business Type / Main Market / Employee Size row, Business Industries and the new
  Profile Link box are in the left column, **Contact (then Quick Info) in the right column starting level with the Employee Size row**.
- **Profile Link box** (left column, under Business Industries): Link Zalo Group, Link Profile, Group URL, Post URL (2 x 2; one column
  when the form is narrow). These four existing fields are MOVED here (no longer in Detail Fields). The "ID" field (`x_getfly_id`, already
  "VN Odoo ID" in the top block) and the post picture are not in the box. The old base group "Group Post Image" is removed; the post picture
  (`x_group_image_binary`) stays once, in Detail Fields > Zalo Group Post.
- **Partners box** (new, under the Image Gallery box, folds like it): logos of partners / customers (Yellow Pages "Doi tac - Khach hang"),
  same grid as the gallery but logos shown whole on white. Empty: the text **"No partners yet."** (pure CSS, no JS).
- **New field (approved 2026-10-27 16:41)**: `x_yp_partners_html` (Html, read-only in the view, like the gallery). The Chrome extension must write the
  partner logos into it (see HANDOFF in the project); until then every Deal shows "No partners yet.". Version 19.0.1.20.0.
- Check on Demo 2: Company card wide; Contact level with Employee Size; Profile Link fields editable; Partners box empty text; after the
  extension writes images, the logos show and the text disappears; the Upgrade adds the column `x_yp_partners_html`.

## What Update_019 changes on top of Update_018 (owner request 2026-10-27 15:21)
- **Marquee (hover slide of cut-off text) stops when you edit.** Hovering still slides the text. Clicking into a box (or Tab into it)
  now freezes the text exactly where it is: no jump back to the start, the caret lands where you clicked. While a box has the focus
  it never slides again, even if the mouse leaves and comes back or moves over it while typing. After the focus is gone it slides on hover again.
- Before (Update_018): the click reset the text to the start and the next mouse movement over the box started the slide again.
- Only `static/src/js/sgt_marquee.js` changes (the same single approved script, still no import/export/RPC). Version 19.0.1.18.0.
- Check on Demo 2: hover a long Address/Email, click into it and type; move the mouse in and out while typing; click another box.

## What Update_018 changes on top of Update_017 (owner request 2026-10-27 08:26, approved 08:48 after the mock-up)
- **Outer frame**: the white form sheet gets the same card look as the inner boxes (1 px border, 4 px brand-blue top edge,
  rounded corners, soft shadow). Scoped with `:has(.sgt_yp_group)` to the Deal form that carries the profile card.
- **English | Vietnamese side by side**: English on the LEFT, Vietnamese on the RIGHT (`div.sgt_yp_pair`). English is open by
  default, Vietnamese is folded into a narrow vertical strip; clicking a strip opens that box and folds the other one.
  Both `<details>` share `name="sgt_crm005_intro_pair"` (native exclusive accordion) + CSS `:has()` grid. **No JavaScript.**
- Narrow form (Chatter open / phone, < 640 px of form width): the two boxes stack and the folded one is a normal header bar.
- No new field, no new JS. Version 19.0.1.17.0.
- Check on Demo 2: default state (English open, Vietnamese strip); click each strip; edit/paste in English then Save;
  Vietnamese (Notes) still editable after opening; Chrome/Edge >= 120 (older browsers may keep both boxes open, harmless).

## What Update_013 changes on top of Update_012 (owner request 2026-10-26)

- **Hover text slide**: when the mouse rests on a text that is wider than its box, the text slides slowly to
  the left until its last characters show, pauses, slides back and repeats until the mouse leaves.
  Applies to the Yellow Pages profile card (company name, address, e-mail, website, referred by ...) and,
  with the Kanban card v3 (`SGT_kanban_card_compact_ARCH_v3.xml`), to the lines of the Kanban card.
- Implemented by ONE small plain script `static/src/js/sgt_marquee.js` (about 100 lines): no RPC, no data
  access, no model/field; it only changes the horizontal scroll position of the hovered element, and only inside
  elements carrying the class `sgt_marq`. Errors are swallowed (worst case a text does not move).
  Speed 40 px/s, 0.35 s delay, 0.7 s pause at each end. Stops on click, drag, focus or when the mouse leaves.
  Disabled when the browser asks for reduced motion.
- To switch it off without removing the addon: remove the line of `sgt_marquee.js` in `__manifest__.py` and upgrade.

## What Update_016 changes on top of Update_015 (owner request 2026-10-26 16:29, approved 16:30)

- **New box "Company Introduction (English)"** right under the Vietnamese introduction (Notes tab / Company
  Introduction), above the Image Gallery box. The owner pastes the English text here instead of separating it
  from the Vietnamese text with a `-----` line inside Notes. Normal Odoo HTML editor, so bold, italic and lists
  are kept when pasting.
- **Fold buttons**: both boxes (English introduction and Image Gallery) are `<details>`, open by default; click the
  title to fold or unfold. Detail Fields already worked this way. Notes is a native tab, so it cannot fold.
- **One new field (approved)**: `x_yp_intro_en` (Html, "Company Introduction (English)"). Existing fields were
  rejected: `x_notes` / `x_addnotes` are plain text (formatting lost) and carry legacy HubSpot data.
  The field does not exist on the main SGT database: if the sync cron copies unknown fields it may complain,
  same as for the other `x_yp_*` fields.
- The Vietnamese Notes content and the old `-----` separator in existing Deals are NOT touched.
- Order on the form: top block, profile card, tabs (Company Introduction, History stage change),
  English introduction box, Image Gallery box, Detail Fields, Sync blocks.

## What Update_015 changes on top of Update_014 (bug report 2026-10-26 15:32, deal 2403 on production)

- **Symptom**: wheel scrolling got stuck when the pointer was over the gallery, then the whole page scroll failed,
  and Save raised an error.
- **Cause (measured on deal 2403: 41 pictures, 2.1 MB of HTML)**: in Update_014 the gallery field was an editable Html
  field outside the tabs, so the Odoo HTML editor was mounted for every Deal (before, the hidden tab never mounted it):
  heavy page, the picture toolbar (including delete) popped up on hover, the form could become dirty and Save then had
  to send the whole 2 MB. The box also had its own scrollbar (max-height 34rem), which traps the mouse wheel.
- **Fix**: the gallery field is `readonly="1"` (shown by the light read-only viewer, no editor, never sent on Save);
  the box has no scrollbar of its own, all pictures flow in the page; the box is a `<details>` (open by default) so the
  whole gallery can be folded to reach Detail Fields; off-screen tiles use `content-visibility: auto`.
- Pictures are written by the Chrome extension, so no manual editing in Odoo is lost. To edit the raw HTML use
  Settings > Technical (developer mode) or the extension.

## What Update_014 changes on top of Update_013 (owner request 2026-10-26 12:53, boss's request)

- **Products & Services tab removed**: its content is already in Notes (Company Introduction). Field
  `x_product_details` and its data are untouched; it stays in Detail Fields > Product / Industry.
- **Image Gallery is no longer a tab**: it is a box of its own, directly under the tabs (Company Introduction,
  History stage change) and above Detail Fields, so images are visible without clicking. Same field
  `x_yp_gallery_html` (no new field).
- Look follows the Yellow Pages gallery: each picture is a bordered tile, the caption sits under the picture.
  Box is about two rows high (about 10 pictures at 5 columns); more pictures scroll inside the box.
- **Captions**: shown when the extension writes `<figure><img ...><figcaption>Caption</figcaption></figure>`
  (extension change, separate package). Older Deals (plain `<p><img></p>`) keep the plain even grid, no caption.
  CSS cannot print an image `alt` as a caption, and no JS was added.
- To verify on Demo 2: the Html sanitizer keeps `figure` / `figcaption` (if it strips them, captions will not show).
- No new field, model, JS, cron or API. Upgrade from Update_013 only reloads the view and CSS; the old tab
  records disappear with the view.

## What Update_012 changes on top of Update_011 (owner request 2026-10-26, matches the Chrome extension Update_008)

- **Image Gallery**: pictures are laid out as an even grid of equal 4:3 tiles (auto columns, min 200px)
  instead of one narrow column. Works whatever wrapper the Html editor puts around each picture
  (`p`, `div`, `span`, `a`) and ignores stray `<br>`. CSS only.
- **Business Industries** card: field `x_fb_industry` is shown with the multiline text widget, so the full
  list written by the extension (separated by `; `) wraps instead of being cut on one line. Same field, no data change.
- **Company Introduction (Notes)**: the rule (`<hr>`) that separates the Vietnamese notes from the English
  version is drawn as a clear blue line; section headings (`h3`) are styled. CSS only.
- No new field, model, JS, cron or API. Upgrade from Update_011 only reloads views and CSS.
- The Kanban card (contact person under the company name) is NOT part of this addon: it is the child view
  "SGT - Kanban card compact" (file `SGT_kanban_card_compact_ARCH_v2.xml`).

## What Update_011 changes on top of Update_010 (owner request 2026-10-25)

- **VN Odoo ID** now sits in the top block, left column, right under **Source** (Opportunity);
  on a Lead (which has no Source row) it is the last row of the left group.
  **Deal ID** sits right under **Address** (right column, Lead and Opportunity). The
  "Deal Identifiers" group is removed from Detail Fields (both fields are still in Detail Fields
  under Marketing / Source and Deal Key / Pipeline). No new field.
- **Colours**: the Yellow Pages yellow is replaced by the Xinyang brand colours of UI-004:
  blue `#0061BD` (card top border, icons, active tab, Detail Fields icon) and red `#E51922`
  (small accent: section kicker, Zalo badge). They read `--o-xinyang-brand-blue/-red` and fall back
  to the same hex values when UI-004 is not installed.

## What Update_010 does

1. Replaces the Deal form **from "Customer Info" downward** with a Yellow Pages style profile:
   company card (logo, name, address), three information cards (Business Type, Main Market,
   Employee Size), Business Industries card, right column "Contact" (Hotline/Zalo, Email,
   Website, Contact person) and "Quick Info" (Tax Code, Founded Year, Referred By).
   The block **above** Customer Info (Expected Revenue, Contact, Email, Phone, Source,
   Salesperson, Expected Closing, Tags, Address) is unchanged.
2. Tabs under the profile: **Company Introduction** (the native Notes tab, field `description`),
   *History stage change* (third-party tab, untouched). (Update_014: the Products & Services and Image Gallery tabs are gone; the gallery is a box under the tabs.)
   The old "Contacts" tab is hidden; its fields are in Detail Fields.
3. **Detail Fields** button (closed `<details>`) below the tabs and above the existing
   Sync / Contact Sync blocks. It holds EVERYTHING that used to be in the old "Deal Import
   Fields" tab and the old Customer Info / Group Post Image blocks (no field removed).
4. Removes the CRM-005 child models (product, project, media) and 14 `x_yp_*` fields of Update_009.

## Field policy (decided by the owner)

Use fields that already exist in Xinyang (and so exist on both sides of the SGT sync) whenever possible.
A new field is created only when the 2026-10-11 production Scan (191 `crm.lead` fields) has nothing able to hold the data.

### Existing fields re-used (nothing new)
| Yellow Pages information | Field | Note |
|---|---|---|
| Logo | `x_image` (char) | displayed with widget `image_url`; value must be a URL or `data:image/...;base64,...`; editable in Detail Fields > Images / Files |
| Hotline = Zalo number | `x_phone` | also the "Sync Phone" sent to Odoo2 by Create Contact |
| Company introduction | `description` (Notes) | whole Notes content = company info |
| Yellow Pages link | `referred` | native label "Referred By" kept (several sources later) |
| Products and services | `x_product_details` | plain text; start each item with a code like `[SP01]` |
| Business type | `x_type_contact` | |
| Business industries | `x_fb_industry` | |
| Main market | `x_country` | text field, not `country_id` |
| Address | `street`, `street2`, `city` | |
| Email / Website / Contact / Position | `email_from`, `website`, `contact_name`, `function` | |

### New fields (4) and why
| Field | Type | Reason (no existing field can hold it) |
|---|---|---|
| `x_yp_tax_code` | Char | no tax-code field on `crm.lead`; `res.partner.vat` exists only on the Contact |
| `x_yp_founded_year` | Integer | no founding year; `x_createdate` is the HubSpot deal creation date |
| `x_yp_employee_range` | Char | no staff-size field |
| `x_yp_gallery_html` | Html | each existing image field holds one image; the only Html field (Notes) holds the introduction |
| `x_yp_partners_html` | Html | (Update_020) partner / customer logos; `x_yp_gallery_html` mixes every picture of the listing and cannot be split without JS |
| `x_yp_intro_en` | Html | (Update_016) English introduction; `description` is the Vietnamese one, `x_notes`/`x_addnotes` are plain text with legacy data |

Dropped by the owner: main customers, project list, Yellow Pages listing ID.
Product ↔ image link: the same code `[SP01]` in `x_product_details` and in the caption/alt of the image.
No JavaScript, controller, cron, automation or external call is added.

## Install / upgrade (Demo 2)
1. Backup the database. **Upgrade drops** the old tables `sgt_crm005_product/project/media` and the 14 old
   `x_yp_*` columns of Update_009 (test data on Demo 2 only). Production never had them.
2. Replace the `sgt_crm_yellowpages_profile` folder, restart Odoo, Apps > Update Apps List,
   open the app, press Upgrade (installed version 19.0.1.7.0/1.8.0 -> 19.0.1.10.0).
3. Hard-refresh the browser (Ctrl+F5) because CSS assets changed.
4. Check the Odoo log: expected lines `CRM-005 ... Import-hide View` and, if it existed,
   `removing obsolete Contact Sync relocation view`. Lines `Could not delete id ... sgt.crm005`
   would mean a leftover relation: send the log, nothing is broken for the form.

## Acceptance checklist
- [ ] Deal form: top block unchanged; Source under Phone; Address under Tags.
- [ ] New profile card shows company name, address; logo box (dashed) when `x_image` is empty.
- [ ] Hotline shows `x_phone`; Email/Website/Contact editable; Tax Code, Founded Year (no thousand separator), Referred By (link).
- [ ] Notes tab is named "Company Introduction" and shows `description`.
- [ ] Image Gallery box (under the tabs, above Detail Fields): pictures in an even grid, caption under each picture when it has one, about two rows high then scrolls. No Products & Services tab.
- [ ] Detail Fields closed by default; opening shows all legacy import groups, Group Post Image, Marketing & Ownership.
- [ ] Order at the bottom: Detail Fields -> Sync -> Contact Sync. Old "Deal Import Fields" tab not shown.
- [ ] "Create Contact" button still in the header and still syncs.
- [ ] Narrow window: the right column goes below the company card.
- [ ] Second Upgrade of the module keeps the Import tab hidden (View External ID has noupdate = True).

## Known limits / things to check on Demo 2 (offline tests cannot prove them)
- `image_url` widget: raw base64 without the `data:image/...;base64,` prefix shows the Odoo placeholder.
- Founded Year uses `options="{'enable_formatting': false}"`; if ignored, Odoo shows 2,010.
- Gallery layout is pure CSS on the Html field (`display: grid`); the Odoo HTML editor may wrap images in extra tags.
  The HTML field keeps Odoo's default sanitizer: inline base64 images are accepted.
- Hotline in `x_phone`: Create Contact will send the hotline to Odoo2 (owner's choice). If an import/automation
  copies `phone` into `x_phone`, the hotline would be overwritten: not verifiable from the Scan.
- Scan (production) and Demo 2 differ for Contact Sync: Demo 2 shows "Contact Sync" at the bottom of the form;
  production (Scan view 1903) adds "Sync Contact Odoo2" inside the top group. Update_010 does not relocate it any more.
- Old Zalo chat text already stored in `description` of existing deals is NOT modified or deleted.
- Nothing is verified against the SGT main database (its field list is not available): check that `x_image`,
  `x_phone`, `x_type_contact`, `x_fb_industry`, `x_country`, `x_product_details` and the 4 new fields behave as wanted on the target.

## Rollback
Reinstall the Update_009 folder + Upgrade (the 4 new fields are dropped; Update_009's children come back empty).

## History
Update_007 hide Import tab (noupdate fix) · Update_008 Source/Address top block · Update_009 Address for Opportunities ·
Update_010 Yellow Pages layout, Detail Fields, 4 new fields, child models removed · **Update_011 VN Odoo ID / Deal ID moved under Source / Address, brand blue + red.**

## Update_021 (19.0.1.20.0) — "?" in Developer Mode on every CRM-005 field
Developer Mode shows the "?" (technical tooltip: Label / Field / Model / Type / Widget) only on real Odoo form labels. The card labels of this layout were plain text, so they had none. Now each is a `<label for="crm005_<field>" string="…"/>` (explicit `id` on the field): Business Type, Main Market, Employee Size, Business Industries, Profile Link rows (4), Contact rows (5), Quick Info rows (3), Company, the box titles (English introduction, Vietnamese introduction = Notes, Image Gallery, Partners). Fields without visible text (street, street 2, city, logo) get an empty label that exists only to carry the "?" (hidden outside Developer Mode, CSS `:has(sup)`). Normal mode looks as before. No new field, JS or API.
