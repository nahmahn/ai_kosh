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
    const [resultJson, setResultJson] = useState<object | null>(null);

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

                // Update state
                setSessionId(data.session_id);
                // Transcript may be nested (data.transcript.cleaned_transcript) or flat
                const transcript = data.transcript?.cleaned_transcript || data.cleaned_transcript || data.transcript?.raw_transcript || data.raw_transcript || "";
                setTranscript(transcript);
                const rounds = data.audio_metadata?.rounds_of_conversation || data.rounds_of_conversation || round + 1;
                setRound(rounds);
                setResultJson(data);

                // Count filled fields
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

                // ── Dispatch auto-fill event to OnboardingForm ──────────
                // Voice backend returns: { extracted_entities: { enterprise_name, product_descriptions[],
                //   buyer_types_mentioned[] (wholesale|retail|government|export|direct_consumer|other_businesses),
                //   buyer_geographies_mentioned[], ... }, ondc_hints: { b2b_signal, b2c_signal, likely_sector } }
                const autoFillData: Record<string, string> = { _source: "Voice Pipeline" };
                if (entities.enterprise_name) autoFillData.enterpriseName = entities.enterprise_name;

                if (entities.product_descriptions?.length) {
                    autoFillData._productHint = entities.product_descriptions.join(", ");
                }

                // Use buyer_types_mentioned (actual schema field) for transaction type
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

                // Use ondc_hints (b2b_signal / b2c_signal booleans) as fallback
                const hints = data.ondc_hints;
                if (!autoFillData.transactionType && hints) {
                    if (hints.b2b_signal && hints.b2c_signal) autoFillData.transactionType = "both";
                    else if (hints.b2b_signal) autoFillData.transactionType = "B2B";
                    else if (hints.b2c_signal) autoFillData.transactionType = "B2C";
                }

                if (entities.buyer_geographies_mentioned?.length) {
                    autoFillData._geographyHint = entities.buyer_geographies_mentioned.join(", ");
                }

                if (Object.keys(autoFillData).length > 1) {
                    window.dispatchEvent(new CustomEvent("ondc-autofill", { detail: autoFillData }));
                }

                // Handle follow-up questions TTS
                const followups = data.followup_questions_audio || [];
                if (followups.length > 0) {
                    const fq = followups[0];
                    setFollowupQuestion(fq.question || "");
                    // Play TTS audio if available
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
                        : "Processing failed. Ensure the FastAPI backend is running on port 8000."
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
        setResultJson(null);
    };

    const content = (
        <div className="two-col">
            {/* Left: Voice Interface */}
            <div className="card">
                <div className="voice-interface">
                    {/* Language Selector */}
                    <div className="language-selector">
                        {LANGUAGES.map((l) => (
                            <button
                                key={l.code}
                                className={`lang-btn ${language === l.code ? "active" : ""}`}
                                onClick={() => setLanguage(l.code)}
                            >
                                {l.label}
                            </button>
                        ))}
                    </div>

                    {/* Mic Button */}
                    <button
                        className={`mic-button ${recording ? "recording" : ""}`}
                        onClick={handleRecordToggle}
                        disabled={processing}
                    >
                        <i className={recording ? "fas fa-stop" : "fas fa-microphone"} />
                    </button>

                    <p className="voice-status">
                        {processing
                            ? "Processing transcript..."
                            : recording
                                ? "Listening... Click to stop"
                                : isComplete
                                    ? "✅ All 10 fields captured!"
                                    : "Click to start recording"}
                    </p>

                    {/* Progress dots */}
                    <div className="conversation-progress">
                        {Array.from({ length: TOTAL_FIELDS }).map((_, i) => (
                            <div
                                key={i}
                                className={`progress-dot ${i < filledFields ? "filled" : ""
                                    } ${i === filledFields ? "active" : ""}`}
                            />
                        ))}
                    </div>
                    <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 8 }}>
                        {filledFields}/{TOTAL_FIELDS} critical fields · Round {round}
                    </p>

                    {processing && <div className="spinner" />}

                    {/* Follow-up Question */}
                    {followupQuestion && !recording && !processing && (
                        <div
                            style={{
                                marginTop: 20,
                                padding: "14px 20px",
                                borderRadius: 12,
                                background: "rgba(74,161,224,0.08)",
                                border: "1px solid rgba(74,161,224,0.15)",
                                textAlign: "left",
                            }}
                        >
                            <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--primary-blue)", marginBottom: 4 }}>
                                <i className="fas fa-volume-up" style={{ marginRight: 6 }} />
                                FOLLOW-UP QUESTION
                            </p>
                            <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", margin: 0 }}>
                                {followupQuestion}
                            </p>
                        </div>
                    )}

                    {error && (
                        <div style={{ marginTop: 16, color: "#e53935", fontSize: "0.85rem" }}>
                            <i className="fas fa-exclamation-triangle" style={{ marginRight: 6 }} />
                            {error}
                        </div>
                    )}

                    {sessionId && (
                        <button
                            className="btn btn-outline btn-sm"
                            style={{ marginTop: 20 }}
                            onClick={resetSession}
                        >
                            <i className="fas fa-redo" /> New Session
                        </button>
                    )}
                </div>
            </div>

            {/* Right: Transcript & extracted data */}
            <div>
                {/* Transcript */}
                <div className="transcript-box">
                    <p className="transcript-label">
                        <i className="fas fa-closed-captioning" style={{ marginRight: 6 }} />
                        Live Transcript
                    </p>
                    <p className="transcript-text">
                        {transcript || "Your spoken words will appear here in real-time..."}
                    </p>
                </div>

                {/* Extracted JSON */}
                {resultJson && (
                    <div className="results-panel" style={{ marginTop: 16, maxHeight: 320 }}>
                        <div className="results-header">
                            <span>
                                <i className="fas fa-brain" style={{ marginRight: 8, opacity: 0.5 }} />
                                Extracted Entities
                            </span>
                            <span className={`status-badge ${isComplete ? "success" : "warning"}`}>
                                <span className="status-dot" />
                                {isComplete ? "Complete" : "In Progress"}
                            </span>
                        </div>
                        <div className="results-body" style={{ fontSize: "0.75rem" }}>
                            <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontFamily: "inherit" }}>
                                {JSON.stringify(
                                    (resultJson as Record<string, unknown>).extracted_entities ||
                                    (resultJson as Record<string, unknown>).nsic_gate3_signals || resultJson,
                                    null,
                                    2
                                )}
                            </pre>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );

    if (isEmbedded) {
        return <div style={{ padding: "40px 20px" }}>{content}</div>;
    }

    return (
        <section className="section section-alt" id="voice-onboarding">
            <div className="container">
                <span className="section-badge">Voice Pipeline</span>
                <h2 className="section-title">Conversational Voice Onboarding</h2>
                <p className="section-subtitle">
                    Speak in any of 11 Indian languages — our Indic Conformer 600M model
                    transcribes and Gemma 4B extracts structured manufacturing data.
                </p>
                {content}
            </div>
        </section>
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
