import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();
        const { state, district, productCategory, transactionType } = body;

        // Mocking the 4-Layer Output
        // Delay to simulate processing
        await new Promise(r => setTimeout(r, 2000));

        // Generate synthetic SNPs
        const snps = [
            {
                id: "snp-dlhi-logistic",
                name: "Delhivery Regional B2B",
                domain: "Retail & Logistics",
                capability_alignment: (0.8 + Math.random() * 0.1).toFixed(2),
                fl_success_prob: (0.75 + Math.random() * 0.1).toFixed(2),
                friction_risk: (0.01 + Math.random() * 0.05).toFixed(2),
                shap_explanations: [
                    { feature: "B2B Fulfillment", contribution: "+25%", reason: "Strong alignment with your B2B volume." },
                    { feature: "Geography", contribution: `+15%`, reason: `High success rate for sellers in ${state || "your region"}.` },
                    { feature: "Category", contribution: "+10%", reason: `Specializes in ${productCategory || "your category"} handling.` }
                ]
            },
            {
                id: "snp-msme-mart",
                name: "MSME Global Mart (NSIC)",
                domain: "Government B2B",
                capability_alignment: (0.7 + Math.random() * 0.1).toFixed(2),
                fl_success_prob: (0.8 + Math.random() * 0.1).toFixed(2),
                friction_risk: (0.05 + Math.random() * 0.05).toFixed(2),
                shap_explanations: [
                    { feature: "Platform Integration", contribution: "+30%", reason: "Native NSIC integration." },
                    { feature: "Verification", contribution: "+12%", reason: "Udyam ID pre-verified." },
                    { feature: "Dispute History", contribution: "-5%", reason: "Slight resolution delays in recent 90 days." }
                ]
            },
            {
                id: "snp-local-kart",
                name: "LocalKart Express",
                domain: "B2C Hyperlocal",
                capability_alignment: (0.65 + Math.random() * 0.1).toFixed(2),
                fl_success_prob: (0.6 + Math.random() * 0.15).toFixed(2),
                friction_risk: (0.02 + Math.random() * 0.03).toFixed(2),
                shap_explanations: [
                    { feature: "Hyperlocal Reach", contribution: "+20%", reason: `Excellent coverage in ${district || "your district"}.` },
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

        // Sort by composite score descending
        snps.sort((a: any, b: any) => parseFloat(b.composite_score) - parseFloat(a.composite_score));

        // Graph Neighbourhood mockup
        const graphNodes = [
            { id: "mse-new", label: "Your Enterprise", type: "MSE", group: "user" },
            { id: `cat-${productCategory}`, label: productCategory || "Category", type: "Category", group: "taxonomy" },
            { id: `loc-${district}`, label: district || "District", type: "Location", group: "geo" },
            { id: snps[0].id, label: snps[0].name, type: "SNP", group: "snp" },
            { id: snps[1].id, label: snps[1].name, type: "SNP", group: "snp" },
            { id: "mse-sim1", label: "Structurally Similar MSE A", type: "MSE", group: "peer" },
            { id: "mse-sim2", label: "Structurally Similar MSE B", type: "MSE", group: "peer" }
        ];

        const graphEdges = [
            { source: "mse-new", target: `cat-${productCategory}`, label: "produces" },
            { source: "mse-new", target: `loc-${district}`, label: "located_in" },
            { source: "mse-sim1", target: `cat-${productCategory}`, label: "produces" },
            { source: "mse-sim2", target: `loc-${district}`, label: "located_in" },
            { source: "mse-sim1", target: snps[0].id, label: "served_by (success)" },
            { source: "mse-sim2", target: snps[1].id, label: "served_by (success)" },
            { source: "mse-new", target: snps[0].id, label: "inferred_match" }
        ];

        return NextResponse.json({
            matches: snps,
            graph: { nodes: graphNodes, edges: graphEdges },
            inferenceInfo: "HGT inductive inference completed. Federated predictions applied."
        });

    } catch (error) {
        console.error("Match mock error:", error);
        return NextResponse.json({ detail: "Match generation failed" }, { status: 500 });
    }
}
