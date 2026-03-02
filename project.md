# MSME-Graph: Project Context & Architecture

**IndiaAI Innovation Challenge 2026 | Problem Statement 2 | Ministry of MSME**
**Focus:** Federated Capability Intelligence for ONDC Onboarding - An AI-Powered MSE Agent Mapping Tool

## 1. Executive Summary & Problem Landscape
The MSME Trade Enablement and Marketing (TEAM) Initiative aims to map Micro and Small Enterprises (MSEs) to Seller Network Participants (SNPs) on the Open Network for Digital Commerce (ONDC). 

**Current Bottlenecks:**
1. Manual, inconsistent product category tagging by MSEs.
2. Labour-intensive, manual claim verification by NSIC.
3. Rudimentary, location/domain-only MSE-to-SNP matching that ignores performance, capacity, and dispute history.

**The Solution: MSME-Graph**
A 4-layer AI architecture that automates, optimizes, and scales this onboarding process. It infers capabilities from documents, uses graph intelligence for cold-start matches, employs federated learning for privacy-preserving SNP performance modeling, and scores operational friction. It is fully compliant with the ONDC Beckn Protocol v1.2.0 and the DPDP Act 2023.

---

## 2. The 4-Layer AI Architecture

### Layer 1: Document-Grounded Capability Inference
**Goal:** Replace self-declared (often inaccurate) capability forms with verified intelligence extracted directly from mandatory business documents.

*   **Inputs:** Udyam Certificates, GST Returns (GSTR-1), e-Invoices/e-Way Bills, and Multilingual Voice Output.
*   **Models:**
    *   `LayoutLMv3 (Microsoft)`: Extracts NIC codes, district, enterprise class from Udyam and HSN/SAC codes from GST returns.
    *   `Donut (Document Understanding Transformer)`: OCR-free parsing for robust extraction from low-quality scans.
    *   `IndicASR / OpenAI Whisper`: Multilingual speech-to-text for 22 Indian languages.
*   **Output:** Generated **"Verified Capability Fingerprint"** (JSON) containing confirmed production scales, B2B/B2C classifications, and geographical reach.

### Layer 2: Heterogeneous Knowledge Graph (HKG)
**Goal:** Map the entire MSME-ONDC ecosystem to enable intelligent, semantic matching and solve the "Cold-Start" problem for new MSEs with no ONDC history.

*   **Nodes:** MSEs, SNPs, NIC/HSN Codes, Districts, ONDC Categories, Industry Clusters.
*   **Models:**
    *   `GraphSAGE (Inductive Representation Learning)`: Generates embeddings for new unseen MSEs by looking at their graph neighborhood.
    *   `HGT (Heterogeneous Graph Transformer)`: Learns complex, multi-hop relationships across different entity types (e.g., matching a textile maker in Varanasi to an SNP serving similar textiles in Surat).
*   **Function:** Translates the Capability Fingerprint into graph embeddings, aligning MSE capabilities with SNP specializations using semantic similarity mapping (NIC to ONDC Taxonomy).

### Layer 3: Federated Learning for SNP Performance Modelling
**Goal:** Predict the 90-day transaction success probability of an MSE-SNP match *without* transferring commercially sensitive SNP data centrally, strictly adhering to the **DPDP Act 2023**.

*   **Architecture:** `Flower (flwr.ai)` framework using Federated Averaging (`FedAvg`) or Secure Aggregation (`SecAgg`).
*   **Mechanism:** 
    1. SNPs train local models on their historical success/failure rates with different MSE profiles.
    2. SNPs send *only* encrypted model weight gradients to the central server.
    3. The central server aggregates gradients to update a Global SNP Performance Model.
*   **Outcome:** Returns a probability score: $P(Success | MSE, SNP)$. Zero raw data leakage.

### Layer 4: Friction-Aware Composite Matching Score
**Goal:** Produce the final, ranked top-3 SNP recommendations by penalizing matches with historically high friction or dispute rates.

*   **Data Source:** ONDC Issue & Grievance Management (IGM) API.
*   **Scoring Formula:**
    $Final\_Score = (\alpha * Capability\_Alignment) + (\beta * FL\_Success\_Prob) - (\gamma * Friction\_Risk)$
*   **Features:**
    *   **SHAP Explainability:** Every recommendation output includes a generated explanation for the NSIC reviewer and MSE (e.g., *why* this SNP was recommended over another).
    *   **Fairness Audited:** Built-in checks to ensure fairness for women-led and SC/ST-owned enterprises.

---

## 3. ONDC & DPDP Compliance
*   **ONDC Integration:** Sits upstream of the Beckn protocol. Checks SNP live status via `/subscribe` and `/lookup` before recommending.
*   **DPDP Act 2023:** 
    *   Explicit consent log for document upload.
    *   Purpose Limitation (fingerprint used *only* for matching).
    *   Data Minimization (no irrelevant personal data extracted).
    *   Federated Learning prevents cross-entity data transfers.
