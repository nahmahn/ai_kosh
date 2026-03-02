"use client";

import { useState, useRef, useCallback, useEffect } from "react";

const LANGUAGES = [
    { code: "hi", label: "हिन्दी" },
    { code: "ta", label: "தமிழ்" },
    { code: "te", label: "తెలుగు" },
    { code: "bn", label: "বাংলা" },
    { code: "mr", label: "मराठी" },
    { code: "gu", label: "ગુજરાતી" },
    { code: "kn", label: "ಕನ್ನಡ" },
    { code: "ml", label: "മലയാളം" },
    { code: "or", label: "ଓଡ଼ିଆ" },
    { code: "pa", label: "ਪੰਜਾਬੀ" },
    { code: "en", label: "English" },
];

const TOTAL_FIELDS = 10;

export default function VoiceOnboarding({ isEmbedded = false }: { isEmbedded?: boolean }) {
    const [language, setLanguage] = useState("hi");
    const [recording, setRecording] = useState(false);
    const [processing, setProcessing] = useState(false);
    const [transcript, setTranscript] = useState("");
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [filledFields, setFilledFields] = useState(0);
    const [isComplete, setIsComplete] = useState(false);
    const [followupQuestion, setFollowupQuestion] = useState("");
    const [round, setRound] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const [conversationHistory, setConversationHistory] = useState<{ role: "user" | "assistant"; text: string }[]>([]);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const streamRef = useRef<MediaStream | null>(null);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            streamRef.current?.getTracks().forEach((t) => t.stop());
        };
    }, []);

    const startRecording = useCallback(async () => {
        try {
            setError(null);
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;
            const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
            mediaRecorderRef.current = mediaRecorder;
            chunksRef.current = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) chunksRef.current.push(e.data);
            };

            mediaRecorder.start();
            setRecording(true);
            setFollowupQuestion("");
        } catch {
            setError("Microphone access denied. Please allow microphone access.");
        }
    }, []);

    const stopRecording = useCallback(async () => {
        if (!mediaRecorderRef.current) return;

        return new Promise<Blob>((resolve) => {
            mediaRecorderRef.current!.onstop = () => {
                const blob = new Blob(chunksRef.current, { type: "audio/webm" });
                streamRef.current?.getTracks().forEach((t) => t.stop());
                resolve(blob);
            };
            mediaRecorderRef.current!.stop();
            setRecording(false);
        });
    }, []);

    const processAudio = useCallback(
        async (audioBlob: Blob) => {
            setProcessing(true);
            setError(null);

            const formData = new FormData();
            formData.append("audio", audioBlob, "recording.webm");
            formData.append("language_hint", language);

            const endpoint = sessionId ? "/api/voice/followup" : "/api/voice/process";
            if (sessionId) formData.append("session_id", sessionId);

            try {
                const res = await fetch(endpoint, {
                    method: "POST",
                    body: formData,
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || `Server error ${res.status}`);
                }

                const data = await res.json();
                setSessionId(data.session_id);

                const currentTranscript = data.transcript?.cleaned_transcript || data.cleaned_transcript || "";
                const turnTranscript = data.transcript?.raw_transcript || data.raw_transcript || "";
                setTranscript(currentTranscript);

                // Add new user turn to history
                if (turnTranscript) {
                    setConversationHistory((prev) => [...prev, { role: "user", text: turnTranscript }]);
                }

                const rounds = data.audio_metadata?.rounds_of_conversation || data.rounds_of_conversation || round + 1;
                setRound(rounds);

                const entities = data.extracted_entities || {};
                let filled = 0;
                if (entities.enterprise_name) filled++;
                if (entities.product_descriptions?.length) filled++;
                if (entities.manufacturing_process_keywords?.length) filled++;
                if (entities.buyer_types_mentioned?.length) filled++;
                if (entities.buyer_geographies_mentioned?.length) filled++;
                if (entities.employees_count) filled++;
                if (entities.years_in_business) filled++;
                if (entities.daily_production_capacity) filled++;
                if (entities.factory_area_size) filled++;
                if (entities.major_machinery_used?.length) filled++;
                setFilledFields(filled);

                setIsComplete(data.conversation_complete || false);

                // ── Expanded auto-fill event to OnboardingForm ──────────
                const autoFillData: Record<string, string> = { _source: "Voice Pipeline" };
                if (entities.enterprise_name) autoFillData.enterpriseName = entities.enterprise_name;

                if (entities.product_descriptions?.length) {
                    autoFillData.productDescription = entities.product_descriptions.join(", ");
                }
                if (entities.raw_materials_mentioned?.length) {
                    autoFillData.rawMaterials = entities.raw_materials_mentioned.join(", ");
                }
                if (entities.factory_area_size) autoFillData.factoryArea = String(entities.factory_area_size);
                if (entities.employees_count) autoFillData.employeesCount = String(entities.employees_count);
                if (entities.years_in_business) autoFillData.yearsInBusiness = String(entities.years_in_business);

                if (entities.major_machinery_used?.length) {
                    autoFillData.machinery = entities.major_machinery_used.join(", ");
                } else if (entities.manufacturing_process_keywords?.length) {
                    autoFillData.machinery = entities.manufacturing_process_keywords.join(", ");
                }

                if (entities.daily_production_capacity) autoFillData.productionCapacity = String(entities.daily_production_capacity);

                if (entities.buyer_geographies_mentioned?.length) {
                    autoFillData.buyerGeographies = entities.buyer_geographies_mentioned.join(", ");
                }

                if (entities.selling_channels?.length) {
                    autoFillData.sellingChannels = entities.selling_channels.join(", ");
                } else if (entities.buyer_types_mentioned?.length) {
                    autoFillData.sellingChannels = entities.buyer_types_mentioned.join(", ");
                }

                if (entities.buyer_types_mentioned?.length) {
                    const types = entities.buyer_types_mentioned as string[];
                    const hasB2B = types.some((t: string) =>
                        ["wholesale", "other_businesses", "government", "export"].includes(t)
                    );
                    const hasB2C = types.some((t: string) =>
                        ["retail", "direct_consumer"].includes(t)
                    );
                    if (hasB2B && hasB2C) autoFillData.transactionType = "both";
                    else if (hasB2B) autoFillData.transactionType = "B2B";
                    else if (hasB2C) autoFillData.transactionType = "B2C";
                }

                const hints = data.ondc_hints;
                if (!autoFillData.transactionType && hints) {
                    if (hints.b2b_signal && hints.b2c_signal) autoFillData.transactionType = "both";
                    else if (hints.b2b_signal) autoFillData.transactionType = "B2B";
                    else if (hints.b2c_signal) autoFillData.transactionType = "B2C";
                }

                if (Object.keys(autoFillData).length > 1) {
                    window.dispatchEvent(new CustomEvent("ondc-autofill", { detail: autoFillData }));
                }

                const followups = data.followup_questions_audio || [];
                if (followups.length > 0 && !data.conversation_complete) {
                    const fq = followups[0];
                    setFollowupQuestion(fq.question || "");

                    // Update history with assistant question
                    setConversationHistory(prev => [
                        ...prev,
                        { role: "assistant", text: fq.question || "" }
                    ]);

                    if (fq.audio_base64 && fq.tts_success) {
                        playBase64Audio(fq.audio_base64);
                    }
                } else {
                    setFollowupQuestion("");
                }
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Processing failed."
                );
            } finally {
                setProcessing(false);
            }
        },
        [language, sessionId, round]
    );

    const handleRecordToggle = useCallback(async () => {
        if (recording) {
            const blob = await stopRecording();
            if (blob) await processAudio(blob);
        } else {
            await startRecording();
        }
    }, [recording, startRecording, stopRecording, processAudio]);

    const resetSession = () => {
        setSessionId(null);
        setTranscript("");
        setFilledFields(0);
        setIsComplete(false);
        setFollowupQuestion("");
        setRound(0);
        setError(null);
    };

    return (
        <div style={{ width: "100%", margin: "0 auto", textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", padding: "20px 0" }}>

            {/* Language Selector */}
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "8px", marginBottom: "32px", maxWidth: "400px" }}>
                {LANGUAGES.slice(0, 5).map((l) => (
                    <button
                        key={l.code}
                        onClick={() => setLanguage(l.code)}
                        style={{
                            padding: "6px 12px",
                            borderRadius: "20px",
                            border: language === l.code ? "none" : "1px solid var(--border-color)",
                            background: language === l.code ? "var(--primary-blue)" : "white",
                            color: language === l.code ? "white" : "var(--text-secondary)",
                            fontSize: "0.85rem",
                            cursor: "pointer",
                            transition: "all 0.2s"
                        }}
                    >
                        {l.label}
                    </button>
                ))}
            </div>

            {/* Central Pulse / Feedback Area */}
            <div style={{ height: "140px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", marginBottom: "32px" }}>
                {!recording && !processing && !followupQuestion && (
                    <div style={{ color: "var(--text-secondary)", fontSize: "1.1rem" }}>
                        Tap the microphone and tell us about your business.
                    </div>
                )}

                {recording && (
                    <div className="pulse-fade" style={{ display: "flex", gap: "8px", alignItems: "center", color: "#ef4444" }}>
                        <div style={{ width: "12px", height: "12px", borderRadius: "50%", background: "#ef4444" }} />
                        <span style={{ fontSize: "1.2rem", fontWeight: 500 }}>Listening...</span>
                    </div>
                )}

                {processing && (
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "12px", color: "var(--primary-blue)" }}>
                        <div className="spinner" style={{ width: "24px", height: "24px", borderWidth: "3px" }} />
                        <span style={{ fontSize: "1.1rem" }}>Analyzing voice data...</span>
                    </div>
                )}

                {followupQuestion && !recording && !processing && (
                    <div className="fade-in" style={{ maxWidth: "80%", textAlign: "center" }}>
                        <p style={{ color: "var(--primary-blue)", fontSize: "0.85rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "1px", marginBottom: "8px" }}>Onboarding Assistant</p>
                        <p style={{ fontSize: "1.2rem", color: "var(--dark-blue)", lineHeight: 1.4, margin: 0 }}>"{followupQuestion}"</p>
                        <p style={{ marginTop: 12, color: "var(--text-muted)", fontSize: "0.85rem", fontStyle: "italic" }}>
                            <i className="fas fa-hand-point-down" /> Tap the mic to reply
                        </p>
                    </div>
                )}
            </div>

            {/* Conversation History Dialogue */}
            {conversationHistory.length > 0 && (
                <div style={{
                    width: "100%",
                    maxWidth: "500px",
                    maxHeight: "200px",
                    overflowY: "auto",
                    marginBottom: "32px",
                    padding: "16px",
                    background: "rgba(0,0,0,0.02)",
                    borderRadius: "16px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "12px",
                    border: "1px solid rgba(0,0,0,0.05)"
                }}>
                    {conversationHistory.map((h, i) => (
                        <div key={i} style={{
                            alignSelf: h.role === "user" ? "flex-end" : "flex-start",
                            maxWidth: "85%",
                            padding: "10px 14px",
                            borderRadius: h.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                            background: h.role === "user" ? "var(--primary-blue)" : "white",
                            color: h.role === "user" ? "white" : "var(--dark-blue)",
                            fontSize: "0.9rem",
                            boxShadow: "0 2px 4px rgba(0,0,0,0.05)",
                            lineHeight: 1.4
                        }}>
                            {h.text}
                        </div>
                    ))}
                </div>
            )}

            {/* Main Mic Action */}
            <button
                onClick={handleRecordToggle}
                disabled={processing}
                style={{
                    width: "80px",
                    height: "80px",
                    borderRadius: "50%",
                    background: recording ? "#ef4444" : "white",
                    border: recording ? "none" : "2px solid rgba(0,0,0,0.05)",
                    boxShadow: recording ? "0 0 24px rgba(239, 68, 68, 0.4)" : "0 8px 24px rgba(0,0,0,0.1)",
                    color: recording ? "white" : "var(--primary-blue)",
                    fontSize: "2rem",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: processing ? "not-allowed" : "pointer",
                    transition: "all 0.3s ease",
                    transform: recording ? "scale(1.1)" : "scale(1)",
                    marginBottom: "32px",
                    opacity: processing ? 0.5 : 1
                }}
                className={recording ? "pulse-ring" : ""}
            >
                <i className={recording ? "fas fa-stop" : "fas fa-microphone"} />
            </button>

            {/* Progress Output */}
            <div style={{ width: "100%", maxWidth: "320px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "8px" }}>
                    <span>Data Captured</span>
                    <span style={{ fontWeight: 600, color: "var(--primary-blue)" }}>{filledFields}/{TOTAL_FIELDS}</span>
                </div>
                <div style={{ width: "100%", height: "6px", background: "rgba(0,0,0,0.05)", borderRadius: "3px", overflow: "hidden" }}>
                    <div
                        style={{
                            width: `${(filledFields / TOTAL_FIELDS) * 100}%`,
                            height: "100%",
                            background: isComplete ? "#22c55e" : "var(--gradient-primary)",
                            transition: "width 0.5s ease"
                        }}
                    />
                </div>
            </div>

            {/* Error & Reset */}
            {error && (
                <div style={{ marginTop: 24, color: "#e53935", fontSize: "0.9rem", display: "flex", alignItems: "center", gap: 8 }}>
                    <i className="fas fa-exclamation-circle" /> {error}
                </div>
            )}

            {sessionId && !recording && !processing && (
                <button
                    onClick={resetSession}
                    style={{
                        marginTop: 24,
                        background: "none",
                        border: "none",
                        color: "var(--text-muted)",
                        fontSize: "0.9rem",
                        cursor: "pointer",
                        textDecoration: "underline"
                    }}
                >
                    Reset Session
                </button>
            )}

        </div>
    );
}

/** Play base64-encoded WAV audio */
function playBase64Audio(base64: string) {
    try {
        const binaryString = atob(base64);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) bytes[i] = binaryString.charCodeAt(i);
        const blob = new Blob([bytes], { type: "audio/wav" });
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.play().catch(() => { });
        audio.onended = () => URL.revokeObjectURL(url);
    } catch {
        // silently fail if audio can't play
    }
}
