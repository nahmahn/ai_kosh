/**
 * ONDC MSME Onboarding — Validation & Parsing Utilities
 *
 * Covers: GSTIN, PAN, Udyam, Pincode, IFSC, Mobile
 * All regex patterns follow Government of India standards.
 */

// ── Indian State Codes (GSTIN first 2 digits) ──────────────────────────────
export const STATE_CODES: Record<string, string> = {
    "01": "Jammu & Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "25": "Daman & Diu",
    "26": "Dadra & Nagar Haveli",
    "27": "Maharashtra",
    "28": "Andhra Pradesh (Old)",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman & Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
};

// ── PAN Category Codes ──────────────────────────────────────────────────────
export const PAN_CATEGORIES: Record<string, string> = {
    A: "Association of Persons",
    B: "Body of Individuals",
    C: "Company",
    F: "Partnership Firm",
    G: "Government",
    H: "Hindu Undivided Family",
    J: "Artificial Judicial Person",
    L: "Local Authority",
    P: "Individual",
    T: "Trust",
};

// ── Udyam State Codes ───────────────────────────────────────────────────────
export const UDYAM_STATES: Record<string, string> = {
    AN: "Andaman & Nicobar",
    AP: "Andhra Pradesh",
    AR: "Arunachal Pradesh",
    AS: "Assam",
    BR: "Bihar",
    CH: "Chandigarh",
    CG: "Chhattisgarh",
    DD: "Daman & Diu",
    DL: "Delhi",
    GA: "Goa",
    GJ: "Gujarat",
    HP: "Himachal Pradesh",
    HR: "Haryana",
    JH: "Jharkhand",
    JK: "Jammu & Kashmir",
    KA: "Karnataka",
    KL: "Kerala",
    LA: "Ladakh",
    MH: "Maharashtra",
    ML: "Meghalaya",
    MN: "Manipur",
    MP: "Madhya Pradesh",
    MZ: "Mizoram",
    NL: "Nagaland",
    OD: "Odisha",
    PB: "Punjab",
    PY: "Puducherry",
    RJ: "Rajasthan",
    SK: "Sikkim",
    TN: "Tamil Nadu",
    TR: "Tripura",
    TS: "Telangana",
    UK: "Uttarakhand",
    UP: "Uttar Pradesh",
    WB: "West Bengal",
};

// ── Validation Functions ────────────────────────────────────────────────────

export interface ValidationResult {
    valid: boolean;
    message: string;
    parsed?: Record<string, string>;
}

/**
 * Validate GSTIN (15-digit alphanumeric).
 * Format: {2-digit state}{10-char PAN}{entity}{Z}{checksum}
 */
export function validateGSTIN(gstin: string): ValidationResult {
    const cleaned = gstin.trim().toUpperCase();

    if (cleaned.length === 0) {
        return { valid: false, message: "" };
    }

    const regex = /^(\d{2})([A-Z]{5}\d{4}[A-Z])(\d)([A-Z])([A-Z0-9])$/;
    const match = cleaned.match(regex);

    if (!match) {
        return {
            valid: false,
            message: "Invalid GSTIN format. Expected 15 characters (e.g., 27ABCDE1234F2Z5)",
        };
    }

    const stateCode = match[1];
    const pan = match[2];
    const stateName = STATE_CODES[stateCode];

    if (!stateName) {
        return { valid: false, message: `Unknown state code: ${stateCode}` };
    }

    return {
        valid: true,
        message: `✅ Valid — ${stateName}`,
        parsed: {
            stateCode,
            stateName,
            pan,
            entityNumber: match[3],
            fullGstin: cleaned,
        },
    };
}

/**
 * Validate PAN (10-char alphanumeric).
 * Format: {3 alpha}{1 category}{1 surname initial}{4 numeric}{1 alpha}
 */
export function validatePAN(pan: string): ValidationResult {
    const cleaned = pan.trim().toUpperCase();

    if (cleaned.length === 0) {
        return { valid: false, message: "" };
    }

    const regex = /^([A-Z]{3})([ABCFGHLJPT])([A-Z])(\d{4})([A-Z])$/;
    const match = cleaned.match(regex);

    if (!match) {
        return {
            valid: false,
            message: "Invalid PAN format. Expected 10 characters (e.g., ABCPE1234F)",
        };
    }

    const categoryCode = match[2];
    const categoryName = PAN_CATEGORIES[categoryCode] || "Unknown";

    return {
        valid: true,
        message: `✅ Valid — ${categoryName}`,
        parsed: {
            category: categoryCode,
            categoryName,
            surnameInitial: match[3],
            fullPan: cleaned,
        },
    };
}

/**
 * Validate Udyam Registration Number.
 * Format: UDYAM-{2-letter state}-{2-digit type}-{7+ digit serial}
 */
export function validateUdyam(udyam: string): ValidationResult {
    const cleaned = udyam.trim().toUpperCase().replace(/\s+/g, "");

    if (cleaned.length === 0) {
        return { valid: false, message: "" };
    }

    const regex = /^UDYAM-([A-Z]{2})-(\d{2})-(\d{5,10})$/;
    const match = cleaned.match(regex);

    if (!match) {
        return {
            valid: false,
            message: "Invalid Udyam format. Expected: UDYAM-XX-00-0000000",
        };
    }

    const stateCode = match[1];
    const typeCode = match[2];
    const stateName = UDYAM_STATES[stateCode];

    if (!stateName) {
        return { valid: false, message: `Unknown state code in Udyam: ${stateCode}` };
    }

    const typeNumber = parseInt(typeCode, 10);
    let enterpriseType = "Unknown";
    if (typeNumber >= 1 && typeNumber <= 9) {
        const types = [
            "",
            "Micro Manufacturing",
            "Small Manufacturing",
            "Medium Manufacturing",
            "Micro Services",
            "Small Services",
            "Medium Services",
            "Micro Trading",
            "Small Trading",
            "Medium Trading",
        ];
        enterpriseType = types[typeNumber] || "Unknown";
    }

    return {
        valid: true,
        message: `✅ Valid — ${stateName} · ${enterpriseType}`,
        parsed: {
            stateCode,
            stateName,
            typeCode,
            enterpriseType,
            serialNumber: match[3],
            fullUdyam: cleaned,
        },
    };
}

/**
 * Validate Indian mobile number. 10 digits starting with 6-9.
 */
export function validateMobile(mobile: string): ValidationResult {
    const cleaned = mobile.trim().replace(/[\s\-+]/g, "");
    // Remove +91 or 91 prefix
    const digits = cleaned.replace(/^(\+?91)/, "");

    if (digits.length === 0) {
        return { valid: false, message: "" };
    }

    if (!/^[6-9]\d{9}$/.test(digits)) {
        return {
            valid: false,
            message: "Invalid mobile. Expected 10 digits starting with 6-9",
        };
    }

    return { valid: true, message: "✅ Valid Indian mobile number" };
}

/**
 * Validate IFSC Code. 11 chars: 4 bank + 0 + 6 branch.
 */
export function validateIFSC(ifsc: string): ValidationResult {
    const cleaned = ifsc.trim().toUpperCase();

    if (cleaned.length === 0) {
        return { valid: false, message: "" };
    }

    if (!/^[A-Z]{4}0[A-Z0-9]{6}$/.test(cleaned)) {
        return {
            valid: false,
            message: "Invalid IFSC format. Expected 11 characters (e.g., SBIN0001234)",
        };
    }

    const bankCode = cleaned.slice(0, 4);
    return {
        valid: true,
        message: `✅ Valid — Bank: ${bankCode}`,
        parsed: { bankCode, branchCode: cleaned.slice(5), fullIfsc: cleaned },
    };
}

/**
 * Validate Indian Pincode. 6 digits, first digit 1-9.
 */
export function validatePincode(pincode: string): ValidationResult {
    const cleaned = pincode.trim();

    if (cleaned.length === 0) {
        return { valid: false, message: "" };
    }

    if (!/^[1-9]\d{5}$/.test(cleaned)) {
        return { valid: false, message: "Invalid pincode. Expected 6 digits" };
    }

    return { valid: true, message: "✅ Valid Indian pincode" };
}

/**
 * Validate bank account number. 9-18 digits.
 */
export function validateAccountNumber(accNo: string): ValidationResult {
    const cleaned = accNo.trim().replace(/\s/g, "");

    if (cleaned.length === 0) {
        return { valid: false, message: "" };
    }

    if (!/^\d{9,18}$/.test(cleaned)) {
        return { valid: false, message: "Account number should be 9-18 digits" };
    }

    return { valid: true, message: "✅ Valid account number format" };
}

// ── NIC Code Product Categories (top-level manufacturing divisions) ──────

export const NIC_CATEGORIES = [
    { code: "10", label: "Food Products" },
    { code: "11", label: "Beverages" },
    { code: "12", label: "Tobacco Products" },
    { code: "13", label: "Textiles" },
    { code: "14", label: "Wearing Apparel" },
    { code: "15", label: "Leather & Related Products" },
    { code: "16", label: "Wood & Cork Products" },
    { code: "17", label: "Paper & Paper Products" },
    { code: "18", label: "Printing & Recorded Media" },
    { code: "19", label: "Coke & Refined Petroleum" },
    { code: "20", label: "Chemicals & Chemical Products" },
    { code: "21", label: "Pharmaceuticals & Medicinal Products" },
    { code: "22", label: "Rubber & Plastics Products" },
    { code: "23", label: "Non-Metallic Mineral Products" },
    { code: "24", label: "Basic Metals" },
    { code: "25", label: "Fabricated Metal Products" },
    { code: "26", label: "Computer & Electronic Products" },
    { code: "27", label: "Electrical Equipment" },
    { code: "28", label: "Machinery & Equipment" },
    { code: "29", label: "Motor Vehicles & Trailers" },
    { code: "30", label: "Other Transport Equipment" },
    { code: "31", label: "Furniture" },
    { code: "32", label: "Other Manufacturing" },
    { code: "33", label: "Repair & Installation of Machinery" },
    // Services categories
    { code: "45", label: "Wholesale & Retail Trade (Motor Vehicles)" },
    { code: "46", label: "Wholesale Trade" },
    { code: "47", label: "Retail Trade" },
    { code: "49", label: "Land Transport" },
    { code: "56", label: "Food & Beverage Services" },
    { code: "62", label: "Computer Programming & IT Services" },
    { code: "63", label: "Information Services" },
    { code: "74", label: "Professional, Scientific & Technical Services" },
    { code: "96", label: "Other Personal Services" },
];

// ── Pincode Lookup ──────────────────────────────────────────────────────────

export interface PincodeResult {
    city: string;
    state: string;
    district: string;
}

export async function lookupPincode(pincode: string): Promise<PincodeResult | null> {
    try {
        const res = await fetch(`https://api.postalpincode.in/pincode/${pincode}`);
        if (!res.ok) return null;

        const data = await res.json();
        if (data?.[0]?.Status === "Success" && data[0].PostOffice?.length > 0) {
            const po = data[0].PostOffice[0];
            return {
                city: po.Block || po.Name || "",
                state: po.State || "",
                district: po.District || "",
            };
        }
        return null;
    } catch {
        return null;
    }
}
