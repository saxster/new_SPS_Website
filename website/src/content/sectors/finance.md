---
title: "Financial Services"
icon: "🏦"
description: "A security framework for banks, NBFCs, and fintechs--integrating regulatory expectations, cyber resilience, and physical risk control across branches, ATMs, and digital channels."
risks:
  - "Account takeover and payment fraud"
  - "Insider misuse and collusion"
  - "ATM/branch physical incidents"
  - "Third-party and vendor compromise"
regulations:
  - "RBI Cyber Security Framework for Banks (2016)"
  - "RBI Master Direction: IT Framework for NBFCs (2023)"
  - "Digital Personal Data Protection (DPDP) Act, 2023"
---

## Table of Contents
1. Sector snapshot
2. Key definitions (plain language)
3. Regulatory landscape
4. Risk map (cyber + physical)
5. Control framework (governance, people, process, technology)
6. Branch and ATM security
7. Data protection and privacy
8. Incident response and resilience
9. Metrics and assurance
10. Sources

---

## 1. Sector snapshot
Financial institutions run on trust and availability. A single security failure can trigger financial loss, regulatory action, and long-term reputational harm. The Reserve Bank of India (RBI) has issued sector-specific cyber security expectations for banks and NBFCs, and India's data-protection law applies to the handling of customer data.

## 2. Key definitions (plain language)
- **SOC (Security Operations Centre)**: A team that monitors systems and responds to incidents.
- **Segregation of duties**: No single person controls an entire high-risk process (reduces fraud risk).
- **Transaction monitoring**: Rules and analytics that flag unusual activity.

## 3. Regulatory landscape
- **RBI Cyber Security Framework for Banks (2016)**: Requires a board-approved cyber security policy, continuous monitoring, and incident response readiness.
- **RBI Master Direction on IT Framework for NBFCs (2023)**: Defines governance, risk management, and security control expectations for NBFCs.
- **DPDP Act, 2023**: Establishes obligations to protect personal data.

## 4. Risk map: The Cyber-Physical Nexus

### 4.1. The "Insider Threat" and collusion
In the Indian banking context, the most damaging frauds are often internal. This involves "Privilege Misuse"—a branch manager overriding KYC norms for a mule account, or an IT administrator disabling logs to exfiltrate database records. The risk is not just theft; it is the *erosion of trust*. Collusion between a loan officer and an external valuer is a classic vector for Non-Performing Asset (NPA) creation.

### 4.2. ATM attacks: From gas cutters to "Jackpotting"
Physical attacks on ATMs have evolved. While "Gas Cutter" attacks (brute force) still happen in rural areas, urban centres face "Logical Attacks." This includes "Black Box" attacks (Jackpotting), where criminals drill a hole in the fascia, connect a laptop to the dispenser, and command it to spit out cash. This is a cyber-attack executed via physical access.

### 4.3. Third-party and API risk
Fintech integration has opened the "Walled Garden" of banking. Banks now expose APIs to Payment Aggregators and Neo-Banks. If a third-party partner has weak security, they become the "Backdoor" into the Core Banking System (CBS). The risk is "Supply Chain Compromise"—inheriting the vulnerabilities of the weakest partner in the digital ecosystem.

### 4.4. Social engineering and the "Human Firewall"
Phishing and Vishing (Voice Phishing) remain the highest volume vectors. Attackers target junior staff with "Urgent CEO Requests" to transfer funds or click malicious links. In India, "KYC Update" scams targeting customers often bleed into brand reputation damage for the bank, even if the bank's own systems were not breached.

## 5. Control framework: The RBI Mandate

### 5.1. Governance: The Board's responsibility
The RBI Master Direction (2016) makes cyber security a Board-level agenda. Banks must have a Cyber Security Operations Centre (C-SOC) that operates 24/7. Governance includes the "IS Audit"—a rigorous, independent review of the IT infrastructure. The CISO (Chief Information Security Officer) must report directly to the Risk Committee, ensuring independence from the CIO (who builds the systems).

### 5.2. People: "Maker-Checker" and Segregation of Duties (SoD)
To counter the insider threat, no single individual should have the power to execute a critical transaction from end-to-end. The "Maker-Checker" principle is mandatory: one person initiates, another approves. Access rights must be "Role-Based" (RBAC). A teller should not have access to the server room; a database admin should not have access to transfer funds.

### 5.3. Process: KYE (Know Your Employee)
Banks spend millions on KYC (Know Your Customer) but often neglect KYE. Employee background verification must be continuous, not one-time. Periodic checks on credit history and lifestyle changes can flag an employee under financial stress—a key predictor of fraud. "Mandatory Block Leave" (sending sensitive staff on 10 days leave) is a critical control to detect fraud that requires daily manual cover-ups.

### 5.4. Technology: Network segmentation and "Air Gaps"
The SWIFT network (used for international transfers) and the Core Banking System (CBS) must be strictly isolated from the corporate internet. Network Segmentation ensures that a malware infection in the HR department cannot jump to the ATM switch. For critical backups, an "Air Gap" (offline storage) is the only defence against modern ransomware that seeks to encrypt backups first.

## 6. Branch and ATM security: The Physical Shield

### 6.1. E-Surveillance and Central Monitoring
The days of the sleeping night guard at the ATM are over. Modern security relies on "E-Surveillance." This involves AI-enabled cameras and IoT sensors (vibration, heat, door contact) connected to a Command Centre. If a criminal sprays paint on the camera or shakes the machine, the system triggers a "2-Way Audio" warning ("You are being watched, police have been alerted") and automatically dispatches a Quick Response Team (QRT). This converts security from reactive to proactive.

### 6.2. Strong rooms and currency chests (IS 1550)
The heart of the branch is the Strong Room. Compliance with IS 1550 (Indian Standard for vault doors) is non-negotiable. The walls must be reinforced concrete (RCC), and the door must have a "Time Lock" that prevents opening even with the correct keys until a pre-set time. "Dual Control" applies physically here: the keys are split between the Branch Manager and the Joint Custodian.

## 7. Data protection: The New Gold

### 7.1. Encryption and masking
Data in transit (moving over the network) and data at rest (on the hard drive) must be encrypted using strong standards (AES-256). In the database, PII (Personally Identifiable Information) like Aadhaar numbers and PAN cards should be "Masked" or Tokenized. A call centre agent needs to verify the customer, but they do not need to see the full 16-digit credit card number—only the last 4 digits.

### 7.2. Data Leakage Prevention (DLP)
DLP tools monitor the "egress points"—USB ports, email attachments, and upload sites. If an employee tries to copy a file named "Customer_List_High_Net_Worth.xlsx" to a USB drive, the DLP system blocks the action and alerts the SOC. This is the primary technological control against the "Insider Threat" of data theft.

## 8. Incident response and resilience

### 8.1. The Cyber Crisis Management Plan (CCMP)
RBI requires every bank to have a CCMP. This is a "War Book." It defines exactly what happens during a breach: Who declares the disaster? Who talks to the media? Who informs the RBI (mandatory within 6 hours for certain incidents)? This plan must be tested through "Table-Top Exercises" where executives role-play a ransomware scenario to find the gaps in their decision-making.

### 8.2. Business Continuity Planning (BCP)
If the primary data centre in Mumbai floods, can the bank operate from the Disaster Recovery (DR) site in Bengaluru? BCP is about "Resilience." It tests not just the servers, but the people. Can the treasury team trade from home? Can the branch operate manually if the link is down? Regular "DR Drills" (switching live operations to the backup site) are the only way to prove this capability.

## 9. Metrics and assurance
- **Operational**: Mean time to detect and respond to incidents.
- **Governance**: % of systems with current risk assessments.
- **Access**: % of privileged accounts reviewed quarterly.

## 10. Sources
1. RBI Cyber Security Framework for Banks (2016).
2. RBI Master Direction: IT Framework for NBFCs (2023).
3. Digital Personal Data Protection Act, 2023.
