# CRM-005 Update_063 — No-Source footer: lift links to the left (14/11/2026)

## Based on
Complete CRM-005 Update_062 provided by the user. Manifest upgraded from
`19.0.1.61.0` to `19.0.1.62.0`. Does not add database fields or migrations.

## Fixed behavior
- Source present: Source left and native notification bell/Salesperson right on
  the first line; links on the second line, left-aligned.
- Source absent: links automatically occupy the first line on the **left**;
  native notification bell/Salesperson remain on the **right**, at the same height.
- No usable links and Documents not permitted: shortcuts container fully collapses,
  leaving no empty extra row or gap. Invalid URLs remain hidden.
- Links wrap within the available left space on narrow screens.

## Technical scope
- `views/crm_yp_lead_kanban.xml`: change the existing quick-links insertion
  from `position="after"` to `position="inside"` the same native Kanban footer.
  Preserve all other 6 XPath operations and all original native footer elements.
- `static/src/css/kanban_safe_links.css`: use footer `flex-wrap`, natural Source
  sibling selection, scoped visible-content hiding; no JS reparenting.
- `__manifest__.py`: bump to `19.0.1.62.0` to cause a normal upgrade.
- Current regression tests updated to reflect the new footer placement.
- All business models, JS, permissions, other views and functions unchanged.

## Deployment
1. Back up Odoo database `xinyang` and the current addon folder.
2. Replace the entire `sgt_crm_yellowpages_profile` folder with this package.
3. Restart Odoo, Upgrade the CRM-005 addon, clear/rebuild assets and hard refresh
   the CRM Pipeline in a browser (Ctrl+Shift+R).
4. Check an opportunity **with** Source and one **without** Source, with 1 and
   multiple links, and one without any usable link; verify native right widgets.
5. Regression-check palette, New, drag/drop, ordinary and Ctrl/Cmd+Click,
   Documents permissions, Website/Facebook/Zalo/Trang Vang, map, gallery.

Offline validation: 161 Python unittest cases executed, 124 passed and 37 skipped;
no failures. Chromium synthetic footer layout validated four cases: Source
present, Source absent with 2 links, Source absent with 0 usable links, Source
absent with 8 links wrapping on multiple lines. All expected alignment and
visibility assertions passed. This is not equivalent to a live Odoo staging
upgrade. Stage first where possible; if the view differs from this addon
baseline, restore Update_062 and upgrade without uninstalling.
