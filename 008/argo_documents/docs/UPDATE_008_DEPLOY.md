# Documents-008 Update_008: deployment, verification, rollback

1. BACK UP PostgreSQL DB and the exact installed Documents-008 Update_007 files. Use staging.
2. Deploy `argo_documents`, restart Odoo, Upgrade module (`-u argo_documents -d xinyang` in a maintenance window or UI Upgrade). Odoo should run `upgrades/19.0.1.8.0/post-10-configure-company-crm-root.py`; this aligns the legacy parameter without touching old folders.
3. Check `env.ref('argo_documents.folder_crm_information_root')` exists with parent=False, is_locked=True, system_root=True, crm_shared_root=True, access_mode='public', public_level='view'.
4. Confirm Explorer sidebar two top roots Company Information (virtual, old data) and CRM Information (system folder). Existing `CRM_Infor`/`XINYANG_Infor` remain under Company.
5. Verify User A and B have Documents User implied from base.group_user; A cannot see B's private tax folder; manager can see all. Test direct RPC and `/argo_documents/download` and `/argo_documents/upload`; View cannot upload/delete; Edit cannot delete.
6. Try to archive, delete, trash, permanently delete or unlock CRM Information using ADMIN account and direct ORM; all must fail. Check other folders still support Admin lock/unlock.
7. Deploy CRM-005 Update_043 second. Test Deal with tax code: Create Folder creates/links under CRM Information, drag/drop file then verify same file in Discuss Documents. Test existing linked older Deal (must remain readable without moving files).
8. If older configured CRM_Infor was set Public View and locked, do NOT delete it. Review and archive only after inventory of linked folders and permissions.
9. Rollback both module code and database snapshot together if any migration/permission operation fails; do not revert only code after schema upgrade.

Caveats: Existing folder data is preserved. This update has NOT been verified on a live Odoo server. Real record rules, group implications and OWL explorer require staging sign-off.
