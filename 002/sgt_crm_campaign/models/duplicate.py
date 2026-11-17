"""Update_026: system-wide Deal duplicate check for the Chrome extension (5 public RPC functions).
(Update_027: every function also needs the Sales right "User: Own Documents Only" or higher.)

    yp_duplicate_check(phone_keys, tax_code)           read-only look at EVERY Deal (all funnels, Lost, archived)
    yp_duplicate_scan(options)                         Admin only, read-only: groups of duplicate Deals in the CRM
    yp_create_lead(vals, phone_keys, tax_code, force)  check + create in one locked step
    yp_read_lead(lead_id, field_names)                 read a Deal the caller may update
    yp_update_lead(lead_id, vals)                      write a Deal the caller may update

INTENTIONAL, NARROW EXCEPTION to "core crm.lead is never sudo-read here": a normal salesperson
cannot see Deals of other funnels/owners (record rules), which is exactly why the extension used to
create "X_1" copies.  These functions therefore search with sudo(), but

  * the answer is a minimal list (name, company, owner, funnel/step/stage, state) - never phone,
    e-mail or notes;
  * yp_duplicate_scan is for Administrators only (checked first, before any sudo query) and writes nothing;
  * read/update is allowed per Deal only to Admin, the "Kinh doanh (MMC)" department (and its
    sub-departments) or the Deal's own Salesperson, checked here on the server;
  * only the fixed white lists in yp_utils.py can be read or written;
  * sudo() keeps env.uid, so write_uid and Chatter still name the real person;
  * creation runs with the employee's own rights (no sudo) so funnel permissions and the CRM-002
    create hook behave as when the Deal is created by hand.

Nothing here changes a record rule or an existing function.
"""
import logging
import math
import time
from bisect import bisect_right
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from psycopg2 import IntegrityError
from psycopg2.errors import LockNotAvailable

from . import yp_utils as U

_logger = logging.getLogger(__name__)


class Crm002Duplicate(models.AbstractModel):
    _inherit = 'sgt.crm002.service'

    # ------------------------------------------------------------------ small helpers
    @staticmethod
    def _yp_error(code, message='', **extra):
        res = {'ok': False, 'code': code}
        if message:
            res['message'] = message
        res.update(extra)
        return res

    def _yp_internal_only(self):
        """Update_027: only accounts with the Sales right "User: Own Documents Only" or higher.

        "User: All Documents" and Sales "Administrator" include it (and so the internal-user group).  The
        Role Administrator alone does NOT carry any Sales group, so it is refused here as well; an abstract
        model has no ACL of its own, this is the gate."""
        if self.env.user.has_group(U.SALES_USER_GROUP):
            return None
        return self._yp_error('forbidden', 'Cần quyền Sales (User: Own Documents Only trở lên) để dùng chức năng này.')

    def _yp_roles(self):
        """(is_admin, is_sales). is_sales = current department is Kinh doanh (MMC) or below it."""
        admin = self._is_admin()
        if admin:
            return True, False
        return False, self._yp_is_sales()

    def _yp_is_sales(self):
        user_depts = self._user_department_ids()
        if not user_depts:
            return False
        Dept = self.env['hr.department'].sudo()
        roots = Dept.search([('name', '=', U.SALES_DEPARTMENT_NAME)])
        if not roots:
            return False
        return bool(user_depts & set(Dept.search([('id', 'child_of', roots.ids)]).ids))

    def _yp_lead_model(self, env=None):
        return (env or self.env)['crm.lead'].sudo().with_context(active_test=False)

    def _yp_access(self, lead_id):
        """(lead, error): a Deal this caller may read/update, decided on the server per Deal."""
        refused = self._yp_internal_only()
        if refused:
            return None, refused
        if not isinstance(lead_id, int) or isinstance(lead_id, bool) or lead_id <= 0:
            return None, self._yp_error('invalid', 'lead_id không hợp lệ.')
        admin, sales = self._yp_roles()
        Lead = self._yp_lead_model()
        if admin or sales:
            lead = Lead.browse(lead_id).exists()
            if not lead:
                return None, self._yp_error('not_found', 'Không tìm thấy Deal.')
            return lead, None
        # Anyone else: only the Deal they own. A missing id answers the same as a foreign one,
        # so the answer never tells which ids exist.
        lead = Lead.search([('id', '=', lead_id), ('user_id', '=', self.env.uid)], limit=1)
        if not lead:
            return None, self._yp_error('forbidden', 'Bạn không có quyền với Deal này.')
        return lead, None

    # ------------------------------------------------------------------ finding duplicates
    def _yp_candidate_ids(self, env, keys, taxes):
        """Cheap database pre-filter. Never misses a real match; Python decides afterwards.

        A key (last 9 digits) is looked for as its 9 digits in order, with only the separators the
        Python matcher also accepts between them (space . ( ) -; in HTML fields also &nbsp; and tags).
        So "0912 345 678", "+84.912.345.678" and "(091) 234-5678" all hit the key 912345678.
        One regex per column instead of stripping every non-digit: about 30 times faster on long notes.
        """
        Lead = env['crm.lead']
        columns = Lead._fields
        clauses, params = [], []
        for name in U.PHONE_FIELDS if keys else ():
            f = columns.get(name)
            if f is None or not f.store or f.translate or f.type not in ('char', 'text', 'html'):
                continue
            html = name in U.HTML_FIELDS
            clauses.append('"%s" %s %%s' % (name, '~*' if html else '~'))
            params.append(U.key_regex(keys, html))
        tax_field = columns.get(U.TAX_FIELD)
        if taxes and tax_field is not None and tax_field.store and not tax_field.translate:
            clauses.append('UPPER(regexp_replace(COALESCE("%s", \'\'), \'[^0-9A-Za-z]\', \'\', \'g\')) = ANY(%%s)'
                           % U.TAX_FIELD)
            params.append(list(taxes))
        if not clauses:
            return []
        env.cr.execute('SELECT id FROM "%s" WHERE %s' % (Lead._table, ' OR '.join(clauses)), params)
        return [row[0] for row in env.cr.fetchall()]

    def _yp_sequences(self, env):
        """Column order numbers and the "Mark Lost"-like stages, from the three tiny stage/funnel tables.

        Returns ({'stage': {id: sequence}, 'funnel': {...}, 'sale_stage': {...}}, {lost stage ids})."""
        def read_all(model, names):
            return env[model].sudo().with_context(active_test=False).search([]).read(names)

        stages = read_all('crm.stage', ['id', 'sequence', 'name'])
        seqs = {
            'stage': {r['id']: r['sequence'] for r in stages},
            'funnel': {r['id']: r['sequence'] for r in read_all('sgt.crm002.funnel', ['id', 'sequence'])},
            'sale_stage': {r['id']: r['sequence'] for r in read_all('sgt.crm002.funnel.stage', ['id', 'sequence'])},
        }
        return seqs, {r['id'] for r in stages if U.stage_is_lost(r.get('name'))}

    def _yp_find_matches(self, env, keys, taxes, is_admin, is_sales):
        """Every Deal sharing a phone key or tax code, furthest first.

        Returns (matches cut to MAX_MATCHES, truncated, total).  The cut happens AFTER sorting, so a hotline
        shared by 120 Deals still shows the 50 furthest ones."""
        ids = self._yp_candidate_ids(env, keys, taxes)
        if not ids:
            return [], False, 0
        Lead = self._yp_lead_model(env)
        columns = Lead._fields
        phone_fields = [n for n in U.PHONE_FIELDS if n in columns]
        company_field = 'x_company' if 'x_company' in columns else ''
        wanted = ['id', 'name', 'active', 'user_id', 'partner_name', 'lost_reason_id', 'probability',
                  'stage_id', 'sgt_crm002_funnel_id', 'sgt_crm002_step', 'sgt_crm002_sale_funnel_id',
                  'sgt_crm002_sale_stage_id', company_field, U.TAX_FIELD] + phone_fields
        names = []
        for n in wanted:
            if n and n in columns and n not in names:
                names.append(n)
        seqs, lost_stage_ids = self._yp_sequences(env)
        keyset, taxset = set(keys), set(taxes)
        matches = []
        for row in Lead.browse(ids).read(names):
            phone_hit = False
            for n in phone_fields:
                if keyset.intersection(U.phone_keys_in_text(row.get(n), html=n in U.HTML_FIELDS)):
                    phone_hit = True
                    break
            tax_hit = bool(taxset) and U.tax_key(row.get(U.TAX_FIELD)) in taxset
            if phone_hit or tax_hit:
                matches.append(U.build_match(row, phone_hit, tax_hit, is_admin, is_sales,
                                             env.uid, company_field, seqs, lost_stage_ids))
        matches.sort(key=U.sort_key)
        total = len(matches)
        return matches[:U.MAX_MATCHES], total > U.MAX_MATCHES, total

    def _yp_duplicate_answer(self, matches, truncated, total, is_admin, is_sales):
        return {'ok': True, 'is_admin': is_admin, 'is_sales': is_sales,
                'can_update': any(m['can_update'] for m in matches),
                'truncated': truncated, 'total': total, 'matches': matches}

    # ------------------------------------------------------------------ scanning the whole CRM (Admin)
    SCAN_PAGE = 1000          # Deals read per query: memory stays small however big the CRM grows

    @staticmethod
    def _yp_stored_text(field):
        return field is not None and field.store and not field.translate and field.type in ('char', 'text', 'html')

    def _yp_scan_read_keys(self, env, lost_stage_ids):
        """Read every Deal ONCE (raw SQL, all funnels, Lost and archived included) and join the Deals
        that share a phone key or tax code.  Returns (graph, meta, active_ids):
          graph      KeyGraph of the Deals that carry at least one key
          meta       {id: (active, lost_reason, probability, stage, step, sale_funnel, sale_stage)}
          active_ids ascending ids of the Deals that count as active (the scan "seeds")."""
        Lead = env['crm.lead']
        columns = Lead._fields
        phone = [n for n in U.PHONE_FIELDS if self._yp_stored_text(columns.get(n))]
        tax = U.TAX_FIELD if self._yp_stored_text(columns.get(U.TAX_FIELD)) else ''
        meta_cols = [n for n in U.SCAN_META_FIELDS if n in columns and columns[n].store]
        cols = ['id'] + meta_cols + phone + ([tax] if tax else [])
        sql = ('/* yp_scan */ SELECT %s FROM "%s" WHERE "id" > %%s ORDER BY "id" LIMIT %%s'
               % (', '.join('"%s"' % c for c in cols), Lead._table))
        at = {n: i for i, n in enumerate(cols)}
        graph, meta, active_ids = U.KeyGraph(), {}, []
        last = 0
        while True:
            env.cr.execute(sql, [last, self.SCAN_PAGE])
            rows = env.cr.fetchall()
            for row in rows:
                lead_id = row[0]
                stage = row[at['stage_id']] if 'stage_id' in at else None
                active = bool(row[at['active']]) if 'active' in at else True
                if active and not (stage and stage in lost_stage_ids):
                    active_ids.append(lead_id)
                pkeys = []
                for n in phone:
                    pkeys.extend(U.phone_keys_in_text(row[at[n]], html=n in U.HTML_FIELDS))
                graph.add(lead_id, pkeys, U.tax_key(row[at[tax]]) if tax else '')
                if lead_id in graph.keys:
                    meta[lead_id] = tuple(row[at[n]] if n in at else None for n in U.SCAN_META_FIELDS)
            if len(rows) < self.SCAN_PAGE:
                return graph, meta, active_ids
            last = rows[-1][0]

    def _yp_scan_groups(self, env, after_id, limit):
        """The scan itself.  Returns the answer dict (without ok/is_admin/max_batch)."""
        seqs, lost_stage_ids = self._yp_sequences(env)
        graph, meta, active_ids = self._yp_scan_read_keys(env, lost_stage_ids)
        start = bisect_right(active_ids, after_id)
        seeds = active_ids[start:start + limit]
        answer = {'scanned': len(seeds), 'from_id': seeds[0] if seeds else None,
                  'to_id': seeds[-1] if seeds else None, 'next_after_id': None, 'done': True, 'groups': []}
        if not seeds:
            return answer
        to_id = seeds[-1]
        if start + limit < len(active_ids):               # more active Deals are waiting after this batch
            answer['next_after_id'], answer['done'] = to_id, False

        def info(lead_id):
            active, lost_reason, probability, stage, step, sale_funnel, sale_stage = meta[lead_id]
            state = U.lead_state(active, lost_reason, probability, bool(stage) and stage in lost_stage_ids)
            place = U.place_rank(sale_funnel, seqs['funnel'].get(sale_funnel), seqs['sale_stage'].get(sale_stage),
                                 stage, seqs['stage'].get(stage), step)
            return state, place

        picked = []                                        # (owner id, ordered member ids)
        for ids in graph.groups():
            states = {i: info(i) for i in ids}
            active = [i for i in ids if states[i][0] == 'active']
            if not active:
                continue                                   # only Lost/archived Deals: nobody to scan from
            owner = min(active)                            # the group belongs to the batch holding this id
            if after_id < owner <= to_id:
                ordered = sorted(ids, key=lambda i: U.order_key(states[i][0], states[i][1], i))
                picked.append((owner, ordered))
        picked.sort()
        if not picked:
            return answer

        Lead = self._yp_lead_model(env)
        columns = Lead._fields
        company_field = 'x_company' if 'x_company' in columns else ''
        names = [n for n in dict.fromkeys(
            ['id', 'name', 'active', 'user_id', 'partner_name', 'lost_reason_id', 'probability', 'stage_id',
             'sgt_crm002_funnel_id', 'sgt_crm002_step', 'sgt_crm002_sale_funnel_id', 'sgt_crm002_sale_stage_id',
             company_field]) if n and n in columns]
        wanted = sorted({i for _owner, ordered in picked for i in ordered[:U.SCAN_MAX_MEMBERS]})
        rows = {}
        for at in range(0, len(wanted), 500):
            for row in Lead.browse(wanted[at:at + 500]).read(names):
                rows[row['id']] = row
        uid = env.uid
        for _owner, ordered in picked:
            members = []
            for lead_id in ordered[:U.SCAN_MAX_MEMBERS]:
                phone_hit, tax_hit = graph.shares(lead_id)
                members.append(U.build_match(rows[lead_id], phone_hit, tax_hit, True, False, uid,
                                             company_field, seqs, lost_stage_ids))
            answer['groups'].append({'size': len(ordered), 'truncated': len(ordered) > U.SCAN_MAX_MEMBERS,
                                     'members': members})
        return answer

    # ------------------------------------------------------------------ public functions
    @api.model
    def yp_duplicate_check(self, phone_keys, tax_code):
        refused = self._yp_internal_only()
        if refused:
            return refused
        keys, tax, problem = U.clean_inputs(phone_keys, tax_code)
        if problem:
            return self._yp_error('invalid', problem)
        wait = U.CHECK_LIMITER.hit(self.env.uid)
        if wait:
            return self._yp_error('rate_limit', 'Kiểm tra trùng quá nhanh, thử lại sau.', retry_after=wait)
        is_admin, is_sales = self._yp_roles()
        matches, truncated, total = self._yp_find_matches(self.env, keys, [tax] if tax else [], is_admin, is_sales)
        _logger.info('CRM-002 yp_duplicate_check uid=%s keys=%s matches=%s', self.env.uid, len(keys), total)
        return self._yp_duplicate_answer(matches, truncated, total, is_admin, is_sales)

    @api.model
    def yp_duplicate_scan(self, options=None):
        """Admin only, read only: groups of Deals that share a phone number or tax code.

        options: {'probe': bool, 'after_id': int >= 0, 'limit': int}.  probe=True only tells whether the
        caller may use the scan.  Each call scans at most SCAN_MAX_BATCH active Deals ("seeds") in id order;
        call again with after_id = next_after_id until done.  A group is returned by the one batch that holds
        its smallest active Deal id, so no group comes twice and every group has all its members."""
        if not self._is_admin():                      # FIRST, before anything reads data with sudo()
            return self._yp_error('forbidden', 'Chỉ Administrator được quét trùng toàn CRM.')
        refused = self._yp_internal_only()            # Update_027: and the Sales right, like every yp_* function
        if refused:
            return refused
        opts, problem = U.parse_scan_options(options)
        if problem:
            return self._yp_error('invalid', problem)
        uid = self.env.uid
        if opts['probe']:
            wait = U.PROBE_LIMITER.hit(uid)
            if wait:
                return self._yp_error('rate_limit', 'Kiểm tra quyền quá nhanh, thử lại sau.', retry_after=wait)
            return {'ok': True, 'is_admin': True, 'probe': True, 'max_batch': U.SCAN_MAX_BATCH}
        wait = U.SCAN_LIMITER.hit(uid)
        if wait:
            return self._yp_error('rate_limit', 'Quét trùng quá nhiều lần, thử lại sau.', retry_after=wait)
        started = time.monotonic()
        answer = self._yp_scan_groups(self.env, opts['after_id'], opts['limit'])
        _logger.info('CRM-002 yp_duplicate_scan uid=%s after_id=%s scanned=%s groups=%s ms=%s', uid,
                     opts['after_id'], answer['scanned'], len(answer['groups']),
                     int((time.monotonic() - started) * 1000))
        result = {'ok': True, 'is_admin': True, 'max_batch': U.SCAN_MAX_BATCH}
        result.update(answer)
        return result

    @api.model
    def yp_read_lead(self, lead_id, field_names):
        lead, error = self._yp_access(lead_id)
        if error:
            return error
        if (not isinstance(field_names, (list, tuple)) or not field_names or len(field_names) > 80
                or any(not isinstance(n, str) for n in field_names)):
            return self._yp_error('invalid', 'Danh sách field không hợp lệ.')
        bad = sorted(set(n for n in field_names if n not in U.READ_FIELDS))
        if bad:
            return self._yp_error('invalid', 'Field không được phép đọc: %s.' % ', '.join(bad))
        present = [n for n in dict.fromkeys(field_names) if n in lead._fields]
        values = lead.read(present)[0] if present else {'id': lead.id}
        return {'ok': True, 'values': values}

    @api.model
    def yp_update_lead(self, lead_id, vals):
        lead, error = self._yp_access(lead_id)
        if error:
            return error
        problem = U.validate_values(vals, U.WRITE_FIELDS, lead._fields)
        if problem:
            return self._yp_error('invalid', problem)
        try:
            with self.env.cr.savepoint():           # a refused write leaves nothing behind
                lead.write(vals)
        except AccessError as exc:
            return self._yp_error('forbidden', str(exc))
        except (UserError, ValidationError) as exc:
            return self._yp_error('invalid', str(exc))
        _logger.info('CRM-002 yp_update_lead uid=%s lead=%s fields=%s', self.env.uid, lead.id, len(vals))
        return {'ok': True, 'id': lead.id}

    def _yp_create_wait(self, is_admin):
        """0 when the caller may create now, else seconds to wait (DB based, shared by all processes)."""
        limit = U.CREATE_LIMIT_ADMIN if is_admin else U.CREATE_LIMIT_USER
        now = fields.Datetime.now()
        recent = self._yp_lead_model().search(
            [('create_uid', '=', self.env.uid),
             ('create_date', '>=', now - timedelta(seconds=U.WINDOW_SECONDS))],
            order='create_date desc', limit=limit)
        if len(recent) < limit:
            return 0
        oldest = recent[limit - 1].create_date
        return max(1, int(math.ceil(U.WINDOW_SECONDS - (now - oldest).total_seconds())))

    @api.model
    def yp_create_lead(self, vals, phone_keys, tax_code, force_duplicate=False):
        refused = self._yp_internal_only()
        if refused:
            return refused
        problem = U.validate_values(vals, U.WRITE_FIELDS + U.CREATE_EXTRA_FIELDS, self.env['crm.lead']._fields)
        if problem:
            return self._yp_error('invalid', problem)
        keys, tax, problem = U.clean_inputs(phone_keys, tax_code, require_one=False)
        if problem:
            return self._yp_error('invalid', problem)
        own_keys, own_tax = U.keys_from_values(vals)       # the server also checks what the Deal really contains
        keys = list(dict.fromkeys(keys + own_keys))
        taxes = [t for t in dict.fromkeys([tax, own_tax]) if t]
        if not keys and not taxes:
            return self._yp_error('invalid', 'Cần ít nhất một số điện thoại hoặc mã số thuế hợp lệ.')
        if len(keys) > U.MAX_KEYS_TOTAL:
            return self._yp_error('invalid', 'Quá nhiều số điện thoại trong một Deal.')
        is_admin, is_sales = self._yp_roles()
        wait = self._yp_create_wait(is_admin)
        if wait:
            return self._yp_error('rate_limit', 'Tạo Deal quá nhanh, thử lại sau.', retry_after=wait)
        allow_duplicate = bool(is_admin and force_duplicate is True)   # only an Admin, only when asked
        registry = self.env.registry
        uid, context = self.env.uid, dict(self.env.context)
        try:
            # Odoo's own transaction is REPEATABLE READ: it fixed its snapshot before the lock was
            # granted, so it would not see a Deal that the previous holder has just committed.
            # Hence TWO fresh cursors: one only holds the advisory locks, the other (opened AFTER the
            # locks are granted, so its snapshot is new) searches and creates.  The work cursor
            # commits first, the lock cursor releases the locks last.
            with registry.cursor() as lock_cr:
                lock_cr.execute("SET LOCAL lock_timeout = '%s'" % U.LOCK_TIMEOUT)
                for name in U.lock_keys(keys, taxes):
                    lock_cr.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))', [name])
                with registry.cursor() as work_cr:
                    env_w = api.Environment(work_cr, uid, context)
                    matches, truncated, total = self._yp_find_matches(env_w, keys, taxes, is_admin, is_sales)
                    if matches and not allow_duplicate:
                        answer = self._yp_duplicate_answer(matches, truncated, total, is_admin, is_sales)
                        answer.update(ok=False, code='duplicate')
                        return answer
                    lead_id = env_w['crm.lead'].create(vals).id     # the employee's own rights
        except LockNotAvailable:
            return self._yp_error('rate_limit', 'Hệ thống đang xử lý cùng số điện thoại/MST, thử lại sau.',
                                  retry_after=3, reason='busy')
        except AccessError as exc:
            return self._yp_error('forbidden', str(exc))
        except (UserError, ValidationError, IntegrityError) as exc:
            return self._yp_error('invalid', str(exc))
        _logger.info('CRM-002 yp_create_lead uid=%s lead=%s keys=%s forced=%s', uid, lead_id, len(keys),
                     bool(matches))
        return {'ok': True, 'id': lead_id}
