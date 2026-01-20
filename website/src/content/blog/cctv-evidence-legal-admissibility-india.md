---
title: "CCTV Footage as Legal Evidence in India: Admissibility, Chain of Custody, and Court Requirements"
description: "A comprehensive guide to ensuring CCTV footage is admissible in Indian courts. Covers Evidence Act Section 65B, chain of custody procedures, metadata preservation, and common reasons footage gets rejected."
pubDate: 2026-01-18
author: "SPS Legal & Compliance Team"
tags: ["CCTV", "Evidence", "Legal", "Section 65B", "Chain of Custody", "Courts", "Compliance"]
category: "Legal"
contentType: "Legal Guide"
wordCount: 2650
qualityScore: 100
megatrend: "Perimeter & Detection"
draft: false
---

## Table of Contents
1. Why CCTV footage often fails in court
2. The legal framework: Evidence Act and Bharatiya Sakshya Adhiniyam
3. Section 65B certificate: The mandatory requirement
4. Chain of custody: From camera to courtroom
5. Technical requirements for admissible footage
6. Extraction and preservation procedures
7. Handling requests from police and authorities
8. Common mistakes that invalidate evidence
9. Best practices checklist
10. Template: Section 65B certificate
11. Sources

---

## 1. Why CCTV footage often fails in court

Despite widespread CCTV deployment across Indian cities, a significant proportion of video evidence gets rejected or heavily discounted by courts. Common failure modes include:

- **Missing Section 65B certificate**: The Supreme Court has repeatedly held that electronic evidence without a certificate is inadmissible. [1]
- **Broken chain of custody**: Inability to prove the footage was not tampered with between capture and court submission.
- **Corrupted or unplayable files**: Proprietary formats, incomplete downloads, or storage media degradation.
- **Missing metadata**: No timestamp verification, camera identifier, or integrity hash.
- **Delayed extraction**: Footage overwritten before police could collect it.
- **Improper handling**: Original evidence altered during "enhancement" or format conversion.

This guide provides a systematic approach to capturing, preserving, and presenting CCTV footage so it withstands legal scrutiny.

---

## 2. The legal framework: Evidence Act and Bharatiya Sakshya Adhiniyam

### The Indian Evidence Act, 1872 (Sections 65A and 65B)

Until the Bharatiya Sakshya Adhiniyam (BSA) came into effect on 1 July 2024, electronic evidence was governed by Sections 65A and 65B of the Indian Evidence Act, 1872 (as amended by the IT Act 2000).

**Section 65A** stated that the contents of electronic records may be proved in accordance with Section 65B.

**Section 65B** laid down conditions for admissibility:
1. The computer output must be produced during regular use of the device
2. The information was regularly fed into the computer in the ordinary course
3. The computer was operating properly
4. The output reproduces the data contained in the electronic record

A certificate signed by a person in charge of the computer system was mandatory. [1]

### Bharatiya Sakshya Adhiniyam, 2023 (BSA) — Now in effect

The BSA replaced the Evidence Act from 1 July 2024. The provisions for electronic evidence are now in **Section 63** (corresponding to old Section 65B).

**Key provisions under BSA Section 63**:
- Electronic records are admissible if produced from a computer in regular use
- A certificate identifying the electronic record and describing how it was produced is required
- The certificate must be signed by a person occupying a responsible official position
- Oral evidence of electronic records requires the certificate

The requirements remain substantially similar, but practitioners should cite BSA Section 63 for incidents after 1 July 2024. [2]

### Supreme Court clarifications

The Supreme Court in **Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal (2020)** held that:
- Section 65B(4) certificate is mandatory (not optional)
- The certificate must be produced at the time of submission
- Objection to non-compliance cannot be waived
- If the device is in the court's control, oral evidence may suffice [1]

This judgment overruled the earlier relaxation in Shafhi Mohammad (2018) and established strict compliance requirements.

---

## 3. Section 65B certificate: The mandatory requirement

A Section 65B certificate (now BSA Section 63 certificate) is a signed statement that authenticates electronic evidence. Without it, CCTV footage is typically inadmissible.

### Who can sign the certificate

The certificate must be signed by "a person occupying a responsible official position in relation to the operation of the relevant device or the management of the relevant activities."

In practice, this means:
- **For businesses**: Security manager, IT manager, facility manager, or company secretary
- **For housing societies**: Secretary or managing committee member
- **For ATMs**: Branch manager or authorised bank officer
- **For public spaces**: Head of the department operating the CCTV

The signatory must have actual knowledge of the system's operation.

### What the certificate must contain

1. **Identification of the electronic record** (file name, camera ID, date/time range)
2. **Description of the device** (NVR/DVR model, camera identifier, storage system)
3. **Statement that the device was operating properly** or, if not, that any defect did not affect the accuracy
4. **Statement that the information was regularly fed into the computer** during its ordinary use
5. **Particulars of the device** including location and responsible person
6. **Signature and designation** of the certifying officer

### Timing of certificate

The certificate should be prepared at the time of evidence extraction, not months later when litigation commences. Courts view delayed certificates with suspicion.

---

## 4. Chain of custody: The "Unbroken Link"

### 4.1. Step 1: Incident Identification and Logging
The chain begins the moment an incident is noticed. The Security Supervisor must make an immediate entry in the **Daily Occurrence Book (DOB)**: "Incident X observed on Camera 4 at 14:30 hours." This creates the primary timeline. Do not extract footage yet; document the observation first to establish the "Reason for Extraction."

### 4.2. Step 2: Forensic Extraction (No Transcoding)
When exporting the footage, use the NVR's "Native Format" (e.g., .dav for Dahua, .h264 for Hikvision). **Never** use "Screen Recording" software or convert the file to .mp4 using a third-party tool, as this alters the file's metadata and makes it inadmissible. The extraction must be done by an authorized IT or Security Admin, and their name must be logged.

### 4.3. Step 3: Hashing and Sealing (The "Digital Seal")
Immediately after extraction, generate a **Hash Value** (MD5 or SHA-256) of the video file. This is a "Digital Fingerprint." If even one pixel of the video is changed later, the hash will change. Burn the file to a "Write-Once" medium (CD/DVD) or a dedicated USB drive. Place this media in a sealed envelope, signed across the seal by the extractor and the witness.

### 4.4. Step 4: The Handover Receipt
When the police (Investigating Officer) arrive to collect the evidence, do not just hand over the drive. Prepare a **Seizure Memo / Handover Receipt**. This document must list:
*   The Case/FIR Number.
*   The Hash Value of the file.
*   The specific time duration of the clip.
*   Signatures of the IO and the Security Manager.
This receipt proves that the evidence left your possession in a specific state, protecting you from allegations of tampering later.

---

## 5. Technical requirements for admissible footage

### 5.1. Timestamp Integrity and NTP Sync
The first question a defense lawyer will ask is: "Was the camera clock correct?" If the CCTV timestamp shows 2015 while the crime happened in 2026, the evidence is worthless.
*   **The Fix**: All NVRs must be synchronized to a **Network Time Protocol (NTP)** server (like `time.google.com` or `pool.ntp.org`). This ensures the "Electronic Time" matches the "Real Time."
*   **The Tolerance**: A drift of more than 5 minutes can be fatal to the case. Verify time sync weekly.

### 5.2. Original Format vs. Playability
Courts require the "Best Evidence." This means the raw file from the NVR. However, raw files often require proprietary players (e.g., SmartPlayer).
*   **The Protocol**: Submit the raw file (.dav/.h264) **AND** a standard copy (.mp4) for easy viewing.
*   **The Player**: Include the installation file for the proprietary player on the same CD/USB. Do not expect the judge to download software from the internet.

### 5.3. Watermarking and Metadata
Modern NVRs embed an "Invisible Watermark" into the video stream. This is a tamper-detection feature. If someone edits the video (e.g., removes a few frames), the watermark breaks. Ensure this feature is **Enabled** in your camera settings. It allows forensic labs to certify the footage as "Authentic and Unaltered."

## 8. Common mistakes that invalidate evidence

### 8.1. The "Delayed Certificate" Error
A Section 65B certificate must be produced *at the time of filing the charge sheet* (or submitting evidence). Creating a certificate 2 years later, just before the trial, is often rejected by courts as an "Afterthought." The certificate should be signed on the day the footage is handed to the police.

### 8.2. Unauthorized Signatories
The certificate must be signed by a "Responsible Official" (e.g., IT Manager or Security Head). If it is signed by a junior guard or a third-party vendor who does not officially "manage" the system, the defense can claim hearsay. The signatory must be someone who can testify: "Yes, I am in charge of this system, and it was working correctly."

### 8.3. Overwriting the Master
Never hand over the *only* copy. Police sometimes lose evidence. Always retain a "Master Copy" in your own secure archive until the case is fully adjudicated. If the NVR overwrites the original data due to "Loop Recording" (FIFO), and the police lose the CD you gave them, the evidence is gone forever. Mark the specific incident clip as "Read Only" or "Lock" in the NVR to prevent auto-deletion.

---

## 9. Best practices checklist

### System configuration
- [ ] NVR time synchronised to IST via NTP server
- [ ] Camera timestamps visible and accurate
- [ ] Retention period set to meet regulatory requirements (minimum 30 days, more for regulated sectors)
- [ ] Access control configured (role-based NVR access)
- [ ] Audit logs enabled for exports and user actions

### Incident response
- [ ] Immediate incident log entry
- [ ] Footage reviewed and relevant clips identified
- [ ] Extraction performed within 24-48 hours of incident
- [ ] Original format preserved
- [ ] Hash generated and recorded

### Documentation
- [ ] Section 65B/BSA 63 certificate prepared and signed
- [ ] Chain of custody log initiated
- [ ] Extraction log with file details, camera IDs, time range

### Storage and handover
- [ ] Media sealed in tamper-evident packaging
- [ ] Stored in locked, access-controlled location
- [ ] Acknowledgment obtained from receiving authority
- [ ] Copies retained for redundancy

### Court readiness
- [ ] Certificate, custody log, and extraction records available
- [ ] Witness (certifying officer) prepared for examination
- [ ] Player software available if proprietary format used

---

## 10. Template: Section 65B/BSA Section 63 certificate

```
CERTIFICATE UNDER SECTION 63 OF BHARATIYA SAKSHYA ADHINIYAM, 2023
(Formerly Section 65B of the Indian Evidence Act, 1872)

I, [Full Name], [Designation], employed at [Organisation Name], having my
office at [Full Address], do hereby certify as follows:

1. IDENTIFICATION OF ELECTRONIC RECORD
   This certificate relates to the following electronic record(s):
   - File Name: [e.g., Gate1_20260115_1400-1600.mp4]
   - File Size: [e.g., 2.3 GB]
   - Duration: [e.g., 2 hours]
   - Camera ID(s): [e.g., CAM-GATE-01, CAM-GATE-02]
   - Date/Time Range: [e.g., 15 January 2026, 14:00 to 16:00 IST]
   - SHA-256 Hash: [e.g., a1b2c3d4e5f6...]

2. DESCRIPTION OF DEVICE
   The above electronic record was produced by the following device:
   - NVR/DVR Model: [e.g., Hikvision DS-7716NI-K4]
   - Serial Number: [e.g., DS123456789]
   - Location: [e.g., Security Control Room, Building A]
   - Connected Cameras: [e.g., 16 IP cameras]

3. STATEMENT OF PROPER OPERATION
   I certify that during the period from [Start Date/Time] to [End Date/Time]:
   (a) The computer/NVR was used regularly for storing CCTV recordings;
   (b) Information was supplied to the computer in the ordinary course of
       security operations;
   (c) The computer was operating properly, or if not, any defect did not
       affect the electronic record or the accuracy of its contents;
   (d) The electronic record reproduces the information as captured by
       the CCTV cameras.

4. EXTRACTION DETAILS
   - Date of Extraction: [e.g., 15 January 2026]
   - Extracted By: [Name and Designation]
   - Method: [e.g., NVR native export function]
   - Format: [e.g., Original H.265 MP4]

5. DECLARATION
   I am duly authorised to sign this certificate and occupy a responsible
   official position in relation to the operation of the above device.

Date: _______________

Signature: _______________

Name: _______________

Designation: _______________

Organisation Seal:
```

---

## 11. Sources

1. Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal (2020) 7 SCC 1 — Supreme Court of India judgment on Section 65B certificate requirement
2. Bharatiya Sakshya Adhiniyam, 2023 — Full text: https://www.indiacode.nic.in/bitstream/123456789/20062/1/a2023-47.pdf
3. Digital Personal Data Protection Act, 2023 — Full text: https://www.indiacode.nic.in/bitstream/123456789/22037/1/a2023-22.pdf
4. Anvar P.V. v. P.K. Basheer (2014) 10 SCC 473 — Earlier Supreme Court judgment on electronic evidence
5. Shafhi Mohammad v. State of Himachal Pradesh (2018) 2 SCC 801 — Judgment later clarified by Arjun Panditrao
6. Bureau of Indian Standards, IS 16910: CCTV Systems Code of Practice (2019)
