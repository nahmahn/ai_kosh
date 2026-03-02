"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import {
    validateGSTIN,
    validatePAN,
    validateUdyam,
    validateMobile,
    validateIFSC,
    validatePincode,
    validateAccountNumber,
    lookupPincode,
    NIC_CATEGORIES,
    type ValidationResult,
} from "@/utils/validators";

/* ── Types ──────────────────────────────────────────────────────────────── */

interface FormData {
    // Step 1: Identity Validation
    udyamNumber: string;
    mobile: string;
    // Step 2: Business Details
    pan: string;
    gstin: string;
    enterpriseName: string;
    turnover: string;
    productCategory: string;
    transactionType: "B2B" | "B2C" | "both" | "";
    // Auto-filled from Udyam / Layer 1
    enterpriseClass: string;
    majorActivity: string;
    socialCategory: string;
    // Step 3: Address & Banking
    addressLine1: string;
    addressLine2: string;
    pincode: string;
    city: string;
    district: string;
    state: string;
    accountNumber: string;
    ifscCode: string;
    bankName: string;
    // Manufacturing & Scale (from Voice Pipeline)
    productDescription: string;
    rawMaterials: string;
    factoryArea: string;
    employeesCount: string;
    machinery: string;
    productionCapacity: string;
    yearsInBusiness: string;
    sellingChannels: string;
    buyerGeographies: string;
    // Step 4: Declarations
    declareNotOnONDC: boolean;
    declareNotAvailed: boolean;
    declareAccuracy: boolean;
}

interface FieldValidation {
    [key: string]: ValidationResult;
}

const INITIAL_FORM: FormData = {
    udyamNumber: "",
    mobile: "",
    pan: "",
    gstin: "",
    enterpriseName: "",
    turnover: "",
    productCategory: "",
    transactionType: "",
    enterpriseClass: "",
    majorActivity: "",
    socialCategory: "",
    addressLine1: "",
    addressLine2: "",
    pincode: "",
    city: "",
    district: "",
    state: "",
    accountNumber: "",
    ifscCode: "",
    bankName: "",
    productDescription: "",
    rawMaterials: "",
    factoryArea: "",
    employeesCount: "",
    machinery: "",
    productionCapacity: "",
    yearsInBusiness: "",
    sellingChannels: "",
    buyerGeographies: "",
    declareNotOnONDC: false,
    declareNotAvailed: false,
    declareAccuracy: false,
};

const STEP_TITLES = [
    { title: "Validate Identity", icon: "fas fa-id-card", desc: "Udyam & Mobile Verification" },
    { title: "Business Details", icon: "fas fa-building", desc: "PAN, GSTIN & Product Info" },
    { title: "Address & Banking", icon: "fas fa-map-marker-alt", desc: "Location & Payment Details" },
    { title: "Review & Submit", icon: "fas fa-check-circle", desc: "Declarations & Confirmation" },
];

/* ── Component ──────────────────────────────────────────────────────────── */

export default function OnboardingForm({ isEmbedded = false, initialData }: { isEmbedded?: boolean; initialData?: Record<string, string> | null }) {
    const [step, setStep] = useState(0);
    const [form, setForm] = useState<FormData>(INITIAL_FORM);
    const [validations, setValidations] = useState<FieldValidation>({});
    const [submitted, setSubmitted] = useState(false);
    const [autoFillSource, setAutoFillSource] = useState<Record<string, string>>({});
    const [currentDocSource, setCurrentDocSource] = useState<string>("Udyam Certificate");
    const [pincodeLoading, setPincodeLoading] = useState(false);
    const sectionRef = useRef<HTMLElement>(null);

    // ── Field Update ──────────────────────────────────────────────────────

    const updateField = useCallback(
        (field: keyof FormData, value: string | boolean) => {
            setForm((prev) => ({ ...prev, [field]: value }));
        },
        []
    );

    // ── Inline Validation ─────────────────────────────────────────────────

    const runValidation = useCallback(
        (field: string, value: string) => {
            let result: ValidationResult = { valid: false, message: "" };

            switch (field) {
                case "udyamNumber":
                    result = validateUdyam(value);
                    if (result.valid && result.parsed) {
                        // Auto-fill state from Udyam
                        if (result.parsed.stateName && !form.state) {
                            setForm((prev) => ({ ...prev, state: result.parsed!.stateName }));
                            setAutoFillSource((prev) => ({ ...prev, state: "Udyam Number" }));
                        }
                    }
                    break;
                case "mobile":
                    result = validateMobile(value);
                    break;
                case "pan":
                    result = validatePAN(value);
                    break;
                case "gstin":
                    result = validateGSTIN(value);
                    if (result.valid && result.parsed) {
                        // Auto-fill PAN from GSTIN
                        if (result.parsed.pan && !form.pan) {
                            setForm((prev) => ({ ...prev, pan: result.parsed!.pan }));
                            setAutoFillSource((prev) => ({ ...prev, pan: "GSTIN" }));
                            // Also validate the auto-filled PAN
                            const panResult = validatePAN(result.parsed.pan);
                            setValidations((prev) => ({ ...prev, pan: panResult }));
                        }
                        // Auto-fill state from GSTIN
                        if (result.parsed.stateName) {
                            setForm((prev) => ({ ...prev, state: result.parsed!.stateName }));
                            setAutoFillSource((prev) => ({ ...prev, state: "GSTIN" }));
                        }
                    }
                    break;
                case "pincode":
                    result = validatePincode(value);
                    break;
                case "accountNumber":
                    result = validateAccountNumber(value);
                    break;
                case "ifscCode":
                    result = validateIFSC(value);
                    if (result.valid && result.parsed) {
                        setAutoFillSource((prev) => ({ ...prev, bankName: "IFSC Code" }));
                    }
                    break;
            }

            setValidations((prev) => ({ ...prev, [field]: result }));
        },
        [form.pan, form.state]
    );

    // ── Pincode Auto-fill ─────────────────────────────────────────────────

    useEffect(() => {
        if (form.pincode.length === 6 && validatePincode(form.pincode).valid) {
            setPincodeLoading(true);
            lookupPincode(form.pincode).then((result) => {
                setPincodeLoading(false);
                if (result) {
                    setForm((prev) => ({
                        ...prev,
                        city: result.city,
                        district: result.district,
                        state: result.state,
                    }));
                    setAutoFillSource((prev) => ({
                        ...prev,
                        city: "Pincode",
                        district: "Pincode",
                        state: "Pincode",
                    }));
                }
            });
        }
    }, [form.pincode]);

    // ── Pre-fill Initial Data (from page state) ───────────────────────────
    useEffect(() => {
        if (initialData) {
            const data = initialData;
            const source = data._source || "AI Extraction";
            const newAutoFill: Record<string, string> = {};

            setForm((prev) => {
                const updated = { ...prev };
                for (const [key, value] of Object.entries(data)) {
                    if (key === "_source") continue;
                    if (value && key in updated) {
                        (updated as Record<string, unknown>)[key] = value;
                        newAutoFill[key] = source;
                    }
                }
                return updated;
            });

            if (data._docSource) setCurrentDocSource(data._docSource);
            setAutoFillSource((prev) => ({ ...prev, ...newAutoFill }));
        }
    }, [initialData]);

    // ── Listen for OCR / Voice auto-fill events ───────────────────────────

    useEffect(() => {
        function handleAutoFill(e: CustomEvent) {
            const data = e.detail as Record<string, string>;
            const source = e.detail?._source || "AI Extraction";
            const newAutoFill: Record<string, string> = {};

            setForm((prev) => {
                const updated = { ...prev };
                for (const [key, value] of Object.entries(data)) {
                    if (key === "_source") continue;
                    if (value && key in updated) {
                        (updated as Record<string, unknown>)[key] = value;
                        newAutoFill[key] = source;
                    }
                }
                return updated;
            });

            if (data._docSource) setCurrentDocSource(data._docSource as string);
            setAutoFillSource((prev) => ({ ...prev, ...newAutoFill }));
        }

        window.addEventListener("ondc-autofill" as string, handleAutoFill as EventListener);
        return () => {
            window.removeEventListener("ondc-autofill" as string, handleAutoFill as EventListener);
        };
    }, []);

    // ── Step Navigation ───────────────────────────────────────────────────

    const canAdvance = useCallback((): boolean => {
        switch (step) {
            case 0:
                return (
                    validateUdyam(form.udyamNumber).valid &&
                    validateMobile(form.mobile).valid
                );
            case 1:
                return (
                    validatePAN(form.pan).valid &&
                    form.enterpriseName.trim().length > 0 &&
                    form.productCategory !== "" &&
                    form.transactionType !== ""
                );
            case 2:
                return (
                    form.addressLine1.trim().length > 0 &&
                    validatePincode(form.pincode).valid &&
                    form.city.trim().length > 0 &&
                    form.state.trim().length > 0
                );
            case 3:
                return form.declareNotOnONDC && form.declareNotAvailed && form.declareAccuracy;
            default:
                return false;
        }
    }, [step, form]);

    const nextStep = useCallback(() => {
        if (canAdvance() && step < 3) {
            setStep((s) => s + 1);
            sectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }, [canAdvance, step]);

    const prevStep = useCallback(() => {
        if (step > 0) {
            setStep((s) => s - 1);
            sectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }, [step]);

    const handleSubmit = useCallback(() => {
        if (canAdvance()) {
            setSubmitted(true);
            // Dispatch event for downstream systems
            window.dispatchEvent(
                new CustomEvent("ondc-registration-complete", { detail: form })
            );
        }
    }, [canAdvance, form]);

    const resetForm = useCallback(() => {
        setForm(INITIAL_FORM);
        setValidations({});
        setAutoFillSource({});
        setStep(0);
        setSubmitted(false);
    }, []);

    // ── Field Renderer Helpers ────────────────────────────────────────────

    const renderInput = (
        field: keyof FormData,
        label: string,
        placeholder: string,
        opts: {
            type?: string;
            maxLength?: number;
            transform?: "uppercase" | "none";
            icon?: string;
            half?: boolean;
            disabled?: boolean;
        } = {}
    ) => {
        const val = form[field] as string;
        const v = validations[field];
        const source = autoFillSource[field];
        const hasValidation = v && val.length > 0;

        return (
            <div className={`onb-field ${opts.half ? "onb-field-half" : ""}`}>
                <label className="onb-label">
                    {opts.icon && <i className={opts.icon} />}
                    {label}
                    {source && (
                        <span className="onb-autofill-badge">
                            <i className="fas fa-magic" /> Auto-filled from {source}
                        </span>
                    )}
                </label>
                <input
                    className={`onb-input ${hasValidation ? (v.valid ? "valid" : "invalid") : ""} ${source ? "autofilled" : ""}`}
                    type={opts.type || "text"}
                    value={val}
                    placeholder={placeholder}
                    maxLength={opts.maxLength}
                    disabled={opts.disabled}
                    onChange={(e) => {
                        let newVal = e.target.value;
                        if (opts.transform === "uppercase") newVal = newVal.toUpperCase();
                        updateField(field, newVal);
                        // Clear autofill source if user manually edits
                        if (source) {
                            setAutoFillSource((prev) => {
                                const next = { ...prev };
                                delete next[field];
                                return next;
                            });
                        }
                    }}
                    onBlur={() => {
                        if (val) runValidation(field, val);
                    }}
                />
                {hasValidation && (
                    <span className={`onb-hint ${v.valid ? "onb-hint-success" : "onb-hint-error"}`}>
                        {v.message}
                    </span>
                )}
                {field === "pincode" && pincodeLoading && (
                    <span className="onb-hint onb-hint-loading">
                        <i className="fas fa-spinner fa-spin" /> Looking up pincode…
                    </span>
                )}
            </div>
        );
    };

    const renderSelect = (
        field: keyof FormData,
        label: string,
        options: { value: string; label: string }[],
        opts: { icon?: string; half?: boolean } = {}
    ) => {
        const val = form[field] as string;
        const source = autoFillSource[field];

        return (
            <div className={`onb-field ${opts.half ? "onb-field-half" : ""}`}>
                <label className="onb-label">
                    {opts.icon && <i className={opts.icon} />}
                    {label}
                    {source && (
                        <span className="onb-autofill-badge">
                            <i className="fas fa-magic" /> Auto-filled from {source}
                        </span>
                    )}
                </label>
                <select
                    className={`onb-input onb-select ${val ? "filled" : ""}`}
                    value={val}
                    onChange={(e) => updateField(field, e.target.value)}
                >
                    <option value="">Select…</option>
                    {options.map((o) => (
                        <option key={o.value} value={o.value}>
                            {o.value} — {o.label}
                        </option>
                    ))}
                </select>
            </div>
        );
    };

    // ── Submitted State ──────────────────────────────────────────────────

    if (submitted) {
        const successContent = (
            <div className="onb-success">
                <div className="onb-success-icon">
                    <i className="fas fa-check" />
                </div>
                <h2>Registration Submitted!</h2>
                <p>
                    Your MSME has been registered for the ONDC TEAM Initiative.
                    A Seller Network Participant will be assigned to help you get started.
                </p>
                <div className="onb-success-summary">
                    <div className="onb-success-row">
                        <span>Enterprise</span>
                        <strong>{form.enterpriseName}</strong>
                    </div>
                    <div className="onb-success-row">
                        <span>Udyam Number</span>
                        <strong>{form.udyamNumber}</strong>
                    </div>
                    <div className="onb-success-row">
                        <span>PAN</span>
                        <strong>{form.pan}</strong>
                    </div>
                    {form.gstin && (
                        <div className="onb-success-row">
                            <span>GSTIN</span>
                            <strong>{form.gstin}</strong>
                        </div>
                    )}
                    <div className="onb-success-row">
                        <span>Product Category</span>
                        <strong>
                            {NIC_CATEGORIES.find((c) => c.code === form.productCategory)?.label ||
                                form.productCategory}
                        </strong>
                    </div>
                    <div className="onb-success-row">
                        <span>Location</span>
                        <strong>
                            {form.city}, {form.state} — {form.pincode}
                        </strong>
                    </div>
                </div>
                <button className="btn btn-primary" onClick={resetForm}>
                    <i className="fas fa-redo" /> Register Another Enterprise
                </button>
            </div>
        );

        if (isEmbedded) {
            return <section className="onb-embedded-wrapper" ref={sectionRef}>{successContent}</section>;
        }

        return (
            <section className="section section-alt" id="onboarding-form" ref={sectionRef}>
                <div className="container">
                    {successContent}
                </div>
            </section>
        );
    }

    // ── Main Render ───────────────────────────────────────────────────────

    const content = (
        <>
            {/* ── Stepper ──────────────────────────────────────────────── */}
            <div className="onb-stepper">
                {STEP_TITLES.map((s, i) => (
                    <div
                        key={i}
                        className={`onb-step ${i === step ? "active" : ""} ${i < step ? "completed" : ""}`}
                        onClick={() => i < step && setStep(i)}
                    >
                        <div className="onb-step-circle">
                            {i < step ? <i className="fas fa-check" /> : <i className={s.icon} />}
                        </div>
                        <div className="onb-step-label">
                            <span className="onb-step-title">{s.title}</span>
                            <span className="onb-step-desc">{s.desc}</span>
                        </div>
                        {i < STEP_TITLES.length - 1 && <div className="onb-step-line" />}
                    </div>
                ))}
            </div>

            {/* ── Form Card ────────────────────────────────────────────── */}
            <div className="onb-card">
                {/* Step 0: Identity Validation */}
                {step === 0 && (
                    <div className="onb-step-content">
                        <h3 className="onb-step-heading">
                            <i className="fas fa-id-card" /> Validate Your Identity
                        </h3>
                        <p className="onb-step-info">
                            Enter your Udyam Registration Number and the mobile number linked to it.
                            These will be verified against the Udyam database.
                        </p>

                        <div className="onb-fields">
                            {renderInput("udyamNumber", "Udyam Registration Number", "UDYAM-MH-01-0012345", {
                                transform: "uppercase",
                                maxLength: 22,
                                icon: "fas fa-certificate",
                            })}
                            {renderInput("mobile", "Mobile Number (linked to Udyam)", "+91 98765 43210", {
                                type: "tel",
                                maxLength: 15,
                                icon: "fas fa-mobile-alt",
                            })}
                        </div>

                        <div className="onb-info-box">
                            <i className="fas fa-info-circle" />
                            <div>
                                <strong>Where to find your Udyam Number?</strong>
                                <p>
                                    Your Udyam Registration Number is on your Udyam Certificate.
                                    Format: UDYAM-XX-00-0000000. You can also upload your certificate
                                    in the Document AI section above to auto-fill this.
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Step 1: Business Details */}
                {step === 1 && (
                    <div className="onb-step-content">
                        <h3 className="onb-step-heading">
                            <i className="fas fa-building" /> Business Details
                        </h3>
                        <p className="onb-step-info">
                            Provide your business identification. If you entered a GSTIN, PAN and
                            state will be auto-extracted.
                        </p>

                        <div className="onb-fields">
                            {renderInput("gstin", "GSTIN (if applicable)", "27ABCDE1234F2Z5", {
                                transform: "uppercase",
                                maxLength: 15,
                                icon: "fas fa-file-invoice-dollar",
                            })}

                            <div className="onb-row">
                                {renderInput("pan", "PAN", "ABCPE1234F", {
                                    transform: "uppercase",
                                    maxLength: 10,
                                    icon: "fas fa-id-badge",
                                    half: true,
                                })}
                                {renderInput("enterpriseName", "Enterprise Name", "e.g. Sharma Textiles Pvt Ltd", {
                                    icon: "fas fa-store",
                                    half: true,
                                })}
                            </div>

                            <div className="onb-row">
                                {renderSelect(
                                    "productCategory",
                                    "Product Category (NIC Code)",
                                    NIC_CATEGORIES.map((c) => ({ value: c.code, label: c.label })),
                                    { icon: "fas fa-tags", half: true }
                                )}
                            </div>

                            <div className="onb-divider">
                                <span>Manufacturing & Commercial Scale</span>
                            </div>

                            <div className="onb-fields">
                                {renderInput("productDescription", "What do you make/sell?", "e.g. Handmade leather shoes, Cotton textiles", {
                                    icon: "fas fa-shopping-bag",
                                })}

                                <div className="onb-row">
                                    {renderInput("rawMaterials", "Main Raw Materials", "e.g. Leather hides, Cotton yarn, Dyes", {
                                        icon: "fas fa-box-open",
                                        half: true,
                                    })}
                                    {renderInput("machinery", "Major Machinery", "e.g. Stitching machines, CNC router", {
                                        icon: "fas fa-tools",
                                        half: true,
                                    })}
                                </div>

                                <div className="onb-row">
                                    {renderInput("factoryArea", "Factory/Workshop Area", "e.g. 1500 sq. ft.", {
                                        icon: "fas fa-vector-square",
                                        half: true,
                                    })}
                                    {renderInput("productionCapacity", "Monthly Production", "e.g. 500 units per month", {
                                        icon: "fas fa-chart-line",
                                        half: true,
                                    })}
                                </div>

                                <div className="onb-row">
                                    {renderInput("employeesCount", "No. of Employees", "e.g. 10", {
                                        icon: "fas fa-users",
                                        half: true,
                                    })}
                                    {renderInput("yearsInBusiness", "Years in Business", "e.g. 5", {
                                        icon: "fas fa-calendar-alt",
                                        half: true,
                                    })}
                                </div>

                                {renderInput("sellingChannels", "Where do you sell? (Channels)", "e.g. IndiaMART, WhatsApp, Amazon, Local Market", {
                                    icon: "fas fa-external-link-alt",
                                    half: true,
                                })}
                                {renderInput("buyerGeographies", "Target Markets (Cities/States)", "e.g. Mumbai, Delhi, Export to UAE", {
                                    icon: "fas fa-globe-asia",
                                    half: true,
                                })}
                            </div>

                            <div className="onb-row">
                                {renderInput("turnover", "Annual Turnover (₹)", "e.g. 50,00,000", {
                                    type: "text",
                                    icon: "fas fa-rupee-sign",
                                    half: true,
                                })}
                            </div>

                            {/* Enterprise classification fields (auto-filled from Udyam) */}
                            {(form.enterpriseClass || form.majorActivity || form.socialCategory) && (
                                <div className="onb-info-box" style={{ marginBottom: 16 }}>
                                    <i className="fas fa-magic" />
                                    <div>
                                        <strong>AI-Extracted from {currentDocSource}</strong>
                                        <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 12 }}>
                                            {form.enterpriseClass && (
                                                <span className="onb-autofill-badge" style={{ fontSize: "0.85rem" }}>
                                                    <i className="fas fa-layer-group" /> {form.enterpriseClass} Enterprise
                                                </span>
                                            )}
                                            {form.majorActivity && (
                                                <span className="onb-autofill-badge" style={{ fontSize: "0.85rem" }}>
                                                    <i className="fas fa-industry" /> {form.majorActivity}
                                                </span>
                                            )}
                                            {form.socialCategory && (
                                                <span className="onb-autofill-badge" style={{ fontSize: "0.85rem" }}>
                                                    <i className="fas fa-users" /> {form.socialCategory}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div className="onb-field">
                                <label className="onb-label">
                                    <i className="fas fa-exchange-alt" /> Transaction Type
                                </label>
                                <div className="onb-radio-group">
                                    {[
                                        { value: "B2B", label: "B2B (Business to Business)", icon: "fas fa-handshake" },
                                        { value: "B2C", label: "B2C (Business to Consumer)", icon: "fas fa-user" },
                                        { value: "both", label: "Both B2B & B2C", icon: "fas fa-arrows-alt-h" },
                                    ].map((opt) => (
                                        <label
                                            key={opt.value}
                                            className={`onb-radio-card ${form.transactionType === opt.value ? "selected" : ""}`}
                                        >
                                            <input
                                                type="radio"
                                                name="transactionType"
                                                value={opt.value}
                                                checked={form.transactionType === opt.value}
                                                onChange={() => updateField("transactionType", opt.value)}
                                            />
                                            <i className={opt.icon} />
                                            <span>{opt.label}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Step 2: Address & Banking */}
                {step === 2 && (
                    <div className="onb-step-content">
                        <h3 className="onb-step-heading">
                            <i className="fas fa-map-marker-alt" /> Address & Banking
                        </h3>
                        <p className="onb-step-info">
                            Enter your business address and banking details for payment processing.
                            Pincode auto-fills city, district, and state.
                        </p>

                        <div className="onb-fields">
                            {renderInput("addressLine1", "Address Line 1", "123, Industrial Area, Phase 2", {
                                icon: "fas fa-home",
                            })}
                            {renderInput("addressLine2", "Address Line 2 (Optional)", "Near Bus Stand", {})}

                            <div className="onb-row">
                                {renderInput("pincode", "Pincode", "110001", {
                                    maxLength: 6,
                                    icon: "fas fa-map-pin",
                                    half: true,
                                })}
                                {renderInput("city", "City / Town", "New Delhi", {
                                    icon: "fas fa-city",
                                    half: true,
                                    disabled: pincodeLoading,
                                })}
                            </div>

                            <div className="onb-row">
                                {renderInput("district", "District", "Central Delhi", {
                                    half: true,
                                    disabled: pincodeLoading,
                                })}
                                {renderInput("state", "State", "Delhi", {
                                    icon: "fas fa-flag",
                                    half: true,
                                    disabled: pincodeLoading,
                                })}
                            </div>

                            <div className="onb-divider">
                                <span>Banking Details (for incentive payouts)</span>
                            </div>

                            <div className="onb-row">
                                {renderInput("accountNumber", "Bank Account Number", "1234567890123", {
                                    icon: "fas fa-university",
                                    half: true,
                                })}
                                {renderInput("ifscCode", "IFSC Code", "SBIN0001234", {
                                    transform: "uppercase",
                                    maxLength: 11,
                                    icon: "fas fa-code-branch",
                                    half: true,
                                })}
                            </div>
                        </div>
                    </div>
                )}

                {/* Step 3: Review & Submit */}
                {step === 3 && (
                    <div className="onb-step-content">
                        <h3 className="onb-step-heading">
                            <i className="fas fa-check-circle" /> Review & Submit
                        </h3>
                        <p className="onb-step-info">
                            Review your details and accept the mandatory declarations to complete registration.
                        </p>

                        {/* Summary Table */}
                        <div className="onb-review-grid">
                            <div className="onb-review-section">
                                <h4><i className="fas fa-id-card" /> Identity</h4>
                                <div className="onb-review-row">
                                    <span>Udyam Number</span>
                                    <strong>{form.udyamNumber}</strong>
                                </div>
                                <div className="onb-review-row">
                                    <span>Mobile</span>
                                    <strong>{form.mobile}</strong>
                                </div>
                            </div>

                            <div className="onb-review-section">
                                <h4><i className="fas fa-building" /> Business</h4>
                                <div className="onb-review-row">
                                    <span>Enterprise</span>
                                    <strong>{form.enterpriseName}</strong>
                                </div>
                                <div className="onb-review-row">
                                    <span>PAN</span>
                                    <strong>{form.pan}</strong>
                                </div>
                                {form.gstin && (
                                    <div className="onb-review-row">
                                        <span>GSTIN</span>
                                        <strong>{form.gstin}</strong>
                                    </div>
                                )}
                                <div className="onb-review-row">
                                    <span>Product Category</span>
                                    <strong>
                                        {NIC_CATEGORIES.find((c) => c.code === form.productCategory)?.label || "—"}
                                    </strong>
                                </div>
                                <div className="onb-review-row">
                                    <span>Transaction Type</span>
                                    <strong>{form.transactionType.toUpperCase()}</strong>
                                </div>
                                {form.enterpriseClass && (
                                    <div className="onb-review-row">
                                        <span>Enterprise Class</span>
                                        <strong>{form.enterpriseClass}</strong>
                                    </div>
                                )}
                                {form.majorActivity && (
                                    <div className="onb-review-row">
                                        <span>Major Activity</span>
                                        <strong>{form.majorActivity}</strong>
                                    </div>
                                )}
                                {form.socialCategory && (
                                    <div className="onb-review-row">
                                        <span>Social Category</span>
                                        <strong>{form.socialCategory}</strong>
                                    </div>
                                )}
                            </div>

                            <div className="onb-review-section">
                                <h4><i className="fas fa-map-marker-alt" /> Location</h4>
                                <div className="onb-review-row">
                                    <span>Address</span>
                                    <strong>
                                        {form.addressLine1}
                                        {form.addressLine2 ? `, ${form.addressLine2}` : ""}
                                    </strong>
                                </div>
                                <div className="onb-review-row">
                                    <span>Location</span>
                                    <strong>
                                        {form.city}, {form.district}, {form.state} — {form.pincode}
                                    </strong>
                                </div>
                            </div>
                        </div>

                        {/* Declarations */}
                        <div className="onb-declarations">
                            <h4>Mandatory Declarations</h4>
                            {[
                                {
                                    field: "declareNotOnONDC" as keyof FormData,
                                    text: "I declare that my enterprise is NOT already registered as a seller on the ONDC network.",
                                },
                                {
                                    field: "declareNotAvailed" as keyof FormData,
                                    text: "I declare that my enterprise has NOT previously availed benefits from similar ONDC initiatives by central/state governments.",
                                },
                                {
                                    field: "declareAccuracy" as keyof FormData,
                                    text: "I confirm that all information provided is accurate and I understand that misrepresentation may attract penalties under Section 27 of the MSME Act.",
                                },
                            ].map((decl) => (
                                <label key={decl.field} className="onb-checkbox-label">
                                    <input
                                        type="checkbox"
                                        className="onb-checkbox"
                                        checked={form[decl.field] as boolean}
                                        onChange={(e) => updateField(decl.field, e.target.checked)}
                                    />
                                    <span className="onb-checkbox-custom">
                                        <i className="fas fa-check" />
                                    </span>
                                    <span className="onb-checkbox-text">{decl.text}</span>
                                </label>
                            ))}
                        </div>
                    </div>
                )}

                {/* ── Navigation Buttons ────────────────────────────────── */}
                <div className="onb-nav">
                    {step > 0 && (
                        <button className="btn btn-outline" onClick={prevStep}>
                            <i className="fas fa-arrow-left" /> Back
                        </button>
                    )}
                    <div className="onb-nav-spacer" />
                    {step < 3 ? (
                        <button
                            className="btn btn-primary"
                            disabled={!canAdvance()}
                            onClick={nextStep}
                            style={{ opacity: canAdvance() ? 1 : 0.5 }}
                        >
                            Continue <i className="fas fa-arrow-right" />
                        </button>
                    ) : (
                        <button
                            className="btn btn-primary btn-lg"
                            disabled={!canAdvance()}
                            onClick={handleSubmit}
                            style={{ opacity: canAdvance() ? 1 : 0.5 }}
                        >
                            <i className="fas fa-paper-plane" /> Register on ONDC
                        </button>
                    )}
                </div>
            </div>
        </>
    );

    if (isEmbedded) {
        return <section className="onb-embedded-wrapper" ref={sectionRef}>{content}</section>;
    }

    return (
        <section className="section section-alt" id="onboarding-form" ref={sectionRef}>
            <div className="container">
                <span className="section-badge">ONDC TEAM Portal</span>
                <h2 className="section-title">Smart Onboarding Form</h2>
                <p className="section-subtitle">
                    Register your MSME for the ONDC network. Fields are auto-filled from
                    your uploaded documents and voice data — just review and submit.
                </p>
                {content}
            </div>
        </section>
    );
}
