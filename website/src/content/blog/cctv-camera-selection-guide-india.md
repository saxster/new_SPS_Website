---
title: "CCTV Camera Selection Guide: A Technical Framework for Indian Facilities"
description: "A comprehensive guide to selecting the right CCTV cameras for your facility. Covers IP vs analog, resolution, low-light performance, compression codecs, and sector-specific recommendations."
pubDate: 2026-01-18
author: "SPS Technical Team"
tags: ["CCTV", "Surveillance", "Technical Guide", "IP Cameras", "Security Infrastructure"]
category: "Surveillance"
contentType: "Technical Guide"
wordCount: 2850
qualityScore: 100
megatrend: "Perimeter & Detection"
draft: false
---

## Table of Contents
1. Why camera selection matters
2. IP vs Analog: The fundamental choice
3. Resolution: When more megapixels actually help
4. Low-light performance: Starlight, IR, and WDR
5. Lens types and field of view
6. Compression codecs: H.264, H.265, and beyond
7. Camera form factors
8. Environmental considerations for India
9. Sector-specific recommendations
10. Common mistakes to avoid
11. Decision matrix
12. Sources

---

## 1. Why camera selection matters

The difference between a useful surveillance system and an expensive liability often comes down to camera selection. A poorly chosen camera delivers:
- **Unusable footage** when it matters most (low light, fast motion, wide areas)
- **Excessive storage costs** from inefficient compression
- **False sense of security** from blind spots and resolution gaps
- **Legal rejection** when footage cannot identify individuals or events

Indian facilities face specific challenges: extreme temperature swings (0-50°C across regions), dust and pollution, monsoon humidity, and power fluctuations. A camera that works in Singapore may fail in Rajasthan.

This guide provides a technical framework for matching camera specifications to operational requirements.

---

## 2. IP vs Analog: The fundamental choice

### 2.1. The Analog Legacy (HD-TVI/CVI)
Analog cameras transmit raw video signals over coaxial cable (RG59) to a DVR. While they have evolved to support HD resolutions (up to 5MP), they remain "dumb" devices. They simply send a picture; they cannot process it. The primary advantage is cost and simplicity—if you have existing coaxial cabling from a 10-year-old system, upgrading to HD-Analog is cheaper than rewiring the entire building for Ethernet. However, they lack the scalability and intelligence required for modern security operations.

### 2.2. The IP Advantage (Network Cameras)
IP cameras are essentially small computers with a lens. They compress video at the edge and transmit data packets over Ethernet. This architecture allows for **Edge Analytics**—the camera itself can detect a "Line Crossing" or "loitering" without needing a central server. Crucially, **Power over Ethernet (PoE)** simplifies installation by carrying both power and data on a single Cat6 cable. For any new greenfield project in 2026, IP is the only logical choice due to its infinite scalability and integration capabilities with Access Control and Fire systems.

### 2.3. The Verdict for 2026
The price gap has narrowed to the point of irrelevance. A high-quality 4MP IP camera now costs only marginally more than a premium Analog equivalent. The Total Cost of Ownership (TCO) for IP is often lower because of reduced cabling costs (PoE) and easier maintenance. We recommend Analog only for legacy retrofits where re-cabling is physically impossible; for everything else, deploy IP.

## 3. Resolution: When more megapixels actually help

### 3.1. The "Pixels per Metre" (PPM) Rule
Resolution is not about pretty pictures; it is about forensic density. To identify a stranger (admissible in court), you need approximately **80-100 Pixels per Metre (PPM)** of the target's width at the point of interest. A 2MP (1080p) camera typically provides this density only up to 5-8 meters. If you are trying to read a license plate at 20 meters, a 2MP camera will yield a pixelated blur. This math—not marketing hype—should drive your sensor selection.

### 3.2. 4K (8MP) vs. 2MP: The Use Case
Higher resolution allows for "Digital Zoom" during post-incident investigation. A single 4K (8MP) camera can cover a wide parking lot while still allowing the operator to zoom in and read a number plate in the corner of the frame. This "Multi-Purpose" capability often means you can replace two 2MP narrow-view cameras with one 4K wide-angle camera, saving on installation and licensing costs.

### 3.3. The "Megapixel Trap"
More is not always better. Higher resolution reduces low-light performance because the pixels on the sensor are smaller and capture less light. A 12MP camera might look amazing in daylight but turn completely grainy (noise) at night. For dimly lit perimeter walls, a high-quality 4MP camera with a larger sensor (1/1.8") will outperform a cheap 8MP camera with a tiny sensor (1/2.8").

## 4. Low-light performance: The real differentiator

### 4.1. Minimum Illumination and Lux Ratings
The most critical spec for 24/7 security is the "Minimum Illumination" rating. Standard cameras need 0.1 Lux (office lighting). High-performance security cameras operate at 0.005 Lux (Starlight). Ignore the "0 Lux with IR" marketing claim; IR gives you a black-and-white image. True security requires **Color at Night** to identify the colour of a getaway car or the intruder's clothing.

### 4.2. Starlight and "DarkFighter" Technology
Modern sensors use "Back-Illuminated" technology (Starvis/Starlight) to amplify available light. This allows the camera to stay in "Color Mode" even under streetlights, providing far richer forensic detail than grainy IR footage. For critical zones like main gates and perimeter walls, investing in Starlight technology is mandatory; it turns the night into twilight.

### 4.3. True WDR (Wide Dynamic Range)
In India, entrances often face harsh sunlight while the interior is dark. A standard camera will show either a "White-out" outdoors or a "Silhouette" indoors. **True WDR (120dB)** takes multiple exposures (short and long) and combines them, allowing you to see the face of the person entering *and* the car parked outside simultaneously. This is non-negotiable for any camera facing a glass door or window.

---

## 5. Lens types and field of view

The lens determines what the camera sees. The key specification is **focal length** measured in millimetres (mm).

### Fixed lens cameras
- **2.8mm**: ~110° horizontal FOV (wide, for small rooms, corridors)
- **4mm**: ~85° horizontal FOV (standard, most common)
- **6mm**: ~55° horizontal FOV (narrow, for longer distances)
- **12mm**: ~30° horizontal FOV (telephoto, specific targets)

### Varifocal lens cameras
Adjustable focal length (e.g., 2.8-12mm) allows tuning the field of view during installation. Costs ₹2,000-5,000 more than fixed lens.

**Use case**: When you cannot predict exact coverage needs or want flexibility for repositioning.

### Motorised zoom (PTZ)
Pan-Tilt-Zoom cameras can move and zoom remotely. Focal lengths from 4mm to 200mm+.

**Use case**: Large open areas (warehouses, campuses) where a single camera can cover multiple zones when directed by an operator or analytics.

### Fisheye/Panoramic
180° or 360° field of view from a single camera. Software "dewarps" the image for viewing.

**Use case**: Lobbies, conference rooms, retail floors where wall mounting is impractical.

### Field of view calculation
Horizontal FOV = 2 × arctan(sensor width ÷ 2 × focal length)

For a 1/2.8" sensor (common in 4MP cameras) with 4mm lens:
- Sensor width: 5.04mm
- FOV = 2 × arctan(5.04 ÷ 8) = 64.7°

---

## 6. Compression codecs: H.264, H.265, and beyond

Compression determines how much storage and bandwidth your footage requires. The codec (compressor-decompressor) is the algorithm that shrinks video data.

### H.264 (AVC)
- **Status**: Legacy standard, universal compatibility
- **Efficiency**: Baseline for comparison
- **Compatibility**: Works with all NVRs, VMS, and players
- **Use case**: When maximum compatibility is required

### H.265 (HEVC)
- **Status**: Current standard (2013+)
- **Efficiency**: 50% less storage than H.264 at same quality
- **Compatibility**: Requires newer NVRs (2016+)
- **Use case**: Default choice for new installations

### H.265+ / Smart Codecs
Vendor-specific optimisations (Hikvision H.265+, Dahua Smart H.265) that reduce bitrate further for static scenes.

- **Efficiency**: Up to 80% reduction for low-motion scenes
- **Compatibility**: Requires same-brand NVR
- **Use case**: 24/7 recording of static areas (server rooms, vaults)

### Storage impact example
8 cameras × 4K resolution × 25 FPS × 24/7 × 30 days:

| Codec | Bitrate/cam | Daily/cam | 30-day total |
|-------|-------------|-----------|--------------|
| H.264 | 8 Mbps | 86 GB | 20.6 TB |
| H.265 | 4 Mbps | 43 GB | 10.3 TB |
| H.265+ | 2 Mbps | 22 GB | 5.2 TB |

The storage cost difference over 5 years is substantial.

---

## 7. Camera form factors

### Dome cameras
- **Appearance**: Hemispherical housing
- **Advantages**: Vandal-resistant, discreet, difficult to determine viewing direction
- **Disadvantages**: Limited IR range, lens swap may require opening dome
- **Best for**: Indoor ceilings, retail, offices, areas with vandalism risk

### Bullet cameras
- **Appearance**: Cylindrical, often with visible IR array
- **Advantages**: Long IR range, easy lens adjustment, clear deterrence
- **Disadvantages**: More obtrusive, easier to redirect or block
- **Best for**: Outdoor perimeters, parking lots, building exteriors

### Turret/Eyeball cameras
- **Appearance**: Ball-in-socket design
- **Advantages**: Flexible mounting angle, balance of dome and bullet features
- **Disadvantages**: Less vandal-resistant than dome
- **Best for**: Versatile indoor/outdoor installations

### Box cameras
- **Appearance**: Traditional rectangular body, requires separate lens
- **Advantages**: Maximum flexibility, interchangeable lenses, industrial use
- **Disadvantages**: Separate housing required for outdoor use
- **Best for**: Specialised applications requiring custom optics

### PTZ cameras
- **Appearance**: Large dome or pendant mount
- **Advantages**: Remote control, wide area coverage with single camera
- **Disadvantages**: Complex, expensive (₹30,000-2,00,000), mechanical wear
- **Best for**: Manned control rooms, large open areas, VIP protection

---

## 8. Environmental considerations for India

### Temperature
- **Operating range**: Verify -10°C to +60°C for outdoor use
- **North India**: Winter night temperatures can drop to -5°C (Kashmir, Himachal)
- **Central/West India**: Summer temperatures exceed 45°C (Rajasthan, Gujarat, Vidarbha)
- **Solution**: Cameras with built-in heaters and cooling fans, or industrial-grade enclosures

### Dust and pollution
- **IP rating**: Minimum IP66 for outdoor (dust-tight, water jets)
- **Lens cleaning**: Wiper-equipped cameras for highway, industrial, or construction sites
- **Dome material**: Polycarbonate yellows over time; specify optical-grade or glass

### Monsoon and humidity
- **Ingress protection**: IP67 (immersion-resistant) for flood-prone areas
- **Condensation**: Anti-fog coatings and ventilation for dome cameras
- **Cable entry**: Downward-facing or sealed glands to prevent water ingress

### Power supply
- **Voltage tolerance**: Wide-range PoE injectors (44-57V) or UPS-backed switches
- **Surge protection**: Essential in lightning-prone areas (Karnataka, Kerala coast)
- **Backup**: PoE switches on UPS for uninterrupted recording during outages

---

## 9. Sector-specific recommendations

### Banks and NBFCs
- **Resolution**: 4K minimum for cash counters, ATM areas
- **Features**: Starlight, WDR, face capture analytics
- **Retention**: 90 days (RBI guideline)
- **Special**: Covert cameras in ATM fascia, ANPR for vehicle entrance

### Schools (CBSE/State Board)
- **Resolution**: 4MP standard, 4K for main gates
- **Features**: Wide-angle for classrooms, covered walkways
- **Retention**: 60 days minimum
- **Special**: Child-safe mounting heights, no cameras in washrooms/changing areas

### Hospitals
- **Resolution**: 4MP for corridors, 4K for pharmacy, ICU entry
- **Features**: Low-light for wards (patients rest), WDR for entrances
- **Retention**: 30 days minimum
- **Special**: Privacy masking for patient beds, integration with nurse call

### Jewellery retail
- **Resolution**: 4K for display counters, vaults
- **Features**: Starlight, face capture, tamper detection
- **Retention**: 45 days (BIS standard)
- **Special**: Undercover cameras in showcase, time-lapse for closing reconciliation

### Warehouses and logistics
- **Resolution**: 5MP for loading docks, 4MP for aisles
- **Features**: License plate capture at gates, thermal for perimeter
- **Retention**: 30 days minimum
- **Special**: Forklift-mounted cameras, integration with WMS for inventory discrepancy

### Residential societies
- **Resolution**: 4MP for gates, 2MP for corridors
- **Features**: PoE for easy installation, mobile app access
- **Retention**: 15-30 days (society rules)
- **Special**: Intercom integration, visitor face capture

---

## 10. Common mistakes to avoid

### 1. Spec sheet worship
Marketing specifications (0.0001 lux, 50m IR) are measured in ideal conditions. Request sample footage from the exact camera model in similar lighting.

### 2. Ignoring storage costs
A "cheap" high-resolution camera with H.264 compression may cost more in storage over 3 years than a premium H.265+ camera.

### 3. Wrong lens for the distance
A 2.8mm wide-angle lens will not identify faces at 15 metres. Match lens focal length to your identification requirements.

### 4. Skipping site survey
Cameras work differently based on scene lighting, reflective surfaces, and movement patterns. Install one camera temporarily and review footage before committing to full deployment.

### 5. Neglecting cybersecurity
Default passwords, unpatched firmware, and cameras on the main network create serious vulnerabilities. Segment camera networks and establish firmware update policies.

### 6. Over-reliance on PTZ
PTZ cameras only look in one direction at a time. While the operator zooms on one incident, other areas are unmonitored. Use fixed cameras for continuous coverage and PTZ for investigation.

---

## 11. Decision matrix

Use this matrix to guide camera selection:

| Location Type | Resolution | Low-Light | Form Factor | Codec | Special Features |
|---------------|------------|-----------|-------------|-------|------------------|
| Main entrance | 4K | Starlight + WDR | Bullet | H.265 | ANPR if vehicles |
| Cash counter | 4K | Standard | Dome | H.265 | Face capture |
| Corridor | 2MP | IR | Dome | H.265 | - |
| Parking lot | 4MP | Starlight + IR | Bullet | H.265 | ANPR |
| Server room | 2MP | Low-light | Dome | H.265+ | Environmental sensors |
| Perimeter | 4MP | Thermal + visible | Bullet | H.265 | Intrusion detection |
| Lobby/reception | 5MP | WDR | Fisheye | H.265 | People counting |
| Warehouse aisle | 4MP | IR | Bullet | H.265 | Motion zones |
| Loading dock | 4K | Starlight + WDR | PTZ | H.265 | License plate + face |

---

## 12. Sources

1. Bureau of Indian Standards, IS 16910: CCTV Systems Code of Practice (2019)
2. Hikvision Academy, Video Surveillance Training Materials (2024)
3. IPVM, Independent Camera Testing Reports: https://ipvm.com/reports
4. National Institute of Standards and Technology (NIST), Biometric Image Quality Standards: https://www.nist.gov/programs-projects/face-recognition-vendor-test-frvt
5. Reserve Bank of India, Master Directions on Cyber Security Framework for Banks: https://www.rbi.org.in/scripts/BS_ViewMasterDirections.aspx?id=11510
6. Central Board of Secondary Education, Safety Guidelines for Schools: https://www.cbse.gov.in
