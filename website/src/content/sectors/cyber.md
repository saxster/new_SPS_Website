---
title: "Individual Cyber Defence"
icon: "🔒"
description: "A plain-language cyber safety framework for Indian households and professionals--built on data protection law, modern threat patterns, and practical daily habits."
risks:
  - "Impersonation and social-engineering scams"
  - "Payment fraud (UPI, cards, net-banking)"
  - "Account takeover and SIM swap"
  - "Malware and remote-access abuse"
regulations:
  - "Digital Personal Data Protection (DPDP) Act, 2023"
  - "Information Technology Act, 2000"
  - "CERT-In Directions (2022)"
  - "NIST Cybersecurity Framework 2.0 (best-practice reference)"
  - "ISO/IEC 27001:2022 (security management standard)"
---

## Table of Contents
1. Sector snapshot
2. Key definitions (plain language)
3. The legal and standards context
4. Risk map (what actually happens)
5. Personal cyber-defence framework
6. Family safety protocols
7. Incident response (what to do if it goes wrong)
8. Metrics and self-checks
9. Sources

---

## 1. Sector snapshot
India's digital life is now inseparable from everyday life--banking, healthcare, education, and work. This creates enormous convenience, but also a wider attack surface. The Digital Personal Data Protection (DPDP) Act establishes a legal expectation that personal data is safeguarded, and the Information Technology Act defines cyber offences and penalties. These laws set the baseline for how data must be handled and what constitutes cybercrime.

## 2. Key definitions (plain language)
- **Personal data**: Any data that can identify you directly or indirectly (name, phone number, biometrics, location).
- **Phishing**: A fake message or website designed to trick you into sharing passwords or OTPs.
- **Social engineering**: Psychological manipulation to make you reveal sensitive information or transfer money.
- **Multi-factor authentication (MFA)**: A second step (like an app code) in addition to a password.

## 3. The legal and standards context
- **DPDP Act, 2023**: Defines obligations around personal data handling and safeguards.
- **IT Act, 2000**: Establishes cyber offences and penalties.
- **CERT-In Directions (2022)**: Require regulated entities and service providers to report certain cyber incidents and maintain logs; this shapes how platforms respond to consumer incidents.
- **NIST CSF 2.0 and ISO 27001**: Global best-practice references for risk management and security controls.

## 4. Risk map: What actually happens

### 4.1. Impersonation and "Digital Arrest" scams
The most sophisticated threat in 2025 is the "Digital Arrest" scam. Fraudsters pose as officials from the CBI, Narcotics Bureau, or Cyber Police via video call. They use fake uniforms and office backgrounds to "arrest" the victim digitally, claiming their Aadhaar is linked to money laundering or narcotics. They isolate the victim, forbidding them from ending the call or contacting family, and eventually demand a "settlement" or "verification fee" via UPI to clear their name.

### 4.2. Payment fraud and UPI "Collect Request" traps
India's UPI ecosystem is a primary target. Scammers send a "Collect Request" but frame it as a "Refund" or "Cashback" approval. They pressure the victim to enter their UPI PIN "to receive money." **Rule of Life**: You never need to enter a PIN to *receive* money. Another variation is the "Fake Customer Care" number on Google Maps, which leads victims directly to a fraudster who then requests a small "registration fee" to solve their problem.

### 4.3. Account takeover and SIM swap fraud
In a SIM swap attack, the fraudster gathers the victim's personal details (Aadhaar, DOB) and then convinces the telecom provider to issue a "Replacement SIM" under a fake lost-SIM claim. Once the victim's phone goes dead, the fraudster has the active SIM and can receive all banking OTPs, allowing them to reset passwords and drain bank accounts in minutes. This is often preceded by "Phishing" emails that steal the initial login credentials.

### 4.4. Remote-access abuse and "Support" scams
Fraudsters often pose as technical support from Microsoft, Apple, or a banking app. They trick the victim into installing remote-access tools like AnyDesk or TeamViewer to "fix a security issue." Once installed, the fraudster can see the victim's screen and control their mouse. They will ask the victim to log into their bank account "for verification," allowing the fraudster to steal the password and OTP as it appears on the screen.

### 4.5. Data leakage and "Identity Cloning"
Personal documents (Aadhaar, PAN, Passport) shared loosely over WhatsApp or stored in unencrypted email folders are frequently leaked in mass data breaches. Fraudsters use these to "Clone" identities—opening bank accounts (Mule accounts) or taking out "Instant Loans" in the victim's name. The victim often only realizes the theft when they receive a default notice from a bank they never visited.

## 5. Personal cyber-defence framework

### 5.1. Identity protection: Beyond the password
The era of the "Memorable Password" is over. We mandate the use of a **Password Manager** (like Bitwarden or 1Password) to generate and store unique, 16-character passwords for every site. More importantly, turn on **Multi-Factor Authentication (MFA)** on all critical accounts (Email, Bank, Social Media). Prefer "Authenticator Apps" (Google Authenticator, Microsoft Authenticator) over SMS OTPs, as these are immune to SIM swap attacks.

### 5.2. Transaction safety: The "UPI PIN" Protocol
Treat your UPI PIN like your ATM PIN—never share it, and never enter it to receive money. Establish a **Low-Limit Account** for daily UPI transactions (e.g., linked to a separate bank account with only ₹5,000 balance). Keep your primary savings in a different bank account with no UPI linkage and no debit card carried in your wallet. This creates a "Firewall" between your daily spending and your life savings.

### 5.3. Device hygiene: The Update Habit
Your phone and laptop are your most vulnerable endpoints. Enable **Automatic Updates** for the Operating System (OS) and all apps. These updates are rarely about "new features" and almost always about "security patches" for vulnerabilities that hackers are already exploiting. Never install "Modded" apps or APKs from unknown websites; these are frequently backdoored to steal your data in the background.

### 5.4. Data minimisation: The "Masking" Rule
Stop sharing full Aadhaar or PAN card copies with every hotel or security desk. Use the **Masked Aadhaar** (which hides the first 8 digits) provided by UIDAI. When you must share a document, add a physical or digital **Watermark** across the center: "Shared with Hotel X on 20 Jan 2026 for KYC only." This prevents the document from being reused for a fraudulent loan or SIM card application.

## 6. Family safety protocols

### 6.1. The "Safe-Word" Rule
In the age of AI-generated "Voice Cloning," you can no longer trust a voice on the phone claiming to be your child in trouble. Establish a family **Safe-Word**—a secret word or phrase known only to your inner circle. If someone calls from an unknown number claiming an emergency, ask for the safe-word. If they can't provide it, hang up immediately; it is a scam.

### 6.2. The "Verification Habit"
Establish a family culture where "Urgency is a Red Flag." If a relative or friend sends a message (on WhatsApp/Telegram) asking for an urgent money transfer because they are "stuck at a hospital" or "lost their wallet," do not act. Call them back on their *saved* contact number. If they don't answer, wait. Scammers rely on the "Urgency spell" to bypass your critical thinking.

### 6.3. Elder Protection: The "Call First" Rule
Seniors are the primary targets for "Digital Arrest" and "KYC Update" scams. Set up their phones with a "Trusted Contact List" and establish a firm **Call First** rule: they must call you before sharing an OTP, clicking a link, or following instructions from any "official" caller. Review their bank statements once a month for small "test" transactions that might indicate an ongoing compromise.

## 7. Incident response: What to do if it goes wrong

### 7.1. Immediate Containment (The First 10 Minutes)
If you realize you've been scammed or your account is compromised:
*   **Disconnect**: Turn off the Wi-Fi and mobile data on your device immediately.
*   **Revoke Sessions**: Log in from a clean device and use the "Sign out of all other sessions" feature in Google/Facebook/Bank settings.
*   **Change Passwords**: Change the password for the compromised account AND your primary email account, as that is the key to all other resets.

### 7.2. Notification and Financial Freeze
Time is money.
*   **Call 1930**: This is the National Cyber Crime Helpline. They can coordinate with banks to "Freeze" the recipient's account, potentially stopping the money before it is withdrawn at an ATM.
*   **Bank Portal**: Use your bank's app to "Block" your cards and disable UPI/Net-banking immediately. Document the "Transaction Reference Number" for every fraudulent debit.

### 7.3. Reporting and Documentation
File a formal complaint at **[cybercrime.gov.in](https://cybercrime.gov.in)**. Provide every detail: the scammer's phone number, the UPI ID used, screenshots of the conversation, and the timestamp of the calls. This digital trail is essential for the police to build a case and for you to claim insurance (if applicable). Never pay a "Recovery Agent" who promises to get your money back; these are secondary scams targeting victims.

## 8. Metrics and self-checks
- **Account coverage**: % of accounts with MFA enabled.
- **Update hygiene**: Last OS and app update date.
- **Exposure check**: Count of sensitive documents stored in messaging apps or email.

## 9. Sources
1. Digital Personal Data Protection Act, 2023 (India Code).
2. Information Technology Act, 2000 (Legislative Department).
3. CERT-In Directions (2022) and FAQs (Official).
4. NIST Cybersecurity Framework 2.0.
5. ISO/IEC 27001:2022 overview.
