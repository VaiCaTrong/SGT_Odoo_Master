"""Pure CRM Documents folder-name rules, reusable in offline contract tests."""
import re

_INVALID = set('\\/:*?"<>|')


def normalize_company_tax(value):
    return str(value or '').strip().upper()


def folder_name_for_company(company, tax):
    tax = normalize_company_tax(tax)
    company = re.sub(r'\s+', ' ', str(company or '')).strip()
    company = ''.join('_' if ch in _INVALID or ord(ch) < 32 else ch for ch in company).strip()
    if not company or not tax or not re.fullmatch(r'[0-9A-Z._-]{4,50}', tax):
        raise ValueError('Company name and valid tax ID are required')
    suffix = ' - ' + tax
    name = company[:255 - len(suffix)].rstrip(' ._-') + suffix
    return name


def matches_company_tax_folder(name, tax):
    """Match legacy 'TAX' or new 'COMPANY - TAX'; never a partial tax."""
    tax = normalize_company_tax(tax)
    if not tax or not isinstance(name, str):
        return False
    name = name.strip()
    return name.upper() == tax or name.upper().endswith(' - ' + tax)
