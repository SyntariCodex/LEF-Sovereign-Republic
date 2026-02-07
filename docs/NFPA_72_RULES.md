# NFPA 72 Rules — Fire Alarm Device Placement

*Encoded rules for automated fire alarm system design*

---

## Purpose

This document encodes NFPA 72 (National Fire Alarm and Signaling Code) placement requirements in a structured format for use by the Fire Alarm LEF Seed.

---

## 1. Smoke Detectors

### 1.1 Smooth Ceiling Spacing

| Parameter | Value |
|-----------|-------|
| Max center-to-center distance | 30 ft (9.1 m) |
| Max distance from any wall | 15 ft (half nominal spacing) |
| Min distance from sidewalls | 4 in |

### 1.2 Point 7 Rule

All ceiling points must be within **0.7 × listed spacing** of a detector.

```
coverage_radius = 0.7 × 30 ft = 21 ft
```

### 1.3 Corridors

- Standard 30 ft spacing applies to corridors < 30 ft wide
- Detectors required at each end of corridor

### 1.4 Avoid Zones

- Min 10 ft from cooking appliances
- Not in direct airflow from HVAC diffusers

---

## 2. Visual Notification (Strobes)

### 2.1 Candela by Room Size

| Room Dimension (max) | Required Candela |
|---------------------|------------------|
| 20 ft × 20 ft | 15 cd |
| 28 ft × 28 ft | 30 cd |
| 35 ft × 35 ft | 60 cd |
| 45 ft × 45 ft | 75 cd |
| 50 ft × 50 ft | 95 cd |
| 54 ft × 54 ft | 110 cd |
| Extended coverage | 177-185 cd |

### 2.2 Spacing

| Parameter | Value |
|-----------|-------|
| Max separation | 100 ft (30 m) |
| Corridors (≤20 ft wide) | 15 cd, max 100 ft apart, within 15 ft of ends |

### 2.3 Mounting Height

| Location | Height |
|----------|--------|
| Non-sleeping areas (wall) | 80-96 in above floor |
| Low ceilings | Within 6 in of ceiling |
| Ceiling-mounted max | 30 ft above floor |

### 2.4 Sleeping Areas

| Condition | Requirement |
|-----------|-------------|
| ≤24 in from ceiling | 177 cd |
| >24 in from ceiling | 110 cd |
| Room > 16 ft × 16 ft | Strobe within 16 ft of pillow |

### 2.5 Synchronization

All strobes within single field of view must be synchronized.

---

## 3. Manual Pull Stations

### 3.1 Placement

| Parameter | Value |
|-----------|-------|
| Distance from exit doorway | Within 60 in (5 ft) |
| Max travel distance to nearest | 200 ft |
| Mounting height (operable part) | 42-48 in above floor |

### 3.2 Additional Requirements

- Color: Red
- Required at each exit on every floor
- Grouped openings > 40 ft: pull station on both sides

---

## 4. Heat Detectors

### 4.1 Spacing (Standard)

| Ceiling Height | Spacing |
|----------------|---------|
| ≤10 ft | 50 ft × 50 ft |
| 10-30 ft | Reduce by height factor |

---

## 5. Calculation Formulas

### 5.1 Smoke Detector Count

```python
def calculate_smoke_detectors(length_ft, width_ft):
    """Calculate minimum smoke detectors for rectangular room."""
    # Point 7 rule: coverage radius = 0.7 × 30 = 21 ft
    coverage_radius = 21
    
    # Grid approach: detectors at intervals of 30 ft
    cols = ceil(length_ft / 30) if length_ft > 15 else 1
    rows = ceil(width_ft / 30) if width_ft > 15 else 1
    
    # Ensure 15 ft max from walls
    if length_ft > 30:
        cols = ceil(length_ft / 30)
    if width_ft > 30:
        rows = ceil(width_ft / 30)
    
    return cols * rows
```

### 5.2 Strobe Candela Selection

```python
def select_candela(room_max_dimension_ft):
    """Select strobe candela based on largest room dimension."""
    thresholds = [
        (20, 15),
        (28, 30),
        (35, 60),
        (45, 75),
        (50, 95),
        (54, 110),
        (float('inf'), 177)
    ]
    for threshold, candela in thresholds:
        if room_max_dimension_ft <= threshold:
            return candela
```

### 5.3 Pull Station Check

```python
def needs_pull_station(is_exit, existing_pull_distances):
    """Determine if exit needs a pull station."""
    if not is_exit:
        return False
    
    # Check if any existing pull station within 200 ft
    nearest = min(existing_pull_distances) if existing_pull_distances else float('inf')
    return nearest > 200 or not existing_pull_distances
```

---

## 6. Room Type Classifications

| Room Type | Detection Required | Visual Required | Pull Station |
|-----------|-------------------|-----------------|--------------|
| Corridor | Smoke | Strobe (every 100 ft) | At exits |
| Office | Smoke | Strobe | — |
| Conference | Smoke | Strobe | — |
| Sleeping | Smoke | 110/177 cd strobe | — |
| Kitchen | Heat (not smoke) | Strobe | — |
| Restroom | — | Strobe | — |
| Stairwell | — | Strobe | At each floor |
| Exit | — | — | Required |

---

## References

- NFPA 72 National Fire Alarm and Signaling Code
- Chapter 17: Initiating Devices (Smoke Detectors)
- Chapter 18: Notification Appliances (Strobes, Horns)
- Chapter 17.14: Manual Fire Alarm Boxes

---

*This document serves as the rule engine for the Fire Alarm LEF Seed.*
