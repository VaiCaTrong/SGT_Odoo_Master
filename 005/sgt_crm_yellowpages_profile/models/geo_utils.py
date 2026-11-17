"""Small, side-effect-free helpers for CRM-005 lead geolocation.

Never infer a country's location from the Main Market field; geocoding uses
only the address fields already persisted on crm.lead.
"""
import math
import re


def valid_coordinates(latitude, longitude):
    try:
        lat, lon = float(latitude), float(longitude)
    except (ValueError, TypeError):
        return False
    return (math.isfinite(lat) and math.isfinite(lon)
            and -90 <= lat <= 90 and -180 <= lon <= 180
            and not (lat == 0 and lon == 0))


def clean_part(part):
    return ' '.join(str(part or '').split())


def address_is_usable(street, street2='', city='', state='', zip_code='', country=''):
    """A locality + country is enough for an *explicitly approximate* result.

    A country alone must not produce a pin. Street-only without the country is
    too ambiguous for automated location. All address fields are read from the
    Deal, not Contacts or Market tags.
    """
    return bool(clean_part(country) and (clean_part(city) or clean_part(state)))


def address_signature(street='', street2='', city='', state='', zip_code='', country=''):
    return '|'.join(clean_part(value).casefold() for value in (
        street, street2, city, state, zip_code, country,
    ))


def geocoder_postal_code(zip_code, country=''):
    """Clean the geocoder input, without editing a saved Deal address.

    Vietnam uses numeric 5-digit postal codes (legacy data may have 6 digits).
    A region name accidentally imported into ZIP must not pollute the address
    sent to the geocoder. All other countries preserve their native format.
    """
    code = clean_part(zip_code)
    region = clean_part(country).casefold()
    if ('vietnam' in region or 'viet nam' in region or 'việt nam' in region):
        return code if re.fullmatch(r'[0-9]{5,6}', code) else ''
    return code
