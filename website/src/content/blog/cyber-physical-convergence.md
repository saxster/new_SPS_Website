---
title: "The Great Convergence: When Cyber Met Physical (2026 Strategy)"
description: "Why cyber and physical security can no longer be separate. A practical framework for converged risk management in Indian enterprises."
pubDate: 2026-01-22
author: "SPS Intelligence Team"
tags: ["Strategy", "Cyber-Physical", "IoT", "Convergence", "Leadership"]
category: "Strategic Risk"
contentType: "Analysis"
wordCount: 681
qualityScore: 100
draft: false
---

## Table of Contents
1. What convergence means
2. Why the air gap disappeared
3. The drivers of convergence
4. Threat pathways you must assume
5. Risk taxonomy: safety, integrity, availability
6. Governance model for convergence
7. Technical architecture that works
8. Operational playbooks
9. Metrics that show maturity
10. Implementation roadmap
11. Sources

---

## 1. What convergence means
Cyber-physical convergence is the integration of digital security (networks, identities, data) with physical security (facilities, guards, access control). In practice, this means that cameras, access control, HVAC, and industrial systems are treated as networked endpoints with real-world impact.

## 2. Why the air gap disappeared
Most operational systems now connect to corporate networks for maintenance, analytics, or remote support. NIST's industrial control system guidance highlights the need to treat operational technology (OT) as a distinct risk domain with specialised controls. [1]

## 3. The drivers of convergence
- **Remote operations**: Vendors now maintain cameras, lifts, and BMS platforms remotely.
- **Data-driven security**: Video analytics and access logs need central processing.
- **Cost pressure**: Enterprises consolidate monitoring into a single SOC or command centre.
- **Regulatory scrutiny**: Data protection law treats CCTV and access logs as personal data. [1]

## 4. Threat pathways you must assume

### 4.1. The IT-to-OT pivot
This is the classic "Target Breach" scenario. An attacker gains a foothold in the corporate network (IT) via phishing or a web vulnerability, moves laterally, and crosses the bridge into the Operational Technology (OT) or Physical Security network. Once inside, they can disable cameras, unlock doors, or manipulate HVAC systems to cause physical damage. The assumption must be that the corporate network is already compromised; the physical security network must defend itself against the corporate network.

### 4.2. Vendor and supply-chain access
Most physical security systems (VMS, Access Control) are maintained by external system integrators who often use remote access tools (TeamViewer, AnyDesk) or VPNs. If the vendor's laptop is compromised, the attacker has a direct, privileged tunnel into the heart of your physical security. This "trusted path" is a primary vector because it bypasses the firewall's perimeter defences.

### 4.3. Insecure edge devices
Cameras and door controllers are effectively small Linux computers dangling on the outside of your building. They are often unpatched, have default passwords, and are physically accessible. An attacker can unscrew a camera, plug into the ethernet port, and if the network is not secured with 802.1x NAC (Network Access Control), they are on the internal network. These "Edge Devices" are the soft underbelly of the converged architecture.

### 4.4. Misconfiguration and shared credentials
The most common vulnerability is not a zero-day exploit, but simple negligence. We frequently find "admin/admin" credentials on critical controllers, or database ports exposed to the entire network. Shared accounts (e.g., a single "GuardDesk" login used by 20 guards) make accountability impossible and allow an insider threat to act with anonymity. Basic cyber hygiene is the first line of defence.

## 5. Risk taxonomy: safety, integrity, availability
Converged risk is not only about data theft. It has three layers:
- **Safety**: harm to people due to system manipulation (lifts, fire systems, OT).
- **Integrity**: unauthorised changes to access policies, footage, or logs.
- **Availability**: downtime of cameras, alarms, or industrial processes.

If a control reduces cyber risk but creates safety risk, it is not acceptable. This is why OT security needs its own discipline. [1]

## 6. Governance model for convergence

### 6.1. Joint ownership and the "Security Council"
Convergence fails when it is a turf war. The CISO (Chief Information Security Officer) and CSO (Chief Security Officer) must move from a "Consulted" relationship to a "Joint Ownership" model. This is best operationalized through a "Converged Security Council"—a monthly steering committee that reviews the combined risk register. They must share a single budget line for "Security Technology" to prevent the CSO from buying cheap, insecure cameras that the CISO then has to block.

### 6.2. Unified incident response
In a crisis, minutes matter. If the SOC (Security Operations Centre) sees a network alarm from the warehouse, and the Physical Security Command Centre sees a door alarm at the same time, they usually work in silos. A converged model requires a "Unified Triage Path": a single workflow where physical and digital alerts are correlated. If a badge is used at a door (Physical) but the user's laptop is logged in from another country (Cyber), the system should automatically flag the "Impossible Travel" anomaly.

### 6.3. Shared asset inventory
You cannot protect what you cannot see. Currently, the CSO tracks cameras in an Excel sheet, and the CISO tracks servers in a CMDB. Convergence requires a "Single Source of Truth"—a unified asset inventory that lists every IP-connected physical device. This allows the CISO to see the "security debt" (unpatched cameras) and the CSO to see the operational status of their fleet.

### 6.4. Change control and vendor governance
Physical security upgrades often break cybersecurity rules. A new "License Plate Recognition" system might require opening firewall ports. Under a converged model, all physical security changes must pass through the IT Change Control Board (CCB). Conversely, IT patches that might reboot the video recording server must be coordinated with Physical Security to ensure no "blind time" occurs during critical shifts. Contracts with vendors must now include specific cybersecurity SLAs—patch times, liability for breaches, and strict access protocols.

## 7. Technical architecture that works

### 7.1. Network segmentation and "Air Gaps"
The "flat network" is the enemy. The architecture must strictly segment traffic. Corporate IT users (laptops, phones) should never be able to directly route to the Physical Security network. This is achieved through VLANs and Firewalls. Ideally, the Physical Security Network (PSN) acts as an "OT Zone"—a protected enclave that only allows specific, monitored traffic (conduits) in and out. This limits the "Blast Radius": if a receptionist's PC is infected, the malware cannot jump to the access control server.

### 7.2. Zones and conduits (ISA/IEC 62443)
We adopt the ISA/IEC 62443 standard, which treats the system as a collection of "Zones" (groups of assets with similar security requirements) connected by "Conduits" (communication channels). For example, the "Camera Zone" needs to talk to the "Recording Zone," but it does not need to talk to the "Printer Zone." By defining these allowed conduits explicitly, we deny all other traffic by default, creating a "Zero Trust" environment for physical devices.

### 7.3. Secure remote access
Vendor remote access is necessary but dangerous. We move away from "Always-On" VPNs to "Just-in-Time" (JIT) access. Vendors must authenticate via a Privileged Access Management (PAM) portal with Multi-Factor Authentication (MFA). Their session is recorded (video logged), and access is granted only for a specific time window (e.g., "Tuesday 2 PM - 4 PM") associated with a specific Change Request ticket.

### 7.4. Logging and monitoring
A camera going offline is often treated as a maintenance issue. In a converged world, it is a potential security event. All logs from physical security devices (syslogs, audit trails) must be forwarded to the corporate SIEM (Security Information and Event Management) system. This allows the SOC to write detection rules: "If a camera goes offline AND a door is forced open within 1 minute at the same location, trigger a Critical Alert." This correlation is the "Holy Grail" of convergence.

## 8. Operational playbooks

### 8.1. Integrated incident classification
When an alarm rings, who answers? We need a single "Incident Matrix" that classifies events based on impact, not just source. A "Door Forced" alarm might be a physical issue (guard dispatch) or a cyber issue (if the door controller was hacked). The playbook must guide the L1 analyst to ask the right questions: "Is the camera also offline? Is the controller responding to pings?" This prevents the "ping-pong" effect where teams toss the ticket back and forth.

### 8.2. Table-top exercises (TTX)
You fight like you train. Once a quarter, conduct a Table-Top Exercise that involves both the CISO and CSO teams. Scenario: "A ransomware attack has encrypted the video recording server. Simultaneously, a fire alarm triggers." This forces the teams to coordinate: does the CSO trust the fire alarm? (It might be false). Does the CISO isolate the server? (It might lose evidence). These exercises reveal the gaps in decision-making authority before a real crisis hits.

### 8.3. Forensic readiness
In a converged incident, evidence is fragile. The cyber team might want to re-image the server to get it back online, while the physical team needs the video footage for a police report. The playbook must establish "Evidence Preservation" priority. We define "Forensic Readiness" as the ability to capture volatile data (RAM, logs) and non-volatile data (video footage) without corrupting either, ensuring it stands up in court.

### 8.4. Patch windows and fail-safe design
Patching a server is routine for IT, but patching an Access Control server requires planning. If the server reboots, do the doors lock (fail-secure) or unlock (fail-safe)? The playbook must explicitly state the "Fail-State" for every device. Patching must be scheduled during low-risk windows, and guards must be on standby with physical keys in case the electronic system does not come back up. We never patch "blind"—mitigating controls must be active.

## 9. Metrics that show maturity
- % of cyber-physical assets inventoried and monitored
- Mean time to detect and respond to alerts across both domains
- Patch compliance for security devices and OT endpoints
- Number of joint exercises completed per year
- % of vendors using MFA and least-privilege access

## 10. Implementation roadmap
**0-60 days**
- Build a shared asset inventory and ownership map.
- Identify the top five cyber-physical risks and document controls.

**61-120 days**
- Segment networks and remove shared credentials.
- Create a unified incident response runbook.

**121-180 days**
- Integrate monitoring and run a full-scale exercise.
- Establish a quarterly convergence review.

## 11. Sources
1. NIST SP 800-82 Rev. 3, Guide to Industrial Control Systems Security: https://csrc.nist.gov/pubs/sp/800/82/r3/final
2. MITRE ATT&CK for ICS matrix: https://attack.mitre.org/matrices/ics/
3. ISA/IEC 62443 series overview: https://www.isa.org/standards-and-publications/isa-standards/isa-iec-62443-series-of-standards
