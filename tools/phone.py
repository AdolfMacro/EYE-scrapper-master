import re


PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ENGLISH_DIGITS = "0123456789"


def normalize_digits(text):
    if text is None:
        return ""

    translation = str.maketrans(
        PERSIAN_DIGITS + ARABIC_DIGITS,
        ENGLISH_DIGITS + ENGLISH_DIGITS
    )

    return str(text).translate(translation)


def normalize_phone(phone):
    if phone is None:
        return None

    phone = normalize_digits(phone).strip()

    if not phone:
        return None

    # Normalize Persian plus / Arabic variants if present
    phone = phone.replace("＋", "+")

    # Remove common separators
    phone = re.sub(
        r"[\s\-().\[\]{}]",
        "",
        phone
    )

    # +98XXXXXXXXXX
    if phone.startswith("+98"):
        phone = "0" + phone[3:]

    # 0098XXXXXXXXXX
    elif phone.startswith("0098"):
        phone = "0" + phone[4:]

    # 98XXXXXXXXXX
    elif phone.startswith("98") and len(phone) in (12, 13):
        phone = "0" + phone[2:]

    # Keep digits only
    phone = re.sub(r"\D", "", phone)

    return phone or None


def is_valid_phone(phone):
    if not phone:
        return False

    phone = normalize_phone(phone)

    if not phone:
        return False

    # Iranian mobile
    if re.fullmatch(r"09\d{9}", phone):
        return True

    # Iranian landline
    #
    # 02112345678
    # 04112345678
    # 01312345678
    #
    if re.fullmatch(r"0\d{9,10}", phone):
        return True

    return False


def extract_phones(text):
    if not text:
        return []

    text = normalize_digits(text)

    patterns = [

        # +98 912 123 4567
        r"\+98[\s\-]?9\d{2}[\s\-]?\d{3}[\s\-]?\d{4}",

        # 0098 912 123 4567
        r"0098[\s\-]?9\d{2}[\s\-]?\d{3}[\s\-]?\d{4}",

        # 0912 123 4567
        r"09\d{2}[\s\-]?\d{3}[\s\-]?\d{4}",

        # 021 12345678
        r"0\d{2,3}[\s\-]?\d{7,8}",
    ]

    results = []

    for pattern in patterns:

        for match in re.findall(pattern, text):

            phone = normalize_phone(match)

            if not phone:
                continue

            if not is_valid_phone(phone):
                continue

            if phone not in results:
                results.append(phone)

    return results


def extract_phone(text):
    phones = extract_phones(text)

    return phones[0] if phones else None


def unique_phones(phones):
    result = []

    for phone in phones or []:

        normalized = normalize_phone(phone)

        if not normalized:
            continue

        if not is_valid_phone(normalized):
            continue

        if normalized not in result:
            result.append(normalized)

    return result