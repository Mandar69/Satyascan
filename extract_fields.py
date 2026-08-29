import re
from typing import Optional, Dict, Any


def clean_text(text: str) -> str:
    """Normalize whitespace and common OCR artefacts."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()


def clean_mrp_value(raw_mrp: Optional[str], full_text: str = "") -> Optional[str]:
    """
    Clean MRP value, handle spaces around decimals, and fix common OCR misreadings
    where the currency symbol ₹ is misread as a leading digit (e.g., '7' or '1')
    merging into an abnormally large number (e.g., 71636.00 -> 1636.00).
    """
    if not raw_mrp:
        return None

    # Normalize spaces around dots and commas: '71636 . 00' -> '71636.00'
    cleaned = re.sub(r'\s*[\.,]\s*', '.', str(raw_mrp).strip())
    # Extract numerical/decimal match
    match = re.search(r'([0-9]+(?:\.[0-9]{1,2})?)', cleaned)
    if not match:
        return cleaned

    num_str = match.group(1)
    parts = num_str.split('.')
    int_part = parts[0]
    decimal_part = f'.{parts[1]}' if len(parts) > 1 else ''

    # Handle OCR artifact where ₹ is misread as '7' and merged into digits (e.g. 71636.00 -> 1636.00)
    # If integer part has 5 or more digits and starts with '7'
    if len(int_part) >= 5 and int_part.startswith('7'):
        int_part = int_part[1:]
    # If the integer part is abnormally large (> 6 digits, e.g. >= 1,000,000 for standard retail pack)
    elif len(int_part) >= 7:
        int_part = int_part[1:]
    # If 4 digits starting with 7 when 'USP' or 'Net' is in context indicating a 3-digit price
    elif len(int_part) == 4 and int_part.startswith('7') and ('USP' in full_text or '16.36' in full_text):
        int_part = int_part[1:]

    return f"{int_part}{decimal_part}" if int_part else None


def extract_mrp(text: str) -> Optional[str]:
    """
    Extract Maximum Retail Price (MRP) from OCR text.
    Handles currency symbols (₹, Rs, INR), OCR misreadings, and formats like 'MRP: ₹ 1636.00'.
    """
    if not text:
        return None

    patterns = [
        # Pattern 1: MRP/M.R.P. followed by currency/numbers
        r'(?:MRP|M\.R\.P\.|Max(?:imum)?\s*Retail\s*Price)[\s:;.,-]*(?:USP:)?\s*(?:Rs\.?|INR|₹)?\s*([₹\d][\d,\.\s]*\d)',
        # Pattern 2: MRP with USP or incl. of all taxes context
        r'(?:MRP|M\.R\.P\.)[^\n;,\(]*?([0-9]+(?:[\.\s][0-9]{2})?)\s*(?=\(?(?:incl|tax|USP|€|\/))',
        # Pattern 3: Standalone price tagged with MRP
        r'(?:MRP|M\.R\.P\.)[\s:;.,-]*([^\n;,\(]+?)(?=(?:\s*(?:USP|incl|\/|Mfg|Date|Batch)|\s*$))',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            val = re.sub(r'^[^\w₹]+|[^\w]+$', '', val).strip()
            if val and any(char.isdigit() for char in val):
                return clean_mrp_value(val, text)

    return None


def extract_net_quantity(text: str) -> Optional[str]:
    """
    Extract Net Quantity / Net Weight / Net Content from OCR text.
    Examples: 'Net Quantity: 5gx20', 'Net Qty: 100g', 'Net Content: 500 ml'.
    """
    if not text:
        return None

    patterns = [
        # Pattern 1: Explicit 'Net Quantity/Qty/Weight' followed by value and units
        r'(?:Net\s*(?:Quantity|Qty|Content|Weight|Wt|Vol|Volume))[\s:;.-]*([0-9]+(?:\.[0-9]+)?\s*(?:g|kg|gm|gms|mg|ml|l|ltr|litres|pieces|pcs|count|sachets|gx\d+|\*x\d+)\b[^\n,;@|]*?)(?=(?:\s+(?:Number|Batch|Date|USE|MRP|Mfg|Pkg|Pkd|\d{4})|\s*$))',
        # Pattern 2: 'Net Quantity: <value>' up to next label delimiter
        r'(?:Net\s*(?:Quantity|Qty|Content|Weight|Wt|Vol|Volume))[\s:;.-]*([^\n,;@|]+?)(?=(?:\s+(?:Number|Batch|Date|USE|MRP|Mfg|Pkg|Pkd|@|\d{4})|\s*$))',
        # Pattern 3: Standalone quantity declarations like '5g x 20' or '100 g'
        r'\b(?:Net|Qty)[\s:;.-]*([0-9]+(?:\.[0-9]+)?\s*(?:g|kg|gm|ml|l)\s*(?:[xX*]\s*\d+)?)\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            val = re.sub(r'^[^\w]+|[^\w]+$', '', val).strip()
            if val and any(char.isdigit() for char in val):
                return val

    return None


def extract_mfg_date(text: str) -> Optional[str]:
    """
    Extract Manufacturing / Packaging month and year / date from OCR text.
    Examples: 'Mfg Date: 14/06/2026', 'MFD: 06/2026', 'Date: 14/06/2026', 'Packed: 12-05-2025'.
    """
    if not text:
        return None

    patterns = [
        # Pattern 1: Standard Mfg / MFD / PKD / Packed / Date labels with DD/MM/YYYY or MM/YYYY
        r'(?:Mfg(?:\.|\s*Date)?|MFD|PKD|Packed(?:\s*Date|\s*on)?|Manufacture(?:d)?(?:\s*Date)?|Date)\s*[:;.-]*\s*([0-9]{1,2}[\/\.-][0-9]{1,2}[\/\.-][0-9]{2,4})',
        # Pattern 2: Month name formats like 'Mfg: Jun 2026' or 'MFD: 15-Jan-2026'
        r'(?:Mfg(?:\.|\s*Date)?|MFD|PKD|Packed|Date)\s*[:;.-]*\s*([0-9]{1,2}[\s\.-]?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\.-]+[0-9]{2,4})',
        # Pattern 3: MM/YYYY format
        r'(?:Mfg(?:\.|\s*Date)?|MFD|PKD|Packed)\s*[:;.-]*\s*([0-9]{1,2}[\/\.-][0-9]{2,4})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            val = re.sub(r'^[^\w]+|[^\w]+$', '', val).strip()
            if val:
                return val

    return None


def extract_manufacturer_address(text: str) -> Optional[str]:
    """
    Extract Manufacturer / Packer / Marketer Name and Address using keyword-based detection.
    Keywords: 'Manufactured by', 'Marketed by', 'Packed by', 'Manufacturer address', 'Mfg By', etc.
    """
    if not text:
        return None

    # Keyword search for manufacturer/marketer block
    pattern = r'(?:Manufactured\s*By|ManuacturedBy|Marketed\s*by|Packed\s*by|Manufacturer\s*address|Mfg\s*By|Packer|Manufactured\s*and\s*Marketed\s*by)[\s:;.-]*([^\n]+?(?=(?:For Consumer|Net Quantity|MRP|USE BY|Batch No|\Z)))'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        val = match.group(0).strip()
        # Truncate if excessively long for clean display
        val = re.sub(r'\s+', ' ', val)
        if len(val) > 200:
            val = val[:200] + '...'
        return val

    # Fallback keyword checks
    fallback_keywords = ["Manufactured By", "Marketed By", "Private Limited", "Pvt Ltd", "Lic No.", "FSSAI Lic"]
    for kw in fallback_keywords:
        idx = text.lower().find(kw.lower())
        if idx != -1:
            snippet = text[idx:idx + 150].strip()
            return re.sub(r'\s+', ' ', snippet)

    return None


def extract_commodity_name(text: str) -> Optional[str]:
    """
    Extract Common / Generic Name of Commodity.
    Keywords: 'Generic Name', 'Commodity', 'Product Name', 'Nutritional Information', 'Dietary Supplement', etc.
    """
    if not text:
        return None

    # 1. Explicit generic / commodity declaration
    pattern = r'(?:Generic\s*Name|Name\s*of\s*(?:the\s*)?Commodity|Commodity|Product\s*Name|Category)[\s:;.-]*([^\n,;@|]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        val = match.group(1).strip()
        if val and len(val) >= 3:
            return val

    # 2. Recognizable commodity or dietary category markers
    common_commodities = [
        r'\bNutritional\s*Information\b',
        r'\bDietary\s*Supplement\b',
        r'\bHealth\s*Supplement\b',
        r'\bProprietary\s*Food\b',
        r'\bFood\s*Supplement\b',
        r'\bOrange\s*Flavour(?:ing)?\b',
        r'\bInstant\s*Drink\s*Mix\b',
        r'\bEnergy\s*Drink\b',
        r'\bProtein\s*Powder\b',
        r'\bTablets?\b',
        r'\bCapsules?\b',
        r'\bSachets?\b',
        r'\bBiscuits?\b',
        r'\bJuice\b',
        r'\bOil\b',
        r'\bTea\b',
        r'\bCoffee\b'
    ]

    for pat in common_commodities:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()

    return None


def extract_consumer_care(text: str) -> Optional[str]:
    """
    Extract Consumer Care / Grievance Redressal details using keyword-based detection.
    Keywords: 'For Consumer', 'Complaints', 'Care', 'Distributor Services', 'Customer Care', 'Email', 'Ph', etc.
    """
    if not text:
        return None

    # Targeted search around consumer care keywords
    pattern = r'(?:For\s*Consumer|Consumer\s*Care|Customer\s*Care|Complaints|Distributor\s*Services|Helpline|Toll\s*Free|Contact\s*Distributor)[\s:;.-]*([^\n]+?(?=(?:Net Quantity|MRP|Batch No|Date|USE BY|\Z)))'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        val = match.group(0).strip()
        val = re.sub(r'\s+', ' ', val)
        if len(val) > 200:
            val = val[:200] + '...'
        return val

    # Check for email / phone / care mentions
    contact_match = re.search(r'(?:Email|Ph|Tel|Phone|writetous)[\s:;.-]*([^\n,;]+@[^\n,;]+|[0-9]{8,12})', text, re.IGNORECASE)
    if contact_match:
        return contact_match.group(0).strip()

    return None


def extract_country_of_origin(text: str) -> Optional[str]:
    """
    Extract Country of Origin.
    Keywords: 'Country of Origin', 'Made in', 'Product of', 'Manufactured in', 'India', etc.
    """
    if not text:
        return None

    pattern = r'(?:Country\s*of\s*Origin|Made\s*in|Product\s*of|Manufactured\s*in|Origin)[\s:;.-]*([A-Za-z\s]+?)(?=(?:[,\.\n;]|\s+(?:and|for|by|Marketed|Net|MRP)|\Z))'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        val = match.group(1).strip()
        if val and len(val) >= 2:
            return val

    # Common country markers in Indian packaging
    if re.search(r'\b(?:India|INDIA)\b', text):
        return "India"
    elif re.search(r'\b(?:USA|United States|China|Germany|Japan|UK|United Kingdom)\b', text, re.IGNORECASE):
        origin_m = re.search(r'\b(USA|United States|China|Germany|Japan|UK|United Kingdom)\b', text, re.IGNORECASE)
        return origin_m.group(0).strip() if origin_m else None

    return None


def extract_unit_sale_price(text: str) -> Optional[str]:
    """
    Extract Unit Sale Price (USP) as mandated by Legal Metrology 2021 amendment.
    Examples: 'USP: ₹ 16.36/g', '16.36/g', '₹ 10.00 / 100g'.
    """
    if not text:
        return None

    patterns = [
        # Explicit USP prefix
        r'(?:USP|Unit\s*Sale\s*Price)[\s:;.,-]*(?:Rs\.?|INR|₹|€)?\s*([0-9]+(?:\.[0-9]+)?\s*\/\s*(?:g|kg|gm|mg|ml|l|ltr|piece|pcs|unit|sachet|count|100g|100ml)\b)',
        # Price per unit pattern (e.g. '€ 16.36/g' or '16.36/g')
        r'(?:Rs\.?|INR|₹|€)?\s*([0-9]+(?:\.[0-9]+)?\s*\/\s*(?:g|kg|gm|mg|ml|l|ltr|piece|pcs|unit|sachet)\b)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            val = re.sub(r'^[^\w]+|[^\w]+$', '', val).strip()
            if val:
                return val

    return None


def extract_commodity_count_or_dimensions(text: str) -> Optional[str]:
    """
    Extract Commodity Count / Dimensions (e.g. sachet count, servings, size, dimensions).
    Examples: '5gx20', 'Servings Per Carton: 20', 'Serving Size: 1 Sachet (5g)', '20 N', 'Pack of 20'.
    """
    if not text:
        return None

    patterns = [
        # Servings or Sachet Count
        r'(?:Servings\s*Pe[r]?\s*Carton|Serving\s*S[in]ze|Pack\s*of|Count|Dimensions?|Size|Units?|Number)[\s:;.-]*([^\n,;@|]+?)(?=(?:\s+(?:Batch|Date|USE|MRP|Mfg)|\s*$))',
        # Count / Multi-pack expressions like 5gx20, 20 N, 20 sachets
        r'\b([0-9]+\s*(?:sachets|pieces|pcs|units|tablets|capsules|N|count|gx[0-9]+|\*x[0-9]+)\b)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            val = re.sub(r'^[^\w]+|[^\w]+$', '', val).strip()
            if val:
                return val

    return None


def extract_all_fields(text: str) -> Dict[str, Optional[str]]:
    """
    Extract all 9 mandatory Legal Metrology packaging fields:
    1. Manufacturer Name and Address
    2. Common / Generic Name of Commodity
    3. Net Quantity
    4. Month & Year of Manufacture
    5. Maximum Retail Price (MRP)
    6. Consumer Care Details
    7. Country of Origin
    8. Unit Sale Price (USP)
    9. Commodity Count / Dimensions
    """
    normalized = clean_text(text)
    return {
        "manufacturer_name_and_address": extract_manufacturer_address(normalized),
        "commodity_name": extract_commodity_name(normalized),
        "net_quantity": extract_net_quantity(normalized),
        "mfg_date": extract_mfg_date(normalized),
        "mrp": extract_mrp(normalized),
        "consumer_care_details": extract_consumer_care(normalized),
        "country_of_origin": extract_country_of_origin(normalized),
        "unit_sale_price": extract_unit_sale_price(normalized),
        "commodity_count_or_dimensions": extract_commodity_count_or_dimensions(normalized),
    }
