---
title: "Legality of facial recognition for employee attendance under DPDP Act"
description: "Compliance requirements for biometric attendance systems under the new Digital Personal Data Protection Act 2023."
date: 2026-01-19
question: "Legality of facial recognition for employee attendance under DPDP Act"
author: "SPS Tech Desk"
role: "Data Privacy Officer"
sector: "Tech"
answeredBy: "Col. (Retd) Singh"
tags:
  - "DPDP Act 2023"
  - "Facial Recognition"
  - "Biometrics"
  - "Employee Privacy"
---

## The Direct Answer

Facial Recognition (FR) for attendance is **legal but high-risk** under the **Digital Personal Data Protection (DPDP) Act, 2023**. Employers act as "Data Fiduciaries" and must obtain **explicit, verifiable consent** from employees ("Data Principals"). You must issue a privacy notice explaining *why* you need the face data (purpose limitation) and *how long* you will keep it. Crucially, you must provide an alternative (like an ID card) if an employee refuses consent, unless the FR is mandated by a specific employment law (rare in private sector).

## Detailed Explanation

The "Take it or Leave it" approach to biometric attendance is legally obsolete. The **DPDP Act 2023** fundamentally changes the power dynamic between the employer (Data Fiduciary) and the employee (Data Principal).

### 1. The "Notice and Consent" Pillar
Under **Section 6** of the Act, consent for processing personal data (which includes facial vectors) must be "free, specific, informed, unconditional, and unambiguous." Before capturing an employee's face for the first time, the organization must issue a **Privacy Notice** in plain language (and in the local language if required). This notice must explicitly state: (a) what data is being collected, (b) the specific purpose (attendance/safety), (c) the duration of retention, and (d) how the employee can withdraw their consent. Collecting biometrics via a "general clause" in an employment contract signed 5 years ago is no longer compliant.

### 2. The Right to Erasure and Template Management
A facial recognition system does not store a "photo"; it stores a "Mathematical Vector" of the face. This vector is personal data. **Section 8** mandates that when an employee resigns or their purpose for being on-site ends, the Data Fiduciary must ensure the deletion of that person's biometric template from all local devices and cloud servers. Retaining "retired" face data for "future reference" or "potential re-hiring" is a violation of the **Purpose Limitation** principle and can lead to massive penalties if discovered during a data audit.

### 3. The "Legitimate Use" Debate
**Section 7** of the Act allows for the processing of data for "certain legitimate uses" without explicit consent, including "employment purposes." However, legal experts warn that this is a narrow exception. While using FR to prevent unauthorized entry into a "High-Security Vault" (safety purpose) might qualify as a legitimate use, using it purely for the "convenience" of tracking attendance in a standard office might not. Therefore, obtaining **Active Consent** remains the gold standard for compliance and risk mitigation.

## Privacy by Design Protocols

### 4. Mandatory Fallback Mechanisms
A compliant FR attendance strategy must be inclusive. Organizations should provide a **Secondary Attendance Method** (such as an RFID card or a manual register) for employees who choose to opt out of biometric tracking or for those who have medical conditions (e.g., eye surgery or facial injuries) that interfere with recognition. Forcing an employee to use FR as the *only* way to get paid is "unconditional" and likely a violation of the Act's spirit.

### 5. Data Localization and Vendor Audits
The FR hardware used in many Indian offices often sends data to servers located in China or the US for "algorithm processing." Under the DPDP Act, the employer is responsible for the security of this data, regardless of where it is stored. You must audit your FR vendor: Is the data encrypted at rest? Does the vendor have a "Data Processing Agreement" (DPA) with your firm? If the vendor's cloud is breached, the ₹250 Crore penalty falls on **your organization**, not the hardware manufacturer.

### 6. Updating the Employment Lifecycle
Compliance is not a one-time setup; it must be embedded in the HR lifecycle. 
*   **Onboarding**: Include the Privacy Notice and Consent form as a separate, signed document.
*   **Annual Audit**: Review the user list on all FR terminals and delete any "Ghost Users" or ex-employees.
*   **Exit Interview**: Provide a written acknowledgement to the departing employee that their biometric vectors have been purged from the system.

## Related Questions
*   [Is fingerprint data safer than facial recognition?](/qna/fingerprint-vs-face-privacy)
*   [What is the penalty for data breach under DPDP Act?](/qna/dpdp-penalties)