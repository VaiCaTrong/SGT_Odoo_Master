# Documents-008 Update_008 — Company Information + CRM Information

- Explorer virtual, nondeletable root is now **Company Information**. Existing root-level folders (such as `CRM_Infor` and `XINYANG_Infor`) remain untouched.
- New sibling root **CRM Information** is an actual `argo.document.folder` created by module XML data (`folder_crm_information_root`), made Public/View for internal accounts, flagged system_root and locked permanently. It cannot be renamed, moved, archived, deleted, or unlocked, including via ORM/RPC.
- CRM-005 resolves this CRM root by its stable XML ID, no longer by an ID manually chosen in Settings.
- Upgrade post-migration preserves older `crm_shared_root` flags: legacy children depend on them for privacy. It updates only the old config parameter as compatibility metadata. It does NOT move/delete folders or documents, remove sharing, change `create_uid`, or rewrite Deal links. CRM-005 continues to display previously linked documents in their legacy folders subject to existing access rights.
- Internal Odoo users (`base.group_user`) automatically imply Documents User. **Private folder access is still checked by record rules.** Removal of reverse group implication prevents recursion. Documents Admin keeps its overrides.
- Company Information and CRM Information have separate explorer sidebar roots, search scope, and tree navigation.
- Retain user/department/public View/Edit/Full on child folders, tax-code creation, shared-MST model and drag/drop uploads.

## Testing
Python/JS/XML static + Odoo-free simulated access tests only. NO server upgrade, live record-rule test or E2E user testing performed here. See `docs/UPDATE_008_DEPLOY.md`.
