---
title: "Cybercrime Victim's First 24 Hours: Step-by-Step Response Protocol"
description: "What to do immediately after a cybercrime incident in India. Covers account freezing, evidence preservation, reporting to 1930 helpline, filing FIR, and bank dispute procedures."
pubDate: 2026-01-18
author: "SPS Cyber Response Team"
tags: ["Cybercrime", "Incident Response", "FIR", "Evidence", "Banking", "Legal"]
category: "Cybersecurity"
contentType: "Response Guide"
wordCount: 2400
qualityScore: 100
megatrend: "Cyber-Physical Convergence"
executive_summary:
  - "Call 1930 immediately - this can freeze fraudster's account before funds are withdrawn"
  - "File online report at cybercrime.gov.in within 1 hour of discovering the fraud"
  - "Contact your bank's fraud helpline to request transaction freeze and raise dispute"
draft: false
---

## Table of Contents
1. Why the first 24 hours matter
2. Hour 1: Immediate containment
3. Hour 1-2: Report to authorities
4. Hour 2-4: Bank and financial response
5. Hour 4-12: Evidence collection and documentation
6. Hour 12-24: FIR filing and follow-up
7. After 24 hours: Ongoing steps
8. What NOT to do
9. Reporting procedures by crime type
10. Bank dispute process
11. Contact directory
12. Sources

---

## 1. Why the first 24 hours matter

In cybercrime, money moves fast. Fraudsters typically:
- Transfer funds through multiple accounts within minutes
- Convert to cryptocurrency or cash within hours
- Move money across state lines or international borders within a day

The I4C (Indian Cyber Crime Coordination Centre) reports that recovery rates drop significantly after:
- **2 hours**: ~40% recovery possible
- **6 hours**: ~20% recovery possible
- **24 hours**: ~5% recovery possible
- **48+ hours**: <1% recovery possible

This guide provides a minute-by-minute protocol to maximise your chances of recovery and successful prosecution.

---

## 2. Hour 1: Immediate containment protocol

### 2.1. Breaking the Connection (If the call is live)
If you are still on the phone with the scammer, the first step is psychological: **Hang Up**. Do not explain, do not shout, and do not try to "record them for evidence" if it keeps the channel open. Every second you stay on the line gives them a chance to use "Social Engineering" to extract one more OTP or delay you from calling the bank. If you installed any app (AnyDesk/TeamViewer), immediately switch your phone to **Airplane Mode** to cut their remote access.

### 2.2. The Financial "Kill Switch" (1930 Helpline)
Your first call must be to **1930** (National Cyber Crime Helpline). This number connects to the **Citizen Financial Cyber Fraud Reporting and Management System (CFCFRMS)**.
*   **How it works**: When you report a fraud transaction ID, the system alerts the recipient bank and all downstream banks in the money trail. It attempts to "Freeze" the money wherever it is currently sitting.
*   **The Golden Hour**: Speed is everything. If called within minutes, the success rate of freezing the funds is over 60%. If you wait 2 hours, the money has likely been converted to crypto or withdrawn at an ATM.

### 2.3. Securing the Compromised Device
If the fraud involved a remote access app or a malicious link:
1.  **Isolate**: Keep the device offline (Wi-Fi/Data off).
2.  **Purge**: Uninstall the suspicious apps immediately.
3.  **Reset**: Ideally, perform a "Factory Reset" to remove hidden malware.
4.  **Credential Refresh**: Using a *different* (clean) device, change your net banking passwords and email passwords. Do not log into your bank from the infected phone until it is wiped.

## 3. Hour 1-2: Reporting to authorities

### 3.1. Filing the National Cybercrime Report
Once the immediate panic is managed, go to **[cybercrime.gov.in](https://cybercrime.gov.in)**. This is mandatory because 1930 is just a helpline; the portal creates the legal record.
*   **Select Category**: Choose "Financial Fraud."
*   **The Details**: You will need the specific transaction IDs (UTR numbers) from your bank SMS. The accuracy of this number determines if the police can track the money.
*   **The Receipt**: Save the "Acknowledgement Number." You will need this for the FIR and for your bank's insurance claim.

## 4. Hour 2-4: Bank and financial response

### 4.1. Formal Dispute and "Shadow Credits"
Call your bank's fraud line (listed on the back of your card). Do not just say "I was cheated." Explicitly state: "I am reporting an **Unauthorized Electronic Transaction** under the RBI Limited Liability Circular."
*   **Request a Freeze**: Ask them to freeze your debit card and net banking access to prevent further debits.
*   **Shadow Credit**: For credit card fraud, ask for a "Shadow Credit" (temporary reversal) so you are not charged interest while the investigation is ongoing.

### 4.2. The UPI Dispute Mechanism
If the money went via UPI (PhonePe/GPay), raise a dispute inside the app immediately. Select the transaction -> Help -> "Report Fraud." This signals the NPCI (National Payments Corporation of India) regarding the beneficiary account. If enough people report the same receiver, their account gets "Blacklisted," preventing them from scamming others.

---

## 5. Hour 4-12: Evidence collection and documentation

### What to preserve

**Digital evidence**:
- [ ] Screenshots of all messages with scammer (WhatsApp, SMS, Telegram)
- [ ] Call log showing scammer's number
- [ ] Call recordings if available
- [ ] Bank transaction receipts/statements
- [ ] UPI payment receipts
- [ ] Any apps installed at scammer's request (note names before deleting)
- [ ] Email communications

**Physical documentation**:
- [ ] 1930 complaint number
- [ ] cybercrime.gov.in acknowledgment
- [ ] Bank service request number
- [ ] Any notes you made during/after the incident

### How to preserve evidence

**Screenshots**:
- Capture full screen including date/time
- Include sender's number/ID in frame
- Save to secure location (cloud backup)

**Call recordings**:
- If your phone records calls, locate the file
- Do not delete even if embarrassing
- Back up to email or cloud

**WhatsApp chats**:
- Open chat → More → Export Chat → With Media
- Saves as text file with attachments

### Document timeline

Create a written timeline:
```
Date: [Date of incident]

[Time] - Received call from [Number] claiming to be [Identity]
[Time] - Was told [What they said]
[Time] - Transferred ₹[Amount] via [Method] to [Recipient]
[Time] - Realised it was a scam because [How you realised]
[Time] - Called 1930, Complaint No: [X]
[Time] - Reported on cybercrime.gov.in, Ack No: [X]
[Time] - Called bank, SR No: [X]
```

This timeline will be needed for FIR and insurance claims.

---

## 6. Hour 12-24: FIR filing and follow-up

### 6.1. Why the FIR is Non-Negotiable
While the online complaint (Hour 2) alerts the police, the **FIR (First Information Report)** initiates the criminal investigation. Without an FIR, you cannot legally claim insurance, nor can the bank process a final chargeback for large amounts. The court needs an FIR to order the "Release of Funds" if the money is frozen in the fraudster's account. It converts your complaint from an "Information Report" to a "Criminal Case."

### 6.2. Where and How to File
You have three options, but Option 1 is preferred for serious fraud:
1.  **Cyber Crime Police Station**: Every metro city (Mumbai, Delhi, Bangalore) has specialized stations. They understand technical evidence better than local police.
2.  **Local Police Station**: You can file at your nearest station. They are legally bound to register a "Zero FIR" irrespective of jurisdiction and transfer it later.
3.  **e-FIR**: States like Maharashtra and Karnataka allow online FIRs for property theft/cybercrime. However, this often requires a physical visit to sign the copy within 3 days.

### 6.3. The "Refusal to File" Scenario
If the Station House Officer (SHO) refuses to file an FIR (often citing "jurisdiction" or "civil dispute"), you have recourse.
*   **Written Complaint**: Submit your complaint in writing and get a "Received" stamp on the photocopy.
*   **Escalation**: Send the complaint via Registered Post to the Deputy Commissioner of Police (DCP/SP) of the district.
*   **The Legal Hammer**: Under **Section 175(3) of BNSS (formerly 156(3) CrPC)**, you can approach the Magistrate Court. The Magistrate can *order* the police to register the FIR. Mentioning "Section 175(3)" to a reluctant officer often motivates them to do their job.

### 6.4. The Evidence Package
When you go to the station, bring the "Golden Package" to make their job easier:
*   **The Money Trail**: Printed bank statement highlighting the debit.
*   **The Cyber Trail**: Color printouts of the WhatsApp chat/call logs.
*   **The Acknowledgement**: A printout of the 1930/Cybercrime.gov.in receipt.
*   **ID Proof**: Your Aadhaar/PAN copy.
Police are overworked; giving them a neat, organized file increases the speed of your registration.

---

## 7. After 24 hours: Ongoing steps

### Week 1

- [ ] Follow up with bank on dispute status
- [ ] Check cybercrime.gov.in for case updates
- [ ] Visit police station if IO (Investigating Officer) assigned
- [ ] Freeze CIBIL report if identity theft suspected

### Week 2-4

- [ ] Provide additional evidence if requested by IO
- [ ] Follow up on IO's progress
- [ ] Escalate to DCP/SP if no progress
- [ ] Consider legal counsel if large amount involved

### Ongoing monitoring

- [ ] Monitor bank accounts for unusual activity
- [ ] Watch for secondary scam attempts ("recovery agent" scams)
- [ ] Check credit report for unauthorised accounts
- [ ] Document all follow-up actions

---

## 8. What NOT to do

### Don't delay
Every minute reduces recovery chances. Stop everything else and start the protocol.

### Don't pay "recovery agents"
Scammers target victims again with fake recovery offers. No legitimate agency charges upfront fees to recover stolen money.

### Don't delete evidence
Even if embarrassing, preserve everything. Courts and police need original evidence.

### Don't confront the scammer
This alerts them to move money faster and may expose you to retaliation.

### Don't go public on social media first
File reports first, then share if you want. Public shaming doesn't recover money.

### Don't blame yourself excessively
These are professional criminals. Focus on recovery, not self-recrimination.

---

## 9. Reporting procedures by crime type

| Crime Type | Primary Report | Secondary Steps |
|------------|----------------|-----------------|
| UPI fraud | 1930 + Bank + cybercrime.gov.in | UPI app dispute |
| Net banking hack | Bank fraud helpline immediately | Password reset from secure device |
| Credit card fraud | Card issuer fraud line | Dispute letter, FIR |
| Investment scam | cybercrime.gov.in + SEBI (if securities) | Economic Offences Wing |
| Job scam | cybercrime.gov.in + local FIR | Labour department if employer impersonated |
| Loan app harassment | RBI Sachet Portal + FIR | Document all contact |
| Sextortion | Cyber cell FIR (not local PS) | Don't pay, preserve evidence |
| Identity theft | CIBIL freeze + FIR | Monitor all accounts |

---

## 10. Bank dispute process

### RBI guidelines on fraud liability

Under RBI's 2017 Circular on Customer Liability in Unauthorised Electronic Transactions:

**Zero liability for customer if**:
- Fraud due to bank system/third-party breach
- Customer reports within 3 working days

**Limited liability (up to ₹10,000) if**:
- Reported within 4-7 working days

**Full liability on customer if**:
- Customer negligence (shared OTP, PIN)
- Reported after 7 days

**Key point**: Speed of reporting directly affects liability.

### Escalation path if bank doesn't respond

1. **Branch Manager** (within 7 days)
2. **Nodal Officer** (contact on bank website)
3. **Banking Ombudsman** (within 30 days of no response)
   - File at https://cms.rbi.org.in
   - Free service
4. **Consumer Court** (if large amount, bank unresponsive)

---

## 11. Contact directory

### Emergency contacts

| Service | Number | When to Use |
|---------|--------|-------------|
| Cyber Crime Helpline | 1930 | First call for all cybercrimes |
| Women Helpline | 181 | Cyberstalking, harassment of women |
| Child Helpline | 1098 | Crimes involving minors |
| National Emergency | 112 | Life-threatening situations |

### Reporting portals

| Portal | URL | Purpose |
|--------|-----|---------|
| National Cybercrime Portal | https://cybercrime.gov.in | All cybercrimes |
| RBI Sachet | https://sachet.rbi.org.in | Illegal financial apps, loan harassment |
| SEBI SCORES | https://scores.gov.in | Securities fraud, investment scams |
| NPCI Dispute | https://www.npci.org.in/upi-dispute-redressal-mechanism | UPI transaction disputes |
| Banking Ombudsman | https://cms.rbi.org.in | Bank complaint escalation |

### State cyber cells

Available at: https://cybercrime.gov.in/Webform/Statedetails.aspx

Major cities:
- **Mumbai Cyber Cell**: 022-26941444
- **Delhi Cyber Cell**: 011-23490466
- **Bangalore Cyber Cell**: 080-22942222
- **Chennai Cyber Cell**: 044-28447777
- **Hyderabad Cyber Cell**: 040-27852040
- **Kolkata Cyber Cell**: 033-22143000

---

## 12. Sources

1. Indian Cyber Crime Coordination Centre (I4C), Ministry of Home Affairs: https://cybercrime.gov.in
2. Reserve Bank of India, Customer Protection – Limiting Liability (2017): https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11040
3. National Payments Corporation of India, Dispute Redressal: https://www.npci.org.in/what-we-do/upi/upi-dispute-redressal-mechanism
4. Bureau of Police Research and Development, Cybercrime Investigation Manual
5. Ministry of Electronics and IT, Cyber Security Framework Guidelines
6. RBI Banking Ombudsman Scheme: https://rbi.org.in/scripts/Complaints.aspx
