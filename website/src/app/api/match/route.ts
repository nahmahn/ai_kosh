import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();
        const { state, district, productCategory, transactionType, enterpriseName, annualTurnover } = body;

        // Simulate processing
        await new Promise(r => setTimeout(r, 2500));

        // Layer 2: Generate synthetic SNPs
        const snps = [
            {
                id: "snp-dlhi-logistic",
                name: "Delhivery Regional B2B",
                domain: "Retail & Logistics",
                capability_alignment: (0.85 + Math.random() * 0.05).toFixed(2),
                fl_success_prob: (0.76 + Math.random() * 0.06).toFixed(2),
                friction_risk: (0.03 + Math.random() * 0.03).toFixed(2),
                confidence_interval: { lower: 0.68, upper: 0.84 },
                shap_explanations: [
                    { feature: "B2B Fulfillment", contribution: "+25%", reason: "Strong alignment with your B2B volume." },
                    { feature: "Geography", contribution: `+15%`, reason: `High success rate for sellers in ${state || "Uttar Pradesh"}.` },
                    { feature: "Category", contribution: "+10%", reason: `Specializes in ${productCategory || "4S"} handling.` },
                    { feature: "Capacity", contribution: "+8%", reason: "Available bandwidth for new MSE onboarding." }
                ]
            },
            {
                id: "snp-msme-mart",
                name: "MSME Global Mart (NSIC)",
                domain: "Government B2B",
                capability_alignment: (0.72 + Math.random() * 0.08).toFixed(2),
                fl_success_prob: (0.81 + Math.random() * 0.06).toFixed(2),
                friction_risk: (0.06 + Math.random() * 0.04).toFixed(2),
                confidence_interval: { lower: 0.72, upper: 0.88 },
                shap_explanations: [
                    { feature: "NSIC Integration", contribution: "+30%", reason: "Native NSIC platform integration." },
                    { feature: "Udyam Verification", contribution: "+12%", reason: "Udyam ID pre-verified via LayoutLMv3." },
                    { feature: "Dispute History", contribution: "-5%", reason: "Slight resolution delays in recent 90 days." }
                ]
            },
            {
                id: "snp-local-kart",
                name: "LocalKart Express",
                domain: "B2C Hyperlocal",
                capability_alignment: (0.67 + Math.random() * 0.08).toFixed(2),
                fl_success_prob: (0.62 + Math.random() * 0.10).toFixed(2),
                friction_risk: (0.02 + Math.random() * 0.03).toFixed(2),
                confidence_interval: { lower: 0.54, upper: 0.72 },
                shap_explanations: [
                    { feature: "Hyperlocal Reach", contribution: "+20%", reason: `Excellent coverage in ${district || "Ghaziabad"}.` },
                    { feature: "B2C Focus", contribution: transactionType === 'B2C' ? "+18%" : "-15%", reason: "Optimized for direct-to-consumer." },
                    { feature: "Capacity", contribution: "+8%", reason: "Available bandwidth for new sellers." }
                ]
            }
        ];

        // Calculate composite score (alpha=0.4, beta=0.4, gamma=0.2)
        const alpha = 0.4, beta = 0.4, gamma = 0.2;
        snps.forEach(s => {
            const composite = (alpha * parseFloat(s.capability_alignment)) +
                (beta * parseFloat(s.fl_success_prob)) -
                (gamma * parseFloat(s.friction_risk));
            (s as any).composite_score = Math.max(0, Math.min(1, composite)).toFixed(2);
        });
        snps.sort((a: any, b: any) => parseFloat(b.composite_score) - parseFloat(a.composite_score));

        // ── Layer 2: Heterogeneous Knowledge Graph (HKG) ──
        const catLabel = productCategory || "cat-4S";
        const locLabel = district || "Ghaziabad";
        const graphEdges = [
            { source: "mse-new", target: catLabel, label: "produces", type: "direct" },
            { source: "mse-new", target: `loc-${locLabel}`, label: "located_in", type: "direct" },
            { source: "mse-sim1", target: catLabel, label: "produces", type: "similar" },
            { source: "mse-sim2", target: `loc-${locLabel}`, label: "located_in", type: "similar" },
            { source: "mse-sim1", target: snps[0].id, label: "served_by (success)", type: "historical" },
            { source: "mse-sim2", target: snps[0].id, label: "served_by (success)", type: "historical" },
            { source: "mse-sim2", target: snps[1].id, label: "served_by (success)", type: "historical" },
            { source: "mse-new", target: snps[0].id, label: "inferred_match", type: "inferred" },
            { source: "mse-new", target: snps[1].id, label: "inferred_match", type: "inferred" }
        ];

        const graphMeta = {
            model: "HGT (Heterogeneous Graph Transformer)",
            embeddingDim: 128,
            neighbourhoodHops: 2,
            totalNodes: 1247,
            totalEdges: 4891,
            cosineScores: [
                { snp: snps[0].name, score: parseFloat(snps[0].capability_alignment) },
                { snp: snps[1].name, score: parseFloat(snps[1].capability_alignment) },
                { snp: snps[2].name, score: parseFloat(snps[2].capability_alignment) }
            ],
            coldStartResolution: "Inductive (GraphSAGE neighbourhood sampling)"
        };

        // ── Layer 3: Federated Learning Metrics ──
        const federatedLearning = {
            framework: "Flower (flwr.ai)",
            aggregation: "FedAvg + SecAgg",
            totalRounds: 5,
            participatingClients: 4,
            convergenceData: [
                { round: 1, loss: 0.82, accuracy: 0.61 },
                { round: 2, loss: 0.54, accuracy: 0.73 },
                { round: 3, loss: 0.31, accuracy: 0.81 },
                { round: 4, loss: 0.18, accuracy: 0.87 },
                { round: 5, loss: 0.09, accuracy: 0.91 }
            ],
            clients: [
                { id: "snp-node-A", name: "Delhivery Node", samplesUsed: 1240, status: "synced" },
                { id: "snp-node-B", name: "NSIC Node", samplesUsed: 890, status: "synced" },
                { id: "snp-node-C", name: "LocalKart Node", samplesUsed: 456, status: "synced" },
                { id: "snp-node-D", name: "GeM Portal Node", samplesUsed: 672, status: "synced" }
            ],
            securityProtocol: "Secure Aggregation (SecAgg)",
            dpdpCompliance: {
                consentLog: true,
                purposeLimitation: true,
                dataMinimization: true,
                zeroRawDataTransfer: true
            },
            globalModelAccuracy: 0.91,
            predictionLatency: "42ms"
        };

        // ── Layer 4: Friction & Composite Scoring ──
        const frictionScoring = {
            dataSource: "ONDC IGM (Issue & Grievance Management) API",
            weights: { alpha: 0.4, beta: 0.4, gamma: 0.2 },
            formula: "Final = (α × Capability) + (β × FL_Success) − (γ × Friction)",
            perSnpBreakdown: snps.map((s: any) => ({
                snpName: s.name,
                capabilityAligned: parseFloat(s.capability_alignment),
                flSuccess: parseFloat(s.fl_success_prob),
                frictionRisk: parseFloat(s.friction_risk),
                igmDisputes: { total: Math.floor(Math.random() * 8 + 1), resolved: Math.floor(Math.random() * 6 + 1), avgDays: (Math.random() * 5 + 2).toFixed(1) },
                compositeScore: parseFloat(s.composite_score),
                formulaTrace: `(0.4 × ${s.capability_alignment}) + (0.4 × ${s.fl_success_prob}) − (0.2 × ${s.friction_risk}) = ${s.composite_score}`
            })),
            fairnessAudit: {
                womenLedCheck: "PASSED",
                scStCheck: "PASSED",
                geographicBiasCheck: "PASSED",
                auditTimestamp: new Date().toISOString()
            }
        };

        return NextResponse.json({
            matches: snps,
            graph: { edges: graphEdges, meta: graphMeta },
            federatedLearning,
            frictionScoring,
            inferenceInfo: "HGT inductive inference completed. Federated predictions applied.",
            processingTime: "2.4s",
            ondcProtocol: "Beckn v1.2.0"
        });

    } catch (error) {
        console.error("Match mock error:", error);
        return NextResponse.json({ detail: "Match generation failed" }, { status: 500 });
    }
}
