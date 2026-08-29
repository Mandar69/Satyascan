from typing import Dict, Any, Optional, List

# All 9 Mandatory Declarations under Rule 6 of Legal Metrology (Packaged Commodities) Rules, 2011
FIELD_DEFINITIONS = {
    "manufacturer_name_and_address": {
        "field": "Manufacturer Name and Address",
        "display_name": "Name and Complete Address of Manufacturer / Packer",
        "regulation": "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(a)",
        "fix_instruction": "Display the name and complete physical address of the manufacturer, packer, or importer clearly on the packaging label."
    },
    "commodity_name": {
        "field": "Common / Generic Name of Commodity",
        "display_name": "Common or Generic Name of the Commodity",
        "regulation": "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(b)",
        "fix_instruction": "Mention the common or generic name of the commodity contained in the package clearly on the principal display panel."
    },
    "net_quantity": {
        "field": "Net Quantity",
        "display_name": "Net Quantity in Standard Units",
        "regulation": "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(c)",
        "fix_instruction": "Declare Net Quantity in standard units of weight, measure, or count (e.g., 'Net Qty: 100 g', 'Net Content: 500 ml', '5g x 20 sachets') in prominent contrasting font."
    },
    "mfg_date": {
        "field": "Month and Year of Manufacture",
        "display_name": "Month & Year of Manufacture / Packaging",
        "regulation": "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(d)",
        "fix_instruction": "Clearly indicate the month and year of manufacture, pre-packing, or import (e.g., 'Mfg Date: MM/YYYY' or 'MFD: DD/MM/YYYY')."
    },
    "mrp": {
        "field": "Maximum Retail Price (MRP)",
        "display_name": "Maximum Retail Price (MRP)",
        "regulation": "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(e)",
        "fix_instruction": "Declare the Maximum Retail Price in Indian Rupees (₹ / Rs.) clearly stating 'inclusive of all taxes' (e.g., 'MRP ₹ 1636.00 (incl. of all taxes)') on the principal display panel."
    },
    "consumer_care_details": {
        "field": "Consumer Care Details",
        "display_name": "Consumer Grievance Redressal / Care Details",
        "regulation": "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(n)",
        "fix_instruction": "Provide consumer grievance redressal details including contact person/office name, address, telephone number, and email address."
    },
    "country_of_origin": {
        "field": "Country of Origin",
        "display_name": "Country of Origin / Manufacture",
        "regulation": "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(10)",
        "fix_instruction": "Clearly mention the Country of Origin (e.g., 'Made in India' or 'Country of Origin: India') on the label."
    },
    "unit_sale_price": {
        "field": "Unit Sale Price",
        "display_name": "Unit Sale Price (USP)",
        "regulation": "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(11) (2021 Amendment)",
        "fix_instruction": "Declare Unit Sale Price rounded off to two decimal places in terms of per g/kg/ml/l/unit (e.g., 'USP: ₹ 16.36 / g') wherever MRP is declared."
    },
    "commodity_count_or_dimensions": {
        "field": "Commodity Count / Dimensions",
        "display_name": "Commodity Count / Dimensions / Size",
        "regulation": "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(m)",
        "fix_instruction": "Specify the number of usable units, count, or dimensions (length, breadth, height) contained in the package (e.g., 'Pack of 20 Sachets', 'Net Quantity: 20 N')."
    }
}


def check_compliance(extracted_fields: Dict[str, Optional[str]]) -> List[Dict[str, Any]]:
    """
    Check all 9 mandatory Legal Metrology packaging fields.
    Returns a list of compliance check results with status, detected value, and fix instructions for each field.
    """
    report = []
    for field_key, defs in FIELD_DEFINITIONS.items():
        val = extracted_fields.get(field_key)
        is_present = bool(val and str(val).strip())

        report.append({
            "field": defs["field"],
            "value": val if is_present else None,
            "status": "PASS" if is_present else "FAIL",
            "fix_instruction": None if is_present else defs["fix_instruction"]
        })

    return report
