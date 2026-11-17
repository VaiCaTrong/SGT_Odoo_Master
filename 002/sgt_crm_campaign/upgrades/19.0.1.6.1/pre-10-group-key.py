"""Update_008 PRE (runs on upgrade from < 19.0.1.6.1):

1. Drop the stale selection rows of ``sgt.crm002.funnel.code``.
   ``code`` was a Selection and is now a Char.  Without this, the end of the
   module load unlinks those rows and Odoo crashes with
   ``AttributeError: 'Char' object has no attribute 'ondelete'``.
2. Add ``group_key`` BEFORE the data files load.  The funnel data records are
   ``noupdate``, so fix the existing rows here: code ``mm`` -> Match Making,
   the rest -> Data Funnel.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("SELECT to_regclass('sgt_crm002_funnel')")
    if not cr.fetchone()[0]:
        return
    # 1. stale selection values of the field that is no longer a Selection
    cr.execute("""
        SELECT s.id
          FROM ir_model_fields_selection s
          JOIN ir_model_fields f ON f.id = s.field_id
         WHERE f.model = 'sgt.crm002.funnel' AND f.name = 'code'
    """)
    selection_ids = [row[0] for row in cr.fetchall()]
    if selection_ids:
        cr.execute("""DELETE FROM ir_model_data
                       WHERE model = 'ir.model.fields.selection' AND res_id = ANY(%s)""", (selection_ids,))
        cr.execute("DELETE FROM ir_model_fields_selection WHERE id = ANY(%s)", (selection_ids,))
    cr.execute("""UPDATE ir_model_fields SET ttype = 'char'
                   WHERE model = 'sgt.crm002.funnel' AND name = 'code' AND ttype = 'selection'""")
    _logger.info('CRM-002 Update_008: removed %s stale selection rows of funnel.code.', len(selection_ids))
    # 2. group_key
    cr.execute("ALTER TABLE sgt_crm002_funnel ADD COLUMN IF NOT EXISTS group_key varchar")
    cr.execute("""
        UPDATE sgt_crm002_funnel
           SET group_key = CASE WHEN code = 'mm' THEN 'mm' ELSE 'data' END
         WHERE group_key IS NULL
    """)
    _logger.info('CRM-002 Update_008: group_key filled for %s funnels.', cr.rowcount)
