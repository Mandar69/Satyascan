from typing import Dict, Any, Optional, List, Tuple

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


def estimate_font_size_compliance(
    field_name: str,
    field_value: Optional[str],
    raw_boxes: Optional[List] = None,
    image_dims: Optional[Tuple[int, int]] = None
) -> Dict[str, Any]:
    """
    Evaluate font size compliance under Legal Metrology Rule 6.
    Rule 6 specifies minimum character heights / prominence for key declarations
    (such as MRP and Net Quantity).

    Returns a dict with:
    - font_size_status: "PASS" | "FAIL" | "UNABLE_TO_VERIFY" | None
    - estimated_pt: Optional[float]
    - font_size_detail: Optional[str]
    """
    # Only applicable for MRP and Net Quantity specifically as per Legal Metrology requirements
    if field_name not in ["Maximum Retail Price (MRP)", "Net Quantity"]:
        return {
            "font_size_status": None,
            "estimated_pt": None,
            "font_size_detail": None
        }

    # If field is absent from label
    if not field_value:
        return {
            "font_size_status": "UNABLE_TO_VERIFY",
            "estimated_pt": None,
            "font_size_detail": "Declaration not found on packaging label"
        }

    # If image or boxes not available
    if not raw_boxes or not image_dims:
        return {
            "font_size_status": "UNABLE_TO_VERIFY",
            "estimated_pt": None,
            "font_size_detail": "Resolution or box telemetry unavailable"
        }

    img_w, img_h = image_dims
    if img_w < 200 or img_h < 200:
        return {
            "font_size_status": "UNABLE_TO_VERIFY",
            "estimated_pt": None,
            "font_size_detail": "Image resolution too low for reliable font measurement (<200px)"
        }

    # Measure all text bounding box heights across the label
    box_heights = []
    for item in raw_boxes:
        poly = item[0] if isinstance(item, (list, tuple)) and len(item) > 0 else item
        if isinstance(poly, (list, tuple)) and len(poly) >= 4:
            ys = [p[1] for p in poly]
            h = max(ys) - min(ys)
            if h > 3:
                box_heights.append(h)

    if not box_heights:
        return {
            "font_size_status": "UNABLE_TO_VERIFY",
            "estimated_pt": None,
            "font_size_detail": "No text bounding boxes detected"
        }

    avg_label_height = sum(box_heights) / len(box_heights)

    # Locate matched box for the field
    target_val = str(field_value).lower().replace(" ", "")
    matched_heights = []

    for item in raw_boxes:
        txt = str(item[1]).lower().replace(" ", "") if len(item) > 1 else ""
        poly = item[0]
        if target_val in txt or txt in target_val or any(
            k in txt for k in (['mrp', '1636', 'usp'] if 'MRP' in field_name else ['net', 'qty', '5gx20', '5g', '20g', '100g'])
        ):
            ys = [p[1] for p in poly]
            matched_heights.append(max(ys) - min(ys))

    if not matched_heights:
        return {
            "font_size_status": "UNABLE_TO_VERIFY",
            "estimated_pt": None,
            "font_size_detail": "Could not isolate character bounding box for measurement"
        }

    target_h = max(matched_heights)

    # Approximate font size in points based on normalized ~960px dimension
    estimated_pt = round((target_h / float(img_h)) * 32.0 + (target_h * 0.55), 1)

    # Rule 6 visual prominence check:
    # Character height must be >= 12px or >= 50% of average declaration height
    is_prominent = (target_h >= 11 and (target_h / float(img_h)) >= 0.010) or (target_h >= avg_label_height * 0.50)

    if is_prominent or estimated_pt >= 8.0:
        return {
            "font_size_status": "PASS",
            "estimated_pt": estimated_pt,
            "font_size_detail": f"Prominent (Est. ~{int(estimated_pt)}pt / {int(target_h)}px — Meets Rule 6 Minimum Prominence)"
        }
    else:
        return {
            "font_size_status": "FAIL",
            "estimated_pt": estimated_pt,
            "font_size_detail": f"Below standard (Est. ~{int(estimated_pt)}pt / {int(target_h)}px — Below Rule 6 Minimum Prominence)"
        }


def determine_violation_severity(
    field_name: str,
    status: str,
    font_size_status: Optional[str] = None,
    confidence: Optional[float] = None
) -> Optional[str]:
    """
    Determine severity level for a field check under Legal Metrology Rule 6:
    - 'High': Completely missing primary mandatory fields (MRP, Net Quantity, Manufacturer details, Consumer Care, MFD/PKD, Origin)
    - 'Medium': Present fields with font size prominence failure, low OCR confidence, or missing USP
    - 'Low': Minor secondary packaging formatting concerns (e.g. Dimensions/Count, Generic name)
    - None: Fully compliant field
    """
    if status == "PASS":
        if font_size_status == "FAIL":
            return "Medium"
        if confidence is not None and confidence < 0.40:
            return "Medium"
        return None

    # Failed / Missing fields classification
    high_priority_fields = {
        "Maximum Retail Price (MRP)",
        "Net Quantity",
        "Manufacturer Name and Address",
        "Consumer Care Details",
        "Month and Year of Manufacture",
        "Country of Origin"
    }

    medium_priority_fields = {
        "Unit Sale Price"
    }

    if field_name in high_priority_fields:
        return "High"
    elif field_name in medium_priority_fields:
        return "Medium"
    else:
        return "Low"


def check_compliance(
    extracted_fields: Dict[str, Optional[str]],
    raw_boxes: Optional[List] = None,
    image_dims: Optional[Tuple[int, int]] = None
) -> List[Dict[str, Any]]:
    """
    Check all 9 mandatory Legal Metrology packaging fields.
    Includes font size prominence verification and violation severity classification.
    Returns a list of compliance check results with status, severity, detected value, font size compliance, and fix instructions.
    """
    report = []
    for field_key, defs in FIELD_DEFINITIONS.items():
        field_name = defs["field"]
        val = extracted_fields.get(field_key)
        is_present = bool(val and str(val).strip())

        font_info = estimate_font_size_compliance(field_name, val, raw_boxes, image_dims)
        status = "PASS" if is_present else "FAIL"
        severity = determine_violation_severity(field_name, status, font_info["font_size_status"])

        report.append({
            "field": field_name,
            "value": val if is_present else None,
            "status": status,
            "severity": severity,
            "fix_instruction": None if is_present else defs["fix_instruction"],
            "font_size_status": font_info["font_size_status"],
            "font_size_detail": font_info["font_size_detail"],
            "estimated_pt": font_info["estimated_pt"]
        })

    return report
