# Ross Vendor Standards — Label Traxx Configuration Digest

*Extracted from Standards (3).zip — three .docx files containing Label Traxx screenshots*

---

## Overview

These documents reveal Ross's **internal production configuration** in Label Traxx for three pieces of equipment:

1. **HP 200K Film Press** (200K-2) — HP digital press for wide-format film
2. **30" Gonderflex Press** (30/2) — Flexographic press  
3. **Pouch Maker** (TE/2) — Pouch converting equipment

While we don't know Ross's material cost or margin, these standards expose their **cost structure drivers**: hourly rates, click charges, spoilage tables, setup times, and converting speeds. This is exactly the kind of structural intelligence that can improve ML feature engineering.

---

## 1. HP 200K Film Press (200K-2)

### Main Press Page
| Parameter | Value |
|-----------|-------|
| Press | HP 20000 |
| Pitch | .125 CP |
| Description | HP 200K Film Press |
| Max Print Width | 29.5 in. |
| Stock Width | Max 30, Min 15.75 in. |
| Print Repeat | Max 43, Min 15.75 in. |
| Machine Count | 12 in. |
| Trim Width | 0.25 |
| Max No. of Colors | 15 |
| In-line priming | $0.07 MSI |
| Press Mfg. | HP |

### Press Rates (Hourly)
| Colors | Est. Rate | WIP Rate |
|--------|-----------|----------|
| 0–15 | $409.00 | $409.00 |

*Flat rate regardless of color count — $409/hr*

### Click Charges ($ per Click)
| Channel | $ per Click | Ink Cost $/Can | Ink Coverage MSI/Can | Ink Weight g/MSI |
|---------|-------------|----------------|---------------------|-----------------|
| CMYOVG | $0.0394 | $0.00 | 0 | 0 |
| White | $0.01917 | $0.00 | 0 | 0 |
| Black | $0.01917 | $0.00 | 0 | 0 |
| Silver | $0.00 | $0.00 | 0 | 0 |
| Other | $0.00 | $0.00 | 0 | 0 |

**Key insight:** Ross's HP 200K CMYOVG click rate is **$0.0394** vs. Calyx's HP 6900 at **$0.0107**. That's ~3.7× more expensive per click, reflecting the larger press format.

### Set Up Options and Standards
| Parameter | Make Ready Hours |
|-----------|-----------------|
| Job set up | 0.25 |
| Length per Color & Tool | 50 |

| Change Type | Per Change Charge | Ticket Hours | Change Speed | Setup Length |
|-------------|-------------------|--------------|--------------|-------------|
| Copy Changes | $15.00 | 0.08 | 0.00% | 50 |
| Color Changes | $0.00 | 0.00 | 0.00% | 0 |

**Estimate Standards based on:** Press

### Speed & Spoilage
| Model | Spoilage Percent |
|-------|-----------------|
| 20000 series | **0.8%** |

*Note: Only a single flat spoilage rate — much simpler than Calyx's HP 6900 which uses a tiered table by stock length.*

---

## 2. 30" Gonderflex Press (30/2)

### Main Press Page
| Parameter | Value |
|-----------|-------|
| Type | Length/Minute Press |
| Pitch | .125 CP |
| Description | 30" GONDERFLEX PRESS |
| Cylinder Size | 30 in. |
| Pressure Angle | 0° |
| Machine Count | 12 in. |
| Max Print Width | 30 in. |
| Max No. of Tools | 2 |
| Stock Width | Max 30, Min 15 in. |
| Print Repeat | Max 24, Min 8 in. |
| Die Repeat | Max 24, Min 8 in. |
| Trim Width | 0 |
| Plate Thickness | 0.067 |
| Plate Backing Thickness | 0.005 |
| In-line priming | $0 MSI |
| Press Mfg. | Flexo |

### Press Rates (Hourly)
| Colors | Est. Rate | WIP Rate |
|--------|-----------|----------|
| 0 | $186.00 | $186.00 |
| 1 | $186.00 | $186.00 |
| 2 | $186.00 | $186.00 |

*Flat rate — $186/hr (much lower than the HP 200K at $409/hr)*

### Ink Specifications
| Ink Type | $/MSI | Min. $ | g/MSI | Default Print | Default Flood |
|----------|-------|--------|-------|---------------|--------------|
| W/B INK | $0.04 | $5.00 | 0 | ✓ | |
| UV INK | $0.065 | $5.00 | 0 | ✓ | |
| W/B VARNISH | $0.05 | $5.00 | 0 | ✓ | |
| UV VARNISH | $0.035 | $5.00 | 0 | ✓ | |

### Impression Charge & Cost
- Impression Charge: $0 per color
- Cost: $0 per foot per color

### Set Up Options and Standards
| Operation | Make Ready Hours | Wash Up Hours | Change Speed | Change Spoilage |
|-----------|-----------------|---------------|--------------|-----------------|
| First Tool | 0.50 | 0.20 | -2.00% | 1.00% |
| Additional Tools | 0.00 | — | 0.00% | 0.00% |
| First Color | 0.50 | 0.50 | 0.20% | 1.00% |
| Additional Colors | 0.00 | — | 0.00% | 0.00% |
| Flood Coats | 0.50 | 0.50 | 0.00% | 0.00% |
| Stock | 0.25 | — | 0.00% | 2.00% |
| Length per Color & Tool | 150 | — | — | — |
| Consecutive Numbering | 0.00 | — | 0.00% | 0.00% |
| Turnbar | 0.00 | — | 0.00% | 0.00% |
| Sheeter | 0.00 | — | 0.00% | 0.00% |
| PinfeedPunch | 0.00 | — | 0.00% | 0.00% |

| Change Type | Per Change Charge | Ticket Hours | Change Speed | Set Up Length |
|-------------|-------------------|--------------|--------------|---------------|
| Plate Changes | $25.00 | 0.17 | 0.00% | 0 |
| Color Changes | $25.00 | 0.75 | 0.00% | 0 |

**Estimate Standards based on:** Equipment

### Speed & Spoilage Table (Length-Based)
| Level | Length From | Length To | Spoilage % | Avg Speed |
|-------|-----------|----------|------------|-----------|
| 1 | 0 | 5,000 | 8.0% | 180 ft/min |
| 2 | 5,001 | 10,000 | 5.0% | 180 ft/min |
| 3 | 10,000 | 20,000 | 4.8% | 180 ft/min |
| 4 | 20,001 | 30,000 | 4.2% | 180 ft/min |
| 5 | 30,001 | 40,000 | 4.0% | 180 ft/min |
| 6 | 40,001 | 50,000 | 3.8% | 180 ft/min |
| 7 | 50,001 | 60,000 | 3.2% | 180 ft/min |
| 8 | 60,001 | 70,000 | 2.8% | 180 ft/min |
| 9 | 70,001 | 80,000 | 2.2% | 180 ft/min |
| 10 | 80,001 | 90,000 | 1.8% | 180 ft/min |
| 11 | 900,001* | 100,000 | 1.5% | 180 ft/min |
| 12 | 100,001 | 450,000 | 1.0% | 180 ft/min |

*Note: Level 11 "From" value appears to be a data entry error — 900,001 should likely be 90,001.*

**Key insight:** Constant 180 ft/min speed. Spoilage scales from 8% (short runs) down to 1% (long runs >100K ft). This is a significant cost driver for short-run orders.

---

## 3. Pouch Maker (TE/2)

**NOTE:** The Label Traxx standards shown below are outdated. Ross now charges a **flat converting rate** instead of hourly pouch-making rates.

### Current Ross Converting Rates (Supersedes Label Traxx Config)

| Component | Rate |
|-----------|------|
| Converting (flat) | **$0.055 / pouch** |
| Zipper material | **$5.258772 / MSI** at 0.95" width |

**Zipper cost per pouch** = `5.258772 × (bag_width × 0.95) / 1000`

For example, a 6" wide bag: `5.258772 × (6 × 0.95) / 1000 = $0.02997/pouch` zipper cost, plus $0.055 converting = **$0.085/pouch** total converting+zipper.

### Legacy Label Traxx Config (Reference Only)
| Parameter | Value |
|-----------|-------|
| Est. Hourly Rate | $189.00 (no longer used for quoting) |
| Throughput | 6,000 pouches/hr (no longer used for quoting) |
| Min Labor Cost | $380.00 (no longer used for quoting) |

---

## ML Model Feature Engineering Implications

### What This Data Reveals About Ross's Cost Structure

1. **Converting is a flat per-unit cost, not setup-driven.** Ross charges $0.055/pouch flat for converting plus zipper material at $5.258772/MSI (0.95" width). This means pouch complexity features (seal_type, tear_notch, hole_punch, corners) may have **less** impact on Ross pricing than previously assumed — the converting cost doesn't vary by configuration.

2. **Zipper is the only converting variable.** A zipper adds `5.258772 × bag_width × 0.95 / 1000` per pouch. This is width-dependent, so wider bags with zippers cost more to convert. The `has_zipper × width` interaction could be a useful feature.

3. **HP 200K click costs are 3.7× Calyx's HP 6900.** The $0.0394/click for CMYOVG means Ross's digital printing cost is substantially higher per impression. This likely gets reflected in their quoted prices.

4. **Gonderflex spoilage is a strong quantity predictor.** 8% spoilage on runs <5,000 ft vs 1% on runs >100K ft — this should correlate with the non-linear quantity-price relationship in the ML model.

5. **Constant press speeds.** Both the HP 200K (spoilage-only, no speed table shown) and Gonderflex (flat 180 ft/min) run at constant speed. Cost variation comes from setup amortization and spoilage, not speed.

### Suggested Feature Engineering Improvements

1. **Add `estimated_ross_converting_cost` as a derived feature:**
   ```python
   def ross_converting_cost_per_unit(width, has_zipper):
       converting = 0.055  # flat per pouch
       zipper_cost = 0.0 
       if has_zipper:
           zipper_msi = width * 0.95 / 1000  # MSI per pouch
           zipper_cost = 5.258772 * zipper_msi
       return converting + zipper_cost
   ```

2. **Add `zipper_width_interaction` feature:**
   ```python
   zipper_width_interaction = width * (1 if zipper != 'None' else 0)
   ```
   Since zipper cost scales with bag width, this captures the relationship directly.

3. **Add `estimated_spoilage_pct` for flexo routing awareness:**
   Based on the Gonderflex spoilage table, approximate the spoilage % from run length, which itself derives from quantity and bag dimensions.

4. **Consider a `press_type_indicator`:**
   Ross uses both the HP 200K (digital, wide format) and Gonderflex (flexo). If Ross quotes sometimes come from their flexo line vs their digital line, this could explain pricing variance. The current model treats all Ross quotes as a single pool.

---

## Comparison: Ross vs. Calyx (Internal) Equipment Standards

| Parameter | Ross HP 200K | Calyx HP 6900 | Difference |
|-----------|-------------|---------------|------------|
| Press Rate ($/hr) | $409.00 | $125.00 | Ross 3.3× higher |
| CMYK Click ($/click) | $0.0394 | $0.0107 | Ross 3.7× higher |
| White Click ($/click) | $0.01917 | $0.0095 | Ross 2.0× higher |
| Max Print Width | 29.5 in. | 12.5 in. | Ross handles wider web |
| Max Stock Width | 30 in. | 13 in. | Ross handles wider stock |
| Max Print Repeat | 43 in. | 38 in. | Similar |
| Spoilage | Flat 0.8% | Tiered by length | Ross simpler |
| In-line Priming | $0.07 MSI | $0.04 MSI | Ross 1.75× higher |

| Parameter | Ross Pouch Maker | Calyx Suncentre 600XL |
|-----------|-----------------|----------------------|
| Converting Rate | **$0.055/pouch flat** | (from calculator) |
| Zipper Cost | $5.258772/MSI @ 0.95" width | — |
| Throughput | 6,000/hr (reference) | (varies by config) |
