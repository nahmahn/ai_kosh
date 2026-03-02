import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
    try {
        const formData = await req.formData();

        // Proxy to FastAPI OCR backend on port 8001
        const backendUrl = process.env.OCR_ENGINE_URL || "http://127.0.0.1:8001";
        const endpoint = `${backendUrl}/ocr/process`;

        const response = await fetch(endpoint, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error("OCR engine error:", errorText);
            return NextResponse.json(
                { detail: `FastAPI error: ${response.status}`, error: errorText },
                { status: response.status }
            );
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error("Error connecting to OCR engine:", error);
        return NextResponse.json(
            { detail: "Failed to connect to backend OCR service. Is FastAPI running on port 8001?" },
            { status: 500 }
        );
    }
}
