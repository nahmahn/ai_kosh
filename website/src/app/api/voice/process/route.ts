import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
    try {
        const formData = await req.formData();

        // Proxy to FastAPI backend on port 8000
        const backendUrl = process.env.VOICE_PIPELINE_URL || "http://127.0.0.1:8000";
        const endpoint = `${backendUrl}/voice/process`;

        const response = await fetch(endpoint, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error("Voice pipeline error:", errorText);
            return NextResponse.json(
                { detail: `FastAPI error: ${response.status}`, error: errorText },
                { status: response.status }
            );
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error("Error connecting to voice pipeline:", error);
        return NextResponse.json(
            { detail: "Failed to connect to backend voice service. Is FastAPI running on port 8000?" },
            { status: 500 }
        );
    }
}
