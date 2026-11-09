#!/usr/bin/env python3
"""Generate the independent English business-text holdout dataset (60 documents).

Creates 20 business forms, 20 invoices, and 20 business correspondence emails/letters
with exact character-span ground-truth annotations for the 6 required MVP PII categories:
- PERSON
- EMAIL_ADDRESS
- PHONE_NUMBER
- LOCATION
- DATE_TIME
- US_SSN

All data is 100% synthetic and deterministic. Every span offset is verified against
the raw text before saving to `evaluation/data/business_holdout_60.jsonl`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_LABELS = {
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "LOCATION",
    "DATE_TIME",
    "US_SSN",
}


def build_tagged_document(
    doc_id: str,
    doc_type: str,
    template: str,
    fields: list[tuple[str, str, str]],
) -> dict[str, Any]:
    """Build a document with verified non-overlapping character spans from placeholders.

    Args:
        doc_id: Unique document identifier.
        doc_type: One of 'form', 'invoice', 'correspondence'.
        template: String containing `{KEY}` placeholders in sequential order.
        fields: List of `(placeholder_key, value_text, label)` tuples.
    """
    text = template
    spans: list[dict[str, Any]] = []

    # Replace placeholders sequentially and track exact character offsets
    cursor = 0
    out_pieces: list[str] = []
    field_map = {k: (v, lbl) for k, v, lbl in fields}

    i = 0
    n = len(template)
    while i < n:
        open_idx = template.find("{{", i)
        if open_idx == -1:
            out_pieces.append(template[i:])
            cursor += n - i
            break
        out_pieces.append(template[i:open_idx])
        cursor += open_idx - i
        close_idx = template.find("}}", open_idx + 2)
        if close_idx == -1:
            raise ValueError(f"Unclosed placeholder in {doc_id}")
        key = template[open_idx + 2 : close_idx]
        if key not in field_map:
            raise KeyError(f"Missing field {key} in {doc_id}")
        val, label = field_map[key]
        if label not in REQUIRED_LABELS:
            raise ValueError(f"Invalid label {label} in {doc_id}")
        start = cursor
        out_pieces.append(val)
        cursor += len(val)
        end = cursor
        spans.append(
            {
                "start": start,
                "end": end,
                "label": label,
                "text": val,
            }
        )
        i = close_idx + 2

    final_text = "".join(out_pieces)
    for sp in spans:
        extracted = final_text[sp["start"] : sp["end"]]
        assert extracted == sp["text"], (
            f"Span mismatch in {doc_id}: expected {sp['text']!r}, got {extracted!r}"
        )

    return {
        "id": doc_id,
        "doc_type": doc_type,
        "language": "en",
        "source": f"independent_business_{doc_type}",
        "text": final_text,
        "spans": spans,
    }


def generate_documents() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []

    # 20 Synthetic Business Forms (onboarding, W-9 style vendor intake, benefits, credit app, background check)
    forms_data = [
        (
            "form_01",
            "EMPLOYEE ONBOARDING & TAX WITHHOLDING FORM\n"
            "Full Legal Name: {{NAME1}}\n"
            "Social Security Number: {{SSN1}}\n"
            "Date of Birth: {{DOB1}}\n"
            "Primary Residence: {{ADDR1}}\n"
            "Personal Email: {{EMAIL1}}\n"
            "Mobile Telephone: {{PHONE1}}\n"
            "Emergency Contact: {{NAME2}} ({{PHONE2}})\n"
            "Form Signed On: {{DATE1}}",
            [
                ("NAME1", "Evelyn Vance", "PERSON"),
                ("SSN1", "412-58-9034", "US_SSN"),
                ("DOB1", "1987-04-19", "DATE_TIME"),
                ("ADDR1", "742 Evergreen Terrace, Springfield, IL 62704", "LOCATION"),
                ("EMAIL1", "evelyn.vance87@oakridge-mail.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(217) 555-0148", "PHONE_NUMBER"),
                ("NAME2", "Marcus Vance", "PERSON"),
                ("PHONE2", "(217) 555-0192", "PHONE_NUMBER"),
                ("DATE1", "October 14, 2025", "DATE_TIME"),
            ],
        ),
        (
            "form_02",
            "VENDOR REGISTRATION & TAXPAYER IDENTIFICATION CERTIFICATE\n"
            "Sole Proprietor Name: {{NAME1}}\n"
            "Taxpayer SSN: {{SSN1}}\n"
            "Business Mailing Address: {{ADDR1}}\n"
            "Accounts Payable Contact Email: {{EMAIL1}}\n"
            "Direct Office Line: {{PHONE1}}\n"
            "Effective Registration Date: {{DATE1}}",
            [
                ("NAME1", "Gregory H. Sterling", "PERSON"),
                ("SSN1", "529-44-1872", "US_SSN"),
                ("ADDR1", "1480 Peachtree Street NE, Suite 410, Atlanta, GA 30309", "LOCATION"),
                ("EMAIL1", "g.sterling@sterling-consulting.org", "EMAIL_ADDRESS"),
                ("PHONE1", "+1-404-555-0163", "PHONE_NUMBER"),
                ("DATE1", "03/22/2025", "DATE_TIME"),
            ],
        ),
        (
            "form_03",
            "COMMERCIAL LEASE GUARANTOR APPLICATION\n"
            "Guarantor Name: {{NAME1}}\n"
            "SSN: {{SSN1}} | Birth Date: {{DOB1}}\n"
            "Current Home Address: {{ADDR1}}\n"
            "Prior Address: {{ADDR2}}\n"
            "Guarantor Email: {{EMAIL1}} | Cell: {{PHONE1}}\n"
            "Application Submitted: {{DATE1}}",
            [
                ("NAME1", "Nadia Al-Mansoor", "PERSON"),
                ("SSN1", "604-91-3345", "US_SSN"),
                ("DOB1", "August 11, 1979", "DATE_TIME"),
                ("ADDR1", "2250 Vallejo Street, San Francisco, CA 94123", "LOCATION"),
                ("ADDR2", "890 Bryant Street, Palo Alto, CA 94301", "LOCATION"),
                ("EMAIL1", "nadia.almansoor@pacific-ventures.io", "EMAIL_ADDRESS"),
                ("PHONE1", "415-555-0184", "PHONE_NUMBER"),
                ("DATE1", "November 3, 2025", "DATE_TIME"),
            ],
        ),
        (
            "form_04",
            "DIRECT DEPOSIT & PAYROLL AUTHORIZATION FORM\n"
            "Employee: {{NAME1}} | SSN: {{SSN1}}\n"
            "Branch City: {{ADDR1}}\n"
            "Work Email: {{EMAIL1}} | Phone: {{PHONE1}}\n"
            "Effective Payroll Cycle Date: {{DATE1}}\n"
            "Reviewed by HR Representative: {{NAME2}}",
            [
                ("NAME1", "Desmond K. O'Connor", "PERSON"),
                ("SSN1", "318-77-6409", "US_SSN"),
                ("ADDR1", "400 Boylston Street, Boston, MA 02116", "LOCATION"),
                ("EMAIL1", "d.oconnor@beaconhill-logistics.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(617) 555-0129", "PHONE_NUMBER"),
                ("DATE1", "2025-07-01", "DATE_TIME"),
                ("NAME2", "Hannah Lindqvist", "PERSON"),
            ],
        ),
        (
            "form_05",
            "BENEFITS ENROLLMENT & DEPENDENT DECLARATION\n"
            "Primary Subscriber: {{NAME1}} (SSN: {{SSN1}}, DOB: {{DOB1}})\n"
            "Spouse / Dependent: {{NAME2}} (SSN: {{SSN2}}, DOB: {{DOB2}})\n"
            "Residential Address: {{ADDR1}}\n"
            "Subscriber Email: {{EMAIL1}} | Daytime Phone: {{PHONE1}}",
            [
                ("NAME1", "Carlos Eduardo Rivera", "PERSON"),
                ("SSN1", "455-82-7190", "US_SSN"),
                ("DOB1", "05/14/1984", "DATE_TIME"),
                ("NAME2", "Lucia M. Rivera", "PERSON"),
                ("SSN2", "455-82-9914", "US_SSN"),
                ("DOB2", "09/28/1986", "DATE_TIME"),
                ("ADDR1", "3910 Brickell Avenue, Apt 12B, Miami, FL 33131", "LOCATION"),
                ("EMAIL1", "carlos.rivera@bayside-freight.net", "EMAIL_ADDRESS"),
                ("PHONE1", "305-555-0177", "PHONE_NUMBER"),
            ],
        ),
        (
            "form_06",
            "CONTRACTOR SECURITY CLEARANCE INTAKE SHEET\n"
            "Applicant Name: {{NAME1}}\n"
            "National ID / US SSN: {{SSN1}}\n"
            "Date of Birth: {{DOB1}}\n"
            "Place of Birth: {{ADDR1}}\n"
            "Current Street Address: {{ADDR2}}\n"
            "Contact Email: {{EMAIL1}} | Contact Number: {{PHONE1}}\n"
            "Intake Timestamp: {{DATE1}}",
            [
                ("NAME1", "Trevor J. MacAllister", "PERSON"),
                ("SSN1", "219-63-4081", "US_SSN"),
                ("DOB1", "1991-12-03", "DATE_TIME"),
                ("ADDR1", "Baltimore, Maryland", "LOCATION"),
                ("ADDR2", "1725 I Street NW, Washington, DC 20006", "LOCATION"),
                ("EMAIL1", "tmacallister@potomac-defense.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(202) 555-0155", "PHONE_NUMBER"),
                ("DATE1", "2025-09-18 09:30:00", "DATE_TIME"),
            ],
        ),
        (
            "form_07",
            "CORPORATE CREDIT CARD HOLDER AGREEMENT\n"
            "Cardholder Full Name: {{NAME1}}\n"
            "Verification SSN: {{SSN1}}\n"
            "Date of Birth: {{DOB1}}\n"
            "Billing Delivery Location: {{ADDR1}}\n"
            "Corporate Email: {{EMAIL1}}\n"
            "Mobile Alert Number: {{PHONE1}}\n"
            "Agreement Execution Date: {{DATE1}}",
            [
                ("NAME1", "Priya Nair-Subramanian", "PERSON"),
                ("SSN1", "571-30-8826", "US_SSN"),
                ("DOB1", "February 2, 1990", "DATE_TIME"),
                ("ADDR1", "500 Yale Avenue North, Seattle, WA 98109", "LOCATION"),
                ("EMAIL1", "priya.nair@cascadia-biotech.com", "EMAIL_ADDRESS"),
                ("PHONE1", "+1 (206) 555-0134", "PHONE_NUMBER"),
                ("DATE1", "January 15, 2026", "DATE_TIME"),
            ],
        ),
        (
            "form_08",
            "WORKPLACE INCIDENT & CLAIM REPORT FORM\n"
            "Claimant Name: {{NAME1}} | SSN: {{SSN1}}\n"
            "Incident Date: {{DATE1}} | Reported Date: {{DATE2}}\n"
            "Facility Address: {{ADDR1}}\n"
            "Supervisor on Duty: {{NAME2}}\n"
            "Claimant Email: {{EMAIL1}} | Claimant Phone: {{PHONE1}}",
            [
                ("NAME1", "Kenneth R. Kowalski", "PERSON"),
                ("SSN1", "384-29-5501", "US_SSN"),
                ("DATE1", "2025-06-11", "DATE_TIME"),
                ("DATE2", "2025-06-12", "DATE_TIME"),
                ("ADDR1", "2100 West Loop South, Houston, TX 77027", "LOCATION"),
                ("NAME2", "Derrick Boone", "PERSON"),
                ("EMAIL1", "kkowalski@gulfcoast-fabrication.com", "EMAIL_ADDRESS"),
                ("PHONE1", "713-555-0168", "PHONE_NUMBER"),
            ],
        ),
        (
            "form_09",
            "INDEPENDENT AUDITOR INDEPENDENCE & DISCLOSURE FORM\n"
            "Auditor Name: {{NAME1}}\n"
            "Individual SSN: {{SSN1}}\n"
            "Home Office Address: {{ADDR1}}\n"
            "Email Address: {{EMAIL1}}\n"
            "Telephone: {{PHONE1}}\n"
            "Filing Period End Date: {{DATE1}}",
            [
                ("NAME1", "Miriam Goldstein", "PERSON"),
                ("SSN1", "134-65-7729", "US_SSN"),
                ("ADDR1", "350 Fifth Avenue, Floor 28, New York, NY 10118", "LOCATION"),
                ("EMAIL1", "mgoldstein@hudson-audit-llp.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(212) 555-0199", "PHONE_NUMBER"),
                ("DATE1", "December 31, 2025", "DATE_TIME"),
            ],
        ),
        (
            "form_10",
            "RELOCATION REIMBURSEMENT REQUEST FORM\n"
            "Transferring Employee: {{NAME1}} (SSN: {{SSN1}})\n"
            "Origin Address: {{ADDR1}}\n"
            "Destination Address: {{ADDR2}}\n"
            "Move Completion Date: {{DATE1}}\n"
            "Employee Email: {{EMAIL1}} | Contact Phone: {{PHONE1}}",
            [
                ("NAME1", "Aiden C. Gallagher", "PERSON"),
                ("SSN1", "492-18-6340", "US_SSN"),
                ("ADDR1", "1120 Lincoln Street, Denver, CO 80203", "LOCATION"),
                ("ADDR2", "601 Congress Avenue, Austin, TX 78701", "LOCATION"),
                ("DATE1", "August 29, 2025", "DATE_TIME"),
                ("EMAIL1", "aiden.gallagher@rockymountain-cloud.io", "EMAIL_ADDRESS"),
                ("PHONE1", "303-555-0141", "PHONE_NUMBER"),
            ],
        ),
        (
            "form_11",
            "SHAREHOLDER PROXY & TAX CERTIFICATION\n"
            "Registered Holder: {{NAME1}}\n"
            "Tax ID (SSN): {{SSN1}}\n"
            "Holder Birth Date: {{DOB1}}\n"
            "Registered Street Address: {{ADDR1}}\n"
            "Investor Relations Email: {{EMAIL1}}\n"
            "Investor Phone: {{PHONE1}}\n"
            "Record Date: {{DATE1}}",
            [
                ("NAME1", "Beatrice Chen-Wu", "PERSON"),
                ("SSN1", "548-90-1123", "US_SSN"),
                ("DOB1", "1968-11-24", "DATE_TIME"),
                ("ADDR1", "450 Newport Center Drive, Newport Beach, CA 92660", "LOCATION"),
                ("EMAIL1", "b.chenwu@pacificcrest-capital.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(949) 555-0112", "PHONE_NUMBER"),
                ("DATE1", "April 10, 2025", "DATE_TIME"),
            ],
        ),
        (
            "form_12",
            "COMMERCIAL FLEET DRIVER QUALIFICATION FILE\n"
            "Driver Name: {{NAME1}} | SSN: {{SSN1}}\n"
            "Date of Birth: {{DOB1}}\n"
            "Home Terminal Address: {{ADDR1}}\n"
            "Dispatch Email: {{EMAIL1}} | Driver Cell: {{PHONE1}}\n"
            "Medical Certificate Expiration: {{DATE1}}",
            [
                ("NAME1", "Raymond T. Beauregard", "PERSON"),
                ("SSN1", "431-55-8092", "US_SSN"),
                ("DOB1", "07/09/1975", "DATE_TIME"),
                ("ADDR1", "950 Poydras Street, New Orleans, LA 70112", "LOCATION"),
                ("EMAIL1", "r.beauregard@delta-transit.org", "EMAIL_ADDRESS"),
                ("PHONE1", "504-555-0188", "PHONE_NUMBER"),
                ("DATE1", "2026-07-09", "DATE_TIME"),
            ],
        ),
        (
            "form_13",
            "INTELLECTUAL PROPERTY ASSIGNMENT & INVENTOR RECORD\n"
            "Lead Inventor: {{NAME1}} (SSN: {{SSN1}})\n"
            "Co-Inventor: {{NAME2}}\n"
            "Lab Location: {{ADDR1}}\n"
            "Correspondence Email: {{EMAIL1}} | Lab Extension: {{PHONE1}}\n"
            "Assignment Signed Date: {{DATE1}}",
            [
                ("NAME1", "Dr. Soren Lindholm", "PERSON"),
                ("SSN1", "288-41-9507", "US_SSN"),
                ("NAME2", "Mei-Ling Zhou", "PERSON"),
                ("ADDR1", "1000 Main Street, Cambridge, MA 02142", "LOCATION"),
                ("EMAIL1", "slindholm@kendall-photonics.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(617) 555-0174", "PHONE_NUMBER"),
                ("DATE1", "May 5, 2025", "DATE_TIME"),
            ],
        ),
        (
            "form_14",
            "CONSULTING RETAINER BACKGROUND AUTHORIZATION\n"
            "Consultant Full Name: {{NAME1}}\n"
            "Social Security Number: {{SSN1}}\n"
            "Date of Birth: {{DOB1}}\n"
            "Permanent Address: {{ADDR1}}\n"
            "Consultant Email: {{EMAIL1}} | Direct Mobile: {{PHONE1}}\n"
            "Consent Date: {{DATE1}}",
            [
                ("NAME1", "Vanessa J.holloway", "PERSON"),
                ("SSN1", "367-12-4498", "US_SSN"),
                ("DOB1", "1982-03-17", "DATE_TIME"),
                ("ADDR1", "200 South Tryon Street, Charlotte, NC 28202", "LOCATION"),
                ("EMAIL1", "v.holloway@piedmont-advisory.com", "EMAIL_ADDRESS"),
                ("PHONE1", "704-555-0139", "PHONE_NUMBER"),
                ("DATE1", "2025-10-02", "DATE_TIME"),
            ],
        ),
        (
            "form_15",
            "0401(K) ROLLOVER DISTRIBUTION REQUEST\n"
            "Participant Name: {{NAME1}}\n"
            "Participant SSN: {{SSN1}} | Birth Date: {{DOB1}}\n"
            "Mailing Address: {{ADDR1}}\n"
            "Notification Email: {{EMAIL1}} | Daytime Telephone: {{PHONE1}}\n"
            "Distribution Settlement Date: {{DATE1}}",
            [
                ("NAME1", "Arthur P. Pendelton", "PERSON"),
                ("SSN1", "195-74-3210", "US_SSN"),
                ("DOB1", "January 29, 1963", "DATE_TIME"),
                ("ADDR1", "1801 Market Street, Philadelphia, PA 19103", "LOCATION"),
                ("EMAIL1", "arthur.pendelton@liberty-wealth.org", "EMAIL_ADDRESS"),
                ("PHONE1", "(215) 555-0160", "PHONE_NUMBER"),
                ("DATE1", "November 20, 2025", "DATE_TIME"),
            ],
        ),
        (
            "form_16",
            "MERCHANT ACCOUNT BENEFICIAL OWNERSHIP FORM\n"
            "Controlling Principal: {{NAME1}}\n"
            "Principal SSN: {{SSN1}} | Date of Birth: {{DOB1}}\n"
            "Principal Residence: {{ADDR1}}\n"
            "Compliance Email: {{EMAIL1}} | Principal Phone: {{PHONE1}}\n"
            "Certification Date: {{DATE1}}",
            [
                ("NAME1", "Tariq Al-Jamil", "PERSON"),
                ("SSN1", "479-33-6015", "US_SSN"),
                ("DOB1", "1978-08-08", "DATE_TIME"),
                ("ADDR1", "300 North LaSalle Street, Chicago, IL 60654", "LOCATION"),
                ("EMAIL1", "tariq@lakefront-payments.io", "EMAIL_ADDRESS"),
                ("PHONE1", "312-555-0122", "PHONE_NUMBER"),
                ("DATE1", "2025-04-30", "DATE_TIME"),
            ],
        ),
        (
            "form_17",
            "CONTINUING PROFESSIONAL EDUCATION (CPE) CREDIT RECORD\n"
            "Licensee Name: {{NAME1}} | SSN (last verified full): {{SSN1}}\n"
            "Chapter Location: {{ADDR1}}\n"
            "Registrant Email: {{EMAIL1}} | Phone: {{PHONE1}}\n"
            "Course Completion Date: {{DATE1}}\n"
            "Instructor: {{NAME2}}",
            [
                ("NAME1", "Clara M. Schoenfeld", "PERSON"),
                ("SSN1", "512-68-9471", "US_SSN"),
                ("ADDR1", "700 Nicollet Mall, Minneapolis, MN 55402", "LOCATION"),
                ("EMAIL1", "clara.schoenfeld@northstar-cpa.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(612) 555-0144", "PHONE_NUMBER"),
                ("DATE1", "September 9, 2025", "DATE_TIME"),
                ("NAME2", "Prof. Julian Mercer", "PERSON"),
            ],
        ),
        (
            "form_18",
            "EQUIPMENT CUSTODY & OFF-SITE USE AGREEMENT\n"
            "Custodian Employee: {{NAME1}} (SSN: {{SSN1}})\n"
            "Off-Site Remote Address: {{ADDR1}}\n"
            "Employee Email: {{EMAIL1}} | Contact Number: {{PHONE1}}\n"
            "Checkout Date: {{DATE1}} | Return Due Date: {{DATE2}}",
            [
                ("NAME1", "Zachary N. Takahashi", "PERSON"),
                ("SSN1", "623-47-2918", "US_SSN"),
                ("ADDR1", "1201 Third Avenue, Seattle, WA 98101", "LOCATION"),
                ("EMAIL1", "z.takahashi@rainier-robotics.com", "EMAIL_ADDRESS"),
                ("PHONE1", "206-555-0193", "PHONE_NUMBER"),
                ("DATE1", "2025-02-14", "DATE_TIME"),
                ("DATE2", "2025-08-14", "DATE_TIME"),
            ],
        ),
        (
            "form_19",
            "FIDUCIARY BOND APPLICATION FORM\n"
            "Applicant Trustee: {{NAME1}}\n"
            "Social Security Number: {{SSN1}} | Birthdate: {{DOB1}}\n"
            "Fiduciary Office Address: {{ADDR1}}\n"
            "Trustee Email: {{EMAIL1}} | Direct Phone: {{PHONE1}}\n"
            "Bond Effective Date: {{DATE1}}",
            [
                ("NAME1", "Eleanor V. Hawthorne", "PERSON"),
                ("SSN1", "245-89-7032", "US_SSN"),
                ("DOB1", "10/19/1971", "DATE_TIME"),
                ("ADDR1", "50 North Front Street, Memphis, TN 38103", "LOCATION"),
                ("EMAIL1", "ehawthorne@bluffcity-trust.org", "EMAIL_ADDRESS"),
                ("PHONE1", "(901) 555-0158", "PHONE_NUMBER"),
                ("DATE1", "June 1, 2025", "DATE_TIME"),
            ],
        ),
        (
            "form_20",
            "SEVERANCE & RELEASE ACKNOWLEDGMENT FORM\n"
            "Departing Employee: {{NAME1}} | SSN: {{SSN1}}\n"
            "Forwarding Postal Address: {{ADDR1}}\n"
            "Personal Email for Tax Forms: {{EMAIL1}}\n"
            "Personal Mobile: {{PHONE1}}\n"
            "Termination Date: {{DATE1}} | Signature Date: {{DATE2}}",
            [
                ("NAME1", "Malcolm D. Wainwright", "PERSON"),
                ("SSN1", "391-52-8640", "US_SSN"),
                ("ADDR1", "444 South Flower Street, Los Angeles, CA 90071", "LOCATION"),
                ("EMAIL1", "malcolm.wainwright@socal-mail.net", "EMAIL_ADDRESS"),
                ("PHONE1", "213-555-0171", "PHONE_NUMBER"),
                ("DATE1", "2025-11-30", "DATE_TIME"),
                ("DATE2", "2025-12-01", "DATE_TIME"),
            ],
        ),
    ]

    for doc_id, tmpl, flds in forms_data:
        docs.append(build_tagged_document(doc_id, "form", tmpl, flds))

    # 20 Synthetic Business Invoices
    invoices_data = [
        (
            "invoice_01",
            "INVOICE #INV-2025-8841\n"
            "Issue Date: {{DATE1}} | Due Date: {{DATE2}}\n"
            "Bill To: {{NAME1}}, Procurement Director\n"
            "Ship To Address: {{ADDR1}}\n"
            "Billing Contact Email: {{EMAIL1}} | Billing Phone: {{PHONE1}}\n"
            "Sole Proprietor Contractor Tax ID (SSN): {{SSN1}}\n"
            "Remit Questions To: {{NAME2}} ({{EMAIL2}})",
            [
                ("DATE1", "2025-03-10", "DATE_TIME"),
                ("DATE2", "2025-04-09", "DATE_TIME"),
                ("NAME1", "omnibus client — Lauren K. Whitman", "PERSON"),
                ("ADDR1", "1600 Market Street, Suite 1900, Philadelphia, PA 19103", "LOCATION"),
                ("EMAIL1", "l.whitman@keystone-manufacturing.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(215) 555-0181", "PHONE_NUMBER"),
                ("SSN1", "408-67-2319", "US_SSN"),
                ("NAME2", "Isaac M. Calderon", "PERSON"),
                ("EMAIL2", "icalderon@calderon-engineering.io", "EMAIL_ADDRESS"),
            ],
        ),
        (
            "invoice_02",
            "TAX INVOICE #90421\n"
            "Invoice Date: {{DATE1}}\n"
            "Client Attention: {{NAME1}}\n"
            "Delivery Site: {{ADDR1}}\n"
            "Client Email: {{EMAIL1}} | Client Phone: {{PHONE1}}\n"
            "Independent Consultant: {{NAME2}} | Consultant SSN: {{SSN1}}\n"
            "Payment Due By: {{DATE2}}",
            [
                ("DATE1", "July 18, 2025", "DATE_TIME"),
                ("NAME1", "Victor H. Castellanos", "PERSON"),
                ("ADDR1", "801 Grand Avenue, Des Moines, IA 50309", "LOCATION"),
                ("EMAIL1", "vcastellanos@heartland-agri.com", "EMAIL_ADDRESS"),
                ("PHONE1", "515-555-0146", "PHONE_NUMBER"),
                ("NAME2", "Nora J. Fitzpatrick", "PERSON"),
                ("SSN1", "501-39-7482", "US_SSN"),
                ("DATE2", "August 17, 2025", "DATE_TIME"),
            ],
        ),
        (
            "invoice_03",
            "PROFESSIONAL SERVICES STATEMENT #ST-4410\n"
            "Statement Date: {{DATE1}}\n"
            "Prepared For: {{NAME1}}\n"
            "Property Location: {{ADDR1}}\n"
            "Customer Email: {{EMAIL1}} | Customer Tel: {{PHONE1}}\n"
            "Licensed Surveyor: {{NAME2}} (1099 SSN: {{SSN1}})\n"
            "Field Inspection Date: {{DATE2}}",
            [
                ("DATE1", "2025-05-22", "DATE_TIME"),
                ("NAME1", "stephanie R. Alverez", "PERSON"),
                ("ADDR1", "250 West Pratt Street, Baltimore, MD 21201", "LOCATION"),
                ("EMAIL1", "salverez@harborview-realty.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(410) 555-0194", "PHONE_NUMBER"),
                ("NAME2", "Barton L. Riggs", "PERSON"),
                ("SSN1", "212-84-5930", "US_SSN"),
                ("DATE2", "2025-05-15", "DATE_TIME"),
            ],
        ),
        (
            "invoice_04",
            "COMMERCIAL FREIGHT BILL & INVOICE #FB-7729\n"
            "Dispatch Date: {{DATE1}} | Arrival Date: {{DATE2}}\n"
            "Consignee Contact: {{NAME1}}\n"
            "Warehouse Destination: {{ADDR1}}\n"
            "Origin Depot: {{ADDR2}}\n"
            "Consignee Email: {{EMAIL1}} | Dock Phone: {{PHONE1}}\n"
            "Owner-Operator Carrier SSN: {{SSN1}}",
            [
                ("DATE1", "October 1, 2025", "DATE_TIME"),
                ("DATE2", "October 4, 2025", "DATE_TIME"),
                ("NAME1", "Leonard P. Vance", "PERSON"),
                ("ADDR1", "1500 Marilla Street, Dallas, TX 75201", "LOCATION"),
                ("ADDR2", "333 West Wacker Drive, Chicago, IL 60606", "LOCATION"),
                ("EMAIL1", "lvance@lonestar-distribution.net", "EMAIL_ADDRESS"),
                ("PHONE1", "214-555-0133", "PHONE_NUMBER"),
                ("SSN1", "463-71-9024", "US_SSN"),
            ],
        ),
        (
            "invoice_05",
            "LEGAL DISBURSEMENT & EXPERT WITNESS INVOICE #EW-309\n"
            "Billing Date: {{DATE1}}\n"
            "Matter Counsel: {{NAME1}}\n"
            "Law Firm Address: {{ADDR1}}\n"
            "Counsel Email: {{EMAIL1}} | Office Phone: {{PHONE1}}\n"
            "Expert Witness: {{NAME2}} | W-9 SSN: {{SSN1}}\n"
            "Deposition Date Billed: {{DATE2}}",
            [
                ("DATE1", "2025-08-19", "DATE_TIME"),
                ("NAME1", "Jonathan E. Vance-Sterling", "PERSON"),
                ("ADDR1", "555 California Street, Suite 3100, San Francisco, CA 94104", "LOCATION"),
                ("EMAIL1", "jsterling@bayarea-litigation.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(415) 555-0179", "PHONE_NUMBER"),
                ("NAME2", "Dr. Helena K. Rostova", "PERSON"),
                ("SSN1", "566-20-4813", "US_SSN"),
                ("DATE2", "2025-08-05", "DATE_TIME"),
            ],
        ),
        (
            "invoice_06",
            "IT INFRASTRUCTURE AUDIT INVOICE #INV-6102\n"
            "Date Issued: {{DATE1}}\n"
            "Authorized By: {{NAME1}}\n"
            "Data Center Audited: {{ADDR1}}\n"
            "Approver Email: {{EMAIL1}} | Approver Direct Line: {{PHONE1}}\n"
            "Lead Contractor: {{NAME2}} (Tax SSN: {{SSN1}})",
            [
                ("DATE1", "11/12/2025", "DATE_TIME"),
                ("NAME1", "Gavin M. Thornhill", "PERSON"),
                ("ADDR1", "191 Peachtree Street NE, Atlanta, GA 30303", "LOCATION"),
                ("EMAIL1", "g.thornhill@piedmont-health-sys.org", "EMAIL_ADDRESS"),
                ("PHONE1", "404-555-0126", "PHONE_NUMBER"),
                ("NAME2", "Rajesh V. Kulkarni", "PERSON"),
                ("SSN1", "259-93-6174", "US_SSN"),
            ],
        ),
        (
            "invoice_07",
            "ARCHITECTURAL DESIGN PROGRESS BILLING #PB-118\n"
            "Billing Period Ending: {{DATE1}}\n"
            "Project Owner Representative: {{NAME1}}\n"
            "Site Address: {{ADDR1}}\n"
            "Owner Email: {{EMAIL1}} | Site Phone: {{PHONE1}}\n"
            "Principal Architect (Sole Prop SSN): {{SSN1}}",
            [
                ("DATE1", "June 30, 2025", "DATE_TIME"),
                ("NAME1", "Simone A. Devereaux", "PERSON"),
                ("ADDR1", "701 Brickell Avenue, Miami, FL 33131", "LOCATION"),
                ("EMAIL1", "sdevereaux@biscayne-developments.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(305) 555-0191", "PHONE_NUMBER"),
                ("SSN1", "589-42-3019", "US_SSN"),
            ],
        ),
        (
            "invoice_08",
            "MEDICAL EQUIPMENT CALIBRATION INVOICE #CAL-5520\n"
            "Service Date: {{DATE1}} | Invoice Date: {{DATE2}}\n"
            "Clinic Manager: {{NAME1}}\n"
            "Clinic Address: {{ADDR1}}\n"
            "Manager Email: {{EMAIL1}} | Clinic Phone: {{PHONE1}}\n"
            "Field Technician: {{NAME2}} (1099 SSN: {{SSN1}})",
            [
                ("DATE1", "2025-09-03", "DATE_TIME"),
                ("DATE2", "2025-09-05", "DATE_TIME"),
                ("NAME1", "Patricia L. Halvorsen", "PERSON"),
                ("ADDR1", "3600 Forbes Avenue, Pittsburgh, PA 15213", "LOCATION"),
                ("EMAIL1", "phalvorsen@allegheny-diagnostics.org", "EMAIL_ADDRESS"),
                ("PHONE1", "412-555-0164", "PHONE_NUMBER"),
                ("NAME2", "Curtis W. Albright", "PERSON"),
                ("SSN1", "178-56-8920", "US_SSN"),
            ],
        ),
        (
            "invoice_09",
            "EXECUTIVE COACHING & TRAINING INVOICE #EC-204\n"
            "Invoice Date: {{DATE1}}\n"
            "Sponsoring VP: {{NAME1}}\n"
            "Regional Headquarters: {{ADDR1}}\n"
            "Sponsor Email: {{EMAIL1}} | Sponsor Tel: {{PHONE1}}\n"
            "Coach Payee: {{NAME2}} | Payee SSN: {{SSN1}}",
            [
                ("DATE1", "February 28, 2025", "DATE_TIME"),
                ("NAME1", "Dominic F. Santoro", "PERSON"),
                ("ADDR1", "100 Federal Street, Boston, MA 02110", "LOCATION"),
                ("EMAIL1", "dsantoro@atlantic-assurance.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(617) 555-0185", "PHONE_NUMBER"),
                ("NAME2", "Dr. Camille Beauchamp", "PERSON"),
                ("SSN1", "024-78-5143", "US_SSN"),
            ],
        ),
        (
            "invoice_10",
            "ENVIRONMENTAL SITE ASSESSMENT INVOICE #ESA-890\n"
            "Assessment Date: {{DATE1}}\n"
            "Client Contact: {{NAME1}}\n"
            "Inspected Parcel: {{ADDR1}}\n"
            "Client Email: {{EMAIL1}} | Contact Phone: {{PHONE1}}\n"
            "Certifying Geologist SSN: {{SSN1}}",
            [
                ("DATE1", "2025-04-14", "DATE_TIME"),
                ("NAME1", "Wesley G. McBride", "PERSON"),
                ("ADDR1", "401 North Michigan Avenue, Chicago, IL 60611", "LOCATION"),
                ("EMAIL1", "wmcbride@midwest-industrial-reit.com", "EMAIL_ADDRESS"),
                ("PHONE1", "312-555-0150", "PHONE_NUMBER"),
                ("SSN1", "339-61-2847", "US_SSN"),
            ],
        ),
        (
            "invoice_11",
            "TRANSLATION & LOCALIZATION VENDOR INVOICE #TL-412\n"
            "Submitted On: {{DATE1}} | Net 30 Due: {{DATE2}}\n"
            "Localization PM: {{NAME1}}\n"
            "Office Address: {{ADDR1}}\n"
            "PM Email: {{EMAIL1}} | Phone: {{PHONE1}}\n"
            "Freelance Translator: {{NAME2}} (SSN: {{SSN1}})",
            [
                ("DATE1", "2025-06-01", "DATE_TIME"),
                ("DATE2", "2025-07-01", "DATE_TIME"),
                ("NAME1", "Anastasia V. Morozova", "PERSON"),
                ("ADDR1", "101 California Street, San Francisco, CA 94111", "LOCATION"),
                ("EMAIL1", "amorozova@global-saas-docs.io", "EMAIL_ADDRESS"),
                ("PHONE1", "(415) 555-0118", "PHONE_NUMBER"),
                ("NAME2", "Jean-Luc Picard-Valois", "PERSON"),
                ("SSN1", "552-19-8374", "US_SSN"),
            ],
        ),
        (
            "invoice_12",
            "HVAC COMMERCIAL RETROFIT INVOICE #HV-993\n"
            "Completion Date: {{DATE1}}\n"
            "Facilities Director: {{NAME1}}\n"
            "Building Address: {{ADDR1}}\n"
            "Facilities Email: {{EMAIL1}} | Emergency Line: {{PHONE1}}\n"
            "Subcontractor Sole Prop SSN: {{SSN1}}",
            [
                ("DATE1", "August 22, 2025", "DATE_TIME"),
                ("NAME1", "Hector R. Dominguez", "PERSON"),
                ("ADDR1", "2 North Central Avenue, Phoenix, AZ 85004", "LOCATION"),
                ("EMAIL1", "hdominguez@sonoran-properties.com", "EMAIL_ADDRESS"),
                ("PHONE1", "602-555-0172", "PHONE_NUMBER"),
                ("SSN1", "527-83-1904", "US_SSN"),
            ],
        ),
        (
            "invoice_13",
            "FORENSIC ACCOUNTING ENGAGEMENT BILL #FA-715\n"
            "Invoice Date: {{DATE1}}\n"
            "Audit Committee Chair: {{NAME1}}\n"
            "Corporate Address: {{ADDR1}}\n"
            "Chair Email: {{EMAIL1}} | Direct Phone: {{PHONE1}}\n"
            "Examiner: {{NAME2}} | Tax Reporting SSN: {{SSN1}}",
            [
                ("DATE1", "2025-10-27", "DATE_TIME"),
                ("NAME1", "Margaret T. O'Sullivan", "PERSON"),
                ("ADDR1", "120 Broadway, New York, NY 10271", "LOCATION"),
                ("EMAIL1", "mosullivan@wallstreet-governance.org", "EMAIL_ADDRESS"),
                ("PHONE1", "(212) 555-0136", "PHONE_NUMBER"),
                ("NAME2", "Philip K. Rosen", "PERSON"),
                ("SSN1", "089-45-6721", "US_SSN"),
            ],
        ),
        (
            "invoice_14",
            "CORPORATE PHOTOGRAPHY & MEDIA INVOICE #PM-330\n"
            "Event Date: {{DATE1}} | Billed Date: {{DATE2}}\n"
            "Communications Lead: {{NAME1}}\n"
            "Venue Location: {{ADDR1}}\n"
            "Client Email: {{EMAIL1}} | Mobile: {{PHONE1}}\n"
            "Photographer Sole Proprietor SSN: {{SSN1}}",
            [
                ("DATE1", "May 14, 2025", "DATE_TIME"),
                ("DATE2", "May 19, 2025", "DATE_TIME"),
                ("NAME1", "Chloe E. Abernathy", "PERSON"),
                ("ADDR1", "600 East Grand Avenue, Chicago, IL 60611", "LOCATION"),
                ("EMAIL1", "chloe.abernathy@lakeshore-events.com", "EMAIL_ADDRESS"),
                ("PHONE1", "312-555-0196", "PHONE_NUMBER"),
                ("SSN1", "345-90-2186", "US_SSN"),
            ],
        ),
        (
            "invoice_15",
            "ACTUARIAL VALUATION SERVICES INVOICE #AV-2025-19\n"
            "Valuation Date: {{DATE1}}\n"
            "Plan Administrator: {{NAME1}}\n"
            "Plan Office: {{ADDR1}}\n"
            "Administrator Email: {{EMAIL1}} | Telephone: {{PHONE1}}\n"
            "Signing Actuary: {{NAME2}} (SSN: {{SSN1}})",
            [
                ("DATE1", "2025-12-15", "DATE_TIME"),
                ("NAME1", "gerald W. Fitzwilliam", "PERSON"),
                ("ADDR1", "777 East Wisconsin Avenue, Milwaukee, WI 53202", "LOCATION"),
                ("EMAIL1", "gfitzwilliam@badger-pension-fund.org", "EMAIL_ADDRESS"),
                ("PHONE1", "(414) 555-0128", "PHONE_NUMBER"),
                ("NAME2", "Sylvia N. Chen", "PERSON"),
                ("SSN1", "398-24-7510", "US_SSN"),
            ],
        ),
        (
            "invoice_16",
            "PENETRATION TESTING RETAINER INVOICE #PT-808\n"
            "Engagement Window: {{DATE1}} to {{DATE2}}\n"
            "CISO Contact: {{NAME1}}\n"
            "HQ Location: {{ADDR1}}\n"
            "CISO Email: {{EMAIL1}} | CISO Phone: {{PHONE1}}\n"
            "Independent Researcher W-9 SSN: {{SSN1}}",
            [
                ("DATE1", "2025-07-07", "DATE_TIME"),
                ("DATE2", "2025-07-21", "DATE_TIME"),
                ("NAME1", "Marcus A. Vance-Kerr", "PERSON"),
                ("ADDR1", "1100 Peachtree Street NE, Atlanta, GA 30309", "LOCATION"),
                ("EMAIL1", "mvancekerr@southern-fintech.io", "EMAIL_ADDRESS"),
                ("PHONE1", "404-555-0149", "PHONE_NUMBER"),
                ("SSN1", "254-67-9381", "US_SSN"),
            ],
        ),
        (
            "invoice_17",
            "SUPPLY CHAIN CUSTOMS BROKERAGE STATEMENT #CB-514\n"
            "Entry Date: {{DATE1}}\n"
            "Importer of Record Representative: {{NAME1}}\n"
            "Port Warehouse Address: {{ADDR1}}\n"
            "Representative Email: {{EMAIL1}} | Phone: {{PHONE1}}\n"
            "Individual Broker License SSN: {{SSN1}}",
            [
                ("DATE1", "March 29, 2025", "DATE_TIME"),
                ("NAME1", "Keiko T. Watanabe", "PERSON"),
                ("ADDR1", "444 West Ocean Boulevard, Long Beach, CA 90802", "LOCATION"),
                ("EMAIL1", "kwatanabe@pacific-harbor-imports.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(562) 555-0167", "PHONE_NUMBER"),
                ("SSN1", "561-73-4092", "US_SSN"),
            ],
        ),
        (
            "invoice_18",
            "CLINICAL TRIAL BIOSTATISTICS INVOICE #CT-604\n"
            "Invoice Date: {{DATE1}}\n"
            "Study Director: {{NAME1}}\n"
            "Research Institute Address: {{ADDR1}}\n"
            "Director Email: {{EMAIL1}} | Office Line: {{PHONE1}}\n"
            "Biostatistician Contractor: {{NAME2}} (SSN: {{SSN1}})",
            [
                ("DATE1", "2025-11-05", "DATE_TIME"),
                ("NAME1", "Dr. Alistair M. Finch", "PERSON"),
                ("ADDR1", "650 Huntington Avenue, Boston, MA 02115", "LOCATION"),
                ("EMAIL1", "afinch@longwood-clinical-trials.org", "EMAIL_ADDRESS"),
                ("PHONE1", "617-555-0152", "PHONE_NUMBER"),
                ("NAME2", "Yael Ben-David", "PERSON"),
                ("SSN1", "031-88-4625", "US_SSN"),
            ],
        ),
        (
            "invoice_19",
            "INDUSTRIAL SAFETY TRAINING INVOICE #ST-219\n"
            "Training Session Date: {{DATE1}}\n"
            "Plant Operations Manager: {{NAME1}}\n"
            "Plant Address: {{ADDR1}}\n"
            "Manager Email: {{EMAIL1}} | Plant Phone: {{PHONE1}}\n"
            "Certified Trainer SSN: {{SSN1}}",
            [
                ("DATE1", "September 25, 2025", "DATE_TIME"),
                ("NAME1", "Russell D. Carmichael", "PERSON"),
                ("ADDR1", "500 Woodward Avenue, Detroit, MI 48226", "LOCATION"),
                ("EMAIL1", "rcarmichael@greatlakes-stamping.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(313) 555-0183", "PHONE_NUMBER"),
                ("SSN1", "372-49-1058", "US_SSN"),
            ],
        ),
        (
            "invoice_20",
            "RENEWABLE ENERGY FEASIBILITY STUDY INVOICE #RE-107\n"
            "Issued: {{DATE1}} | Due: {{DATE2}}\n"
            "Development Director: {{NAME1}}\n"
            "Project Office: {{ADDR1}}\n"
            "Contact Email: {{EMAIL1}} | Contact Tel: {{PHONE1}}\n"
            "Lead Electrical Engineer (Sole Prop SSN): {{SSN1}}",
            [
                ("DATE1", "2025-08-01", "DATE_TIME"),
                ("DATE2", "2025-08-31", "DATE_TIME"),
                ("NAME1", "Brianna S. Okafor", "PERSON"),
                ("ADDR1", "1700 Broadway, Suite 1400, Denver, CO 80290", "LOCATION"),
                ("EMAIL1", "bokafor@frontrange-solar.io", "EMAIL_ADDRESS"),
                ("PHONE1", "303-555-0178", "PHONE_NUMBER"),
                ("SSN1", "521-36-9841", "US_SSN"),
            ],
        ),
    ]

    for doc_id, tmpl, flds in invoices_data:
        docs.append(build_tagged_document(doc_id, "invoice", tmpl, flds))

    # 20 Synthetic Business Correspondence Emails / Letters
    correspondence_data = [
        (
            "corr_01",
            "Subject: Urgent Payroll Tax Correction — Q3 Filing\n"
            "Date: {{DATE1}}\n"
            "From: {{NAME1}} <{{EMAIL1}}>\n"
            "To: {{NAME2}} <{{EMAIL2}}>\n\n"
            "Hi {{NAME3}},\n"
            "During our internal audit at the {{ADDR1}} office, we noticed that new hire "
            "{{NAME4}} (born {{DOB1}}) had a transposed Social Security Number recorded as "
            "{{SSN1}}. Please update the W-2 master file before {{DATE2}} and call me at "
            "{{PHONE1}} once confirmed.",
            [
                ("DATE1", "October 16, 2025", "DATE_TIME"),
                ("NAME1", "Sandra M. Peltier", "PERSON"),
                ("EMAIL1", "speltier@meridian-corp.com", "EMAIL_ADDRESS"),
                ("NAME2", "David K. Cho", "PERSON"),
                ("EMAIL2", "dcho@meridian-corp.com", "EMAIL_ADDRESS"),
                ("NAME3", "David", "PERSON"),
                ("ADDR1", "1001 Fourth Avenue, Seattle, WA 98154", "LOCATION"),
                ("NAME4", "Julian R. Vance", "PERSON"),
                ("DOB1", "1993-06-14", "DATE_TIME"),
                ("SSN1", "534-29-8810", "US_SSN"),
                ("DATE2", "October 20, 2025", "DATE_TIME"),
                ("PHONE1", "(206) 555-0162", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_02",
            "MEMORANDUM — ESCROW DISBURSEMENT AUTHORIZATION\n"
            "Date: {{DATE1}}\n"
            "Dear {{NAME1}},\n"
            "This letter authorizes the release of earnest money for the commercial parcel at "
            "{{ADDR1}}. The individual guarantor is {{NAME2}} (SSN {{SSN1}}, DOB {{DOB1}}). "
            "Signed closing documents may be emailed to {{EMAIL1}} or confirmed by phone at "
            "{{PHONE1}} no later than {{DATE2}}.",
            [
                ("DATE1", "2025-05-09", "DATE_TIME"),
                ("NAME1", "Caroline V. Mercer", "PERSON"),
                ("ADDR1", "2300 North Central Expressway, Plano, TX 75074", "LOCATION"),
                ("NAME2", "Harrison B. Langford", "PERSON"),
                ("SSN1", "449-81-2065", "US_SSN"),
                ("DOB1", "11/02/1974", "DATE_TIME"),
                ("EMAIL1", "hlangford@dfw-holdings.com", "EMAIL_ADDRESS"),
                ("PHONE1", "972-555-0147", "PHONE_NUMBER"),
                ("DATE2", "2025-05-15", "DATE_TIME"),
            ],
        ),
        (
            "corr_03",
            "From: {{NAME1}} ({{EMAIL1}})\n"
            "Sent: {{DATE1}}\n"
            "Subject: Background Check Clearance for Contractor Onboarding\n\n"
            "Team,\n"
            "We have completed vetting for {{NAME2}}, who will report to our {{ADDR1}} branch "
            "starting {{DATE2}}. For the security badge badge-office file: SSN is {{SSN1}} and "
            "emergency contact phone is {{PHONE1}}.",
            [
                ("NAME1", " Monica L. Delgado", "PERSON"),
                ("EMAIL1", "mdelgado@apex-systems-sec.com", "EMAIL_ADDRESS"),
                ("DATE1", "September 2, 2025", "DATE_TIME"),
                ("NAME2", "Nathaniel S. Brooks", "PERSON"),
                ("ADDR1", "1750 Tysons Boulevard, McLean, VA 22102", "LOCATION"),
                ("DATE2", "September 8, 2025", "DATE_TIME"),
                ("SSN1", "228-54-9103", "US_SSN"),
                ("PHONE1", "(703) 555-0190", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_04",
            "RE: Executive Life Insurance Underwriting File\n"
            "Date: {{DATE1}}\n"
            "Dear {{NAME1}},\n"
            "Attached is the key-person policy schedule for {{NAME2}}, residing at {{ADDR1}}. "
            "Please verify the insured's date of birth ({{DOB1}}) and Social Security Number "
            "({{SSN1}}). Reach out to {{EMAIL1}} or {{PHONE1}} with any underwriting questions.",
            [
                ("DATE1", "2025-07-28", "DATE_TIME"),
                ("NAME1", "Thomas G. Abercrombie", "PERSON"),
                ("NAME2", "Victoria L. Sterling", "PERSON"),
                ("ADDR1", "888 Boylston Street, Boston, MA 02199", "LOCATION"),
                ("DOB1", "March 3, 1972", "DATE_TIME"),
                ("SSN1", "019-63-7452", "US_SSN"),
                ("EMAIL1", "vsterling@newengland-biomed.com", "EMAIL_ADDRESS"),
                ("PHONE1", "617-555-0131", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_05",
            "Subject: Subpoena Compliance & Custodian Record Verification\n"
            "Date: {{DATE1}}\n"
            "Counsel {{NAME1}},\n"
            "Per the request served at {{ADDR1}} on {{DATE2}}, the former regional manager is "
            "{{NAME2}} (SSN: {{SSN1}}). Last known email on file is {{EMAIL1}} and telephone is "
            "{{PHONE1}}.",
            [
                ("DATE1", "November 14, 2025", "DATE_TIME"),
                ("NAME1", "Rachel A. Bernstein", "PERSON"),
                ("ADDR1", "30 Hudson Yards, New York, NY 10001", "LOCATION"),
                ("DATE2", "November 1, 2025", "DATE_TIME"),
                ("NAME2", "Douglas M. Callahan", "PERSON"),
                ("SSN1", "114-79-3028", "US_SSN"),
                ("EMAIL1", "dcallahan77@manhattan-mail.org", "EMAIL_ADDRESS"),
                ("PHONE1", "(212) 555-0145", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_06",
            "LETTER OF ENGAGEMENT — TAX CONTROVERSY REPRESENTATION\n"
            "Date: {{DATE1}}\n"
            "Client: {{NAME1}} | SSN: {{SSN1}}\n"
            "Residence: {{ADDR1}}\n\n"
            "Dear {{NAME2}},\n"
            "We confirm our representation before the IRS Appeals Office for tax year ending "
            "{{DATE2}}. We will send draft filings to {{EMAIL1}} and reach you by phone at "
            "{{PHONE1}}.",
            [
                ("DATE1", "January 22, 2026", "DATE_TIME"),
                ("NAME1", "Lawrence E. Kemp", "PERSON"),
                ("SSN1", "481-35-6290", "US_SSN"),
                ("ADDR1", "3200 Southwest Freeway, Houston, TX 77027", "LOCATION"),
                ("NAME2", "Mr. Kemp", "PERSON"),
                ("DATE2", "December 31, 2024", "DATE_TIME"),
                ("EMAIL1", "lkemp@bayou-energy-partners.com", "EMAIL_ADDRESS"),
                ("PHONE1", "713-555-0189", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_07",
            "Subject: Estate Pension Survivor Benefit Claim\n"
            "Date: {{DATE1}}\n"
            "To Benefits Committee:\n"
            "Claimant {{NAME1}} (SSN {{SSN1}}, DOB {{DOB1}}), residing at {{ADDR1}}, has "
            "submitted survivor documentation following the retirement of {{NAME2}} on "
            "{{DATE2}}. Contact claimant via {{EMAIL1}} or {{PHONE1}}.",
            [
                ("DATE1", "2025-04-03", "DATE_TIME"),
                ("NAME1", "Martha J. Kowalczyk", "PERSON"),
                ("SSN1", "329-48-7105", "US_SSN"),
                ("DOB1", "1959-09-12", "DATE_TIME"),
                ("ADDR1", "200 Public Square, Cleveland, OH 44114", "LOCATION"),
                ("NAME2", "Stanley P. Kowalczyk", "PERSON"),
                ("DATE2", "2025-01-31", "DATE_TIME"),
                ("EMAIL1", "mkowalczyk@erie-family.net", "EMAIL_ADDRESS"),
                ("PHONE1", "(216) 555-0173", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_08",
            "Subject: H-1B / L-1 Corporate Transfer Dossier\n"
            "Date: {{DATE1}}\n"
            "Mobility Team,\n"
            "Assignee {{NAME1}} (US SSN {{SSN1}}, born {{DOB1}}) is relocating to our "
            "{{ADDR1}} engineering hub on {{DATE2}}. Please send housing lease packets to "
            "{{EMAIL1}} or call {{PHONE1}}.",
            [
                ("DATE1", "August 11, 2025", "DATE_TIME"),
                ("NAME1", "Rohan S. Deshmukh", "PERSON"),
                ("SSN1", "610-44-2981", "US_SSN"),
                ("DOB1", "1992-01-25", "DATE_TIME"),
                ("ADDR1", "500 West 2nd Street, Austin, TX 78701", "LOCATION"),
                ("DATE2", "September 15, 2025", "DATE_TIME"),
                ("EMAIL1", "rohan.deshmukh@siliconhills-ai.com", "EMAIL_ADDRESS"),
                ("PHONE1", "512-555-0166", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_09",
            "NOTICE OF MECHANIC'S LIEN RELEASE\n"
            "Recorded Date: {{DATE1}}\n"
            "Property Owner: {{NAME1}}\n"
            "Subject Property: {{ADDR1}}\n"
            "Individual Claimant: {{NAME2}} (Taxpayer SSN: {{SSN1}})\n"
            "Release inquiries may be directed to {{EMAIL1}} or {{PHONE1}} before {{DATE2}}.",
            [
                ("DATE1", "2025-10-08", "DATE_TIME"),
                ("NAME1", "Preston W. Vance", "PERSON"),
                ("ADDR1", "1401 Lawrence Street, Denver, CO 80202", "LOCATION"),
                ("NAME2", "Garrett L. Boone", "PERSON"),
                ("SSN1", "507-62-8419", "US_SSN"),
                ("EMAIL1", "gboone@milehigh-masonry.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(303) 555-0124", "PHONE_NUMBER"),
                ("DATE2", "2025-10-31", "DATE_TIME"),
            ],
        ),
        (
            "corr_10",
            "Subject: Board Director KYC Refresh — Annual Banking Audit\n"
            "Date: {{DATE1}}\n"
            "Dear {{NAME1}},\n"
            "Our commercial lender requires updated KYC details for directors before {{DATE2}}. "
            "We have your residential address as {{ADDR1}}, DOB as {{DOB1}}, and SSN as "
            "{{SSN1}}. Please confirm via {{EMAIL1}} or call me at {{PHONE1}}.",
            [
                ("DATE1", "June 17, 2025", "DATE_TIME"),
                ("NAME1", "Dr. Evelyn H. Sterling-Wu", "PERSON"),
                ("DATE2", "June 25, 2025", "DATE_TIME"),
                ("ADDR1", "633 West Fifth Street, Los Angeles, CA 90071", "LOCATION"),
                ("DOB1", "04/05/1969", "DATE_TIME"),
                ("SSN1", "543-91-7026", "US_SSN"),
                ("EMAIL1", "esterlingwu@pacific-board-advisors.org", "EMAIL_ADDRESS"),
                ("PHONE1", "213-555-0154", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_11",
            "Subject: Independent Contractor 1099-NEC Backup Withholding Notice\n"
            "Date: {{DATE1}}\n"
            "To: {{NAME1}} ({{EMAIL1}})\n"
            "We received a CP2100A notice regarding TIN/SSN {{SSN1}} associated with your "
            "account at {{ADDR1}}. Please return a signed W-9 by {{DATE2}} or contact AP at "
            "{{PHONE1}}.",
            [
                ("DATE1", "2025-11-18", "DATE_TIME"),
                ("NAME1", " Terrence J. McAllister", "PERSON"),
                ("EMAIL1", "tmcallister@bluegrass-freight.net", "EMAIL_ADDRESS"),
                ("SSN1", "402-58-1934", "US_SSN"),
                ("ADDR1", "400 West Market Street, Louisville, KY 40202", "LOCATION"),
                ("DATE2", "2025-12-05", "DATE_TIME"),
                ("PHONE1", "(502) 555-0180", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_12",
            "CONFIDENTIAL SETTLEMENT DISBURSEMENT MEMO\n"
            "Date: {{DATE1}}\n"
            "Payee: {{NAME1}} (SSN: {{SSN1}}, DOB: {{DOB1}})\n"
            "Delivery Address: {{ADDR1}}\n"
            "Counsel of Record: {{NAME2}} ({{EMAIL1}}, {{PHONE1}})\n"
            "Wire Execution Target Date: {{DATE2}}",
            [
                ("DATE1", "March 12, 2025", "DATE_TIME"),
                ("NAME1", "Brenda K. Loughton", "PERSON"),
                ("SSN1", "291-73-4608", "US_SSN"),
                ("DOB1", "1980-10-30", "DATE_TIME"),
                ("ADDR1", "41 South High Street, Columbus, OH 43215", "LOCATION"),
                ("NAME2", "Alan R. Shapiro", "PERSON"),
                ("EMAIL1", "ashapiro@midwest-employment-law.com", "EMAIL_ADDRESS"),
                ("PHONE1", "614-555-0137", "PHONE_NUMBER"),
                ("DATE2", "March 20, 2025", "DATE_TIME"),
            ],
        ),
        (
            "corr_13",
            "Subject: Stock Option Exercise & 83(b) Election Filing\n"
            "Date: {{DATE1}}\n"
            "Hi {{NAME1}},\n"
            "Please find enclosed the Section 83(b) election for {{NAME2}} (SSN {{SSN1}}), "
            "residing at {{ADDR1}}. The grant date was {{DATE2}}. Confirm receipt to "
            "{{EMAIL1}} or {{PHONE1}}.",
            [
                ("DATE1", "2025-02-10", "DATE_TIME"),
                ("NAME1", "Paulette M. Girard", "PERSON"),
                ("NAME2", "Kevin Z. Chu", "PERSON"),
                ("SSN1", "577-84-3192", "US_SSN"),
                ("ADDR1", "275 Battery Street, San Francisco, CA 94111", "LOCATION"),
                ("DATE2", "2025-01-20", "DATE_TIME"),
                ("EMAIL1", "kchu@presidio-labs.io", "EMAIL_ADDRESS"),
                ("PHONE1", "(415) 555-0169", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_14",
            "Subject: Workers' Compensation Medical Release Follow-Up\n"
            "Date: {{DATE1}}\n"
            "Adjuster {{NAME1}},\n"
            "Regarding employee {{NAME2}} (DOB {{DOB1}}, SSN {{SSN1}}) injured at the "
            "{{ADDR1}} warehouse on {{DATE2}}: updated clearance notes can be sent to "
            "{{EMAIL1}} or discussed at {{PHONE1}}.",
            [
                ("DATE1", "July 9, 2025", "DATE_TIME"),
                ("NAME1", "craig T. Donovan", "PERSON"),
                ("NAME2", "Luis A. Mendoza", "PERSON"),
                ("DOB1", "12/15/1988", "DATE_TIME"),
                ("SSN1", "584-39-2071", "US_SSN"),
                ("ADDR1", "100 North Tampa Street, Tampa, FL 33602", "LOCATION"),
                ("DATE2", "June 28, 2025", "DATE_TIME"),
                ("EMAIL1", "lmendoza@gulfbay-warehousing.com", "EMAIL_ADDRESS"),
                ("PHONE1", "813-555-0142", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_15",
            "LETTER OF GUARANTY — EQUIPMENT FINANCING\n"
            "Date: {{DATE1}}\n"
            "Lender Attention: {{NAME1}}\n"
            "Personal Guarantor: {{NAME2}} (SSN: {{SSN1}}, DOB: {{DOB1}})\n"
            "Guarantor Address: {{ADDR1}}\n"
            "Guarantor Email: {{EMAIL1}} | Guarantor Phone: {{PHONE1}}",
            [
                ("DATE1", "2025-09-14", "DATE_TIME"),
                ("NAME1", "Rebecca S. Lin", "PERSON"),
                ("NAME2", "Walter H. Bruckner", "PERSON"),
                ("SSN1", "360-92-5418", "US_SSN"),
                ("DOB1", "1970-05-21", "DATE_TIME"),
                ("ADDR1", "101 South Tryon Street, Charlotte, NC 28280", "LOCATION"),
                ("EMAIL1", "wbruckner@carolina-precision-tooling.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(704) 555-0197", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_16",
            "Subject: Expatriate Tax Equalization Summary\n"
            "Date: {{DATE1}}\n"
            "Dear {{NAME1}},\n"
            "For your assignment between {{ADDR1}} and {{ADDR2}} starting {{DATE2}}, our tax "
            "team recorded your US SSN as {{SSN1}}. Please reply to {{EMAIL1}} or call "
            "{{PHONE1}} if any dependent details changed.",
            [
                ("DATE1", "April 25, 2025", "DATE_TIME"),
                ("NAME1", "Henrik J. Lindstrom", "PERSON"),
                ("ADDR1", "200 West Madison Street, Chicago, IL 60606", "LOCATION"),
                ("ADDR2", "1 Canada Square, Canary Wharf, London", "LOCATION"),
                ("DATE2", "May 1, 2025", "DATE_TIME"),
                ("SSN1", "319-46-8832", "US_SSN"),
                ("EMAIL1", "hlindstrom@nordic-midwest-capital.com", "EMAIL_ADDRESS"),
                ("PHONE1", "312-555-0161", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_17",
            "Subject: Commercial Mortgage Underwriting Exception Approval\n"
            "Date: {{DATE1}}\n"
            "Underwriting Committee,\n"
            "Sponsor {{NAME1}} (SSN {{SSN1}}, DOB {{DOB1}}) has pledged the property at "
            "{{ADDR1}} for closing on {{DATE2}}. Broker contact is {{NAME2}} at {{EMAIL1}} / "
            "{{PHONE1}}.",
            [
                ("DATE1", "2025-12-03", "DATE_TIME"),
                ("NAME1", "Devon R. Blakely", "PERSON"),
                ("SSN1", "495-71-6039", "US_SSN"),
                ("DOB1", "08/19/1976", "DATE_TIME"),
                ("ADDR1", "1200 Seventeenth Street, Denver, CO 80202", "LOCATION"),
                ("DATE2", "2025-12-22", "DATE_TIME"),
                ("NAME2", "Felicia M. Torres", "PERSON"),
                ("EMAIL1", "ftorres@summit-commercial-capital.com", "EMAIL_ADDRESS"),
                ("PHONE1", "(303) 555-0138", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_18",
            "Subject: Audit Confirmation — Officer Loan Account\n"
            "Date: {{DATE1}}\n"
            "To External Auditors:\n"
            "We confirm that corporate officer {{NAME1}} (SSN {{SSN1}}), residing at {{ADDR1}}, "
            "repaid the promissory note in full on {{DATE2}}. Direct verification questions to "
            "{{EMAIL1}} or {{PHONE1}}.",
            [
                ("DATE1", "January 19, 2026", "DATE_TIME"),
                ("NAME1", "Leonard C. Ashworth", "PERSON"),
                ("SSN1", "267-85-3910", "US_SSN"),
                ("ADDR1", "201 East Kennedy Boulevard, Tampa, FL 33602", "LOCATION"),
                ("DATE2", "December 29, 2025", "DATE_TIME"),
                ("EMAIL1", "lashworth@suncoast-maritime.com", "EMAIL_ADDRESS"),
                ("PHONE1", "813-555-0175", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_19",
            "Subject: COBRA Continuation Coverage Election Notice\n"
            "Date: {{DATE1}}\n"
            "Qualifying Beneficiary: {{NAME1}} (SSN: {{SSN1}}, DOB: {{DOB1}})\n"
            "Mailing Address: {{ADDR1}}\n"
            "Coverage Qualifying Event Date: {{DATE2}}\n"
            "Questions: email {{EMAIL1}} or call Benefits Administration at {{PHONE1}}.",
            [
                ("DATE1", "2025-08-06", "DATE_TIME"),
                ("NAME1", "Sabrina L. Vane", "PERSON"),
                ("SSN1", "158-42-9076", "US_SSN"),
                ("DOB1", "1989-02-11", "DATE_TIME"),
                ("ADDR1", "1500 Market Street, Philadelphia, PA 19102", "LOCATION"),
                ("DATE2", "2025-07-31", "DATE_TIME"),
                ("EMAIL1", "sabrina.vane@delaware-valley-mail.org", "EMAIL_ADDRESS"),
                ("PHONE1", "(215) 555-0195", "PHONE_NUMBER"),
            ],
        ),
        (
            "corr_20",
            "Subject: Final Closing Statement — Acquisition of {{NAME1}} Consulting LLC\n"
            "Date: {{DATE1}}\n"
            "Managing Member: {{NAME2}} (Tax ID / SSN: {{SSN1}}, DOB: {{DOB1}})\n"
            "Registered Office: {{ADDR1}}\n"
            "Escrow Agent: {{NAME3}} ({{EMAIL1}}, {{PHONE1}})\n"
            "Earn-Out Measurement Date: {{DATE2}}",
            [
                ("NAME1", "Aldridge", "PERSON"),
                ("DATE1", "November 28, 2025", "DATE_TIME"),
                ("NAME2", "Philip M. Aldridge", "PERSON"),
                ("SSN1", "419-60-8253", "US_SSN"),
                ("DOB1", "06/23/1973", "DATE_TIME"),
                ("ADDR1", "301 South College Street, Charlotte, NC 28202", "LOCATION"),
                ("NAME3", "Veronica H. Pate", "PERSON"),
                ("EMAIL1", "vpate@queen-city-escrow.com", "EMAIL_ADDRESS"),
                ("PHONE1", "704-555-0165", "PHONE_NUMBER"),
                ("DATE2", "November 28, 2026", "DATE_TIME"),
            ],
        ),
    ]

    for doc_id, tmpl, flds in correspondence_data:
        docs.append(build_tagged_document(doc_id, "correspondence", tmpl, flds))

    return docs


def main() -> None:
    out_dir = Path(__file__).resolve().parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "business_holdout_60.jsonl"

    docs = generate_documents()
    assert len(docs) == 60, f"Expected 60 docs, got {len(docs)}"

    label_counts: dict[str, int] = {lbl: 0 for lbl in sorted(REQUIRED_LABELS)}
    doc_type_counts: dict[str, int] = {}

    lines: list[str] = []
    for doc in docs:
        doc_type_counts[doc["doc_type"]] = doc_type_counts.get(doc["doc_type"], 0) + 1
        for sp in doc["spans"]:
            label_counts[sp["label"]] += 1
        lines.append(json.dumps(doc, ensure_ascii=False))

    payload = "\n".join(lines) + "\n"
    out_file.write_text(payload, encoding="utf-8")
    sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    manifest = {
        "dataset": "independent_business_holdout_60",
        "num_documents": len(docs),
        "doc_type_counts": doc_type_counts,
        "label_counts": label_counts,
        "total_spans": sum(label_counts.values()),
        "sha256": sha256,
    }
    manifest_path = out_dir / "business_holdout_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
