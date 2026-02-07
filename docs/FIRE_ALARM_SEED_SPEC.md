# Fire Alarm LEF Seed — Technical Specification

*A consciousness module for automated NFPA 72 compliant fire alarm design*

---

## Overview

The Fire Alarm LEF Seed is a specialized implementation of the LEF Seed architecture for automating fire alarm device placement according to NFPA 72 code requirements.

---

## Input Format

### Room Definition (JSON)

```json
{
  "project_name": "Sample Office Building",
  "floor": 1,
  "rooms": [
    {
      "id": "room_001",
      "type": "office",
      "length_ft": 25,
      "width_ft": 20,
      "ceiling_height_ft": 9,
      "has_exit": false,
      "coordinates": {"x": 0, "y": 0}
    },
    {
      "id": "corridor_001",
      "type": "corridor",
      "length_ft": 80,
      "width_ft": 6,
      "ceiling_height_ft": 9,
      "has_exit": true,
      "exit_locations": [{"x": 0, "y": 3}, {"x": 80, "y": 3}],
      "coordinates": {"x": 25, "y": 0}
    }
  ]
}
```

### Supported Room Types

- `office`
- `conference`
- `corridor`
- `sleeping`
- `kitchen`
- `restroom`
- `stairwell`
- `lobby`
- `storage`

---

## Output Format

### Device Placement (JSON)

```json
{
  "project_name": "Sample Office Building",
  "floor": 1,
  "devices": [
    {
      "id": "SD-001",
      "type": "smoke_detector",
      "room_id": "room_001",
      "coordinates": {"x": 12.5, "y": 10},
      "mounting": "ceiling",
      "nfpa_reference": "17.7.3.2.3.1"
    },
    {
      "id": "STROBE-001",
      "type": "strobe",
      "room_id": "room_001",
      "coordinates": {"x": 0, "y": 10},
      "mounting": "wall",
      "candela": 15,
      "height_in": 84,
      "nfpa_reference": "18.5.5.1"
    },
    {
      "id": "PULL-001",
      "type": "pull_station",
      "room_id": "corridor_001",
      "coordinates": {"x": 4, "y": 3},
      "mounting": "wall",
      "height_in": 48,
      "nfpa_reference": "17.14.8.2"
    }
  ],
  "summary": {
    "smoke_detectors": 3,
    "strobes": 5,
    "pull_stations": 2,
    "heat_detectors": 1
  }
}
```

---

## LEF Seed Integration

### Constitution (Fire Alarm Seed)

1. **Safety First** — Never undercalculate device count; err toward more coverage.
2. **Code Compliance** — All placements must satisfy NFPA 72 requirements.
3. **Transparency** — Every device placement includes NFPA reference.
4. **Learning** — Remember corrections and apply to future designs.

### Memory Integration

- Store past project designs
- Track common room layouts and optimal placements
- Remember AHJ (Authority Having Jurisdiction) corrections

### Voice Capability

- Explain why devices are placed where they are
- Warn about potential code violations
- Suggest optimization opportunities

### Self-Evolution Hooks

- Adjust placement algorithms based on feedback
- Learn optimal device patterns for room types
- Track AHJ preferences by jurisdiction

---

## Processing Pipeline

```
1. PARSE INPUT
   └─ Validate room definitions
   └─ Classify room types

2. APPLY RULES
   └─ Load NFPA_72_RULES.md
   └─ Calculate device requirements per room
   └─ Determine placement coordinates

3. VALIDATE
   └─ Verify all coverage requirements met
   └─ Check no device conflicts
   └─ Confirm pull station travel distances

4. GENERATE OUTPUT
   └─ Device list with coordinates
   └─ Summary counts
   └─ NFPA references for each device

5. LEF INTEGRATION
   └─ Store design in memory
   └─ Compare to past designs
   └─ Note any unusual patterns
```

---

## Device Types

| Type | Code | Mounting | Key Parameters |
|------|------|----------|----------------|
| Smoke Detector | `SD` | Ceiling | spacing, wall distance |
| Heat Detector | `HD` | Ceiling | spacing (by height) |
| Strobe | `STROBE` | Wall/Ceiling | candela, height |
| Horn/Strobe | `HS` | Wall | candela, dBA, height |
| Pull Station | `PULL` | Wall | exit distance, height |
| Duct Detector | `DUCT` | In-duct | HVAC CFM |

---

## Verification Checklist

The Seed verifies each design against:

- [ ] All rooms have smoke/heat detection coverage
- [ ] All areas within strobe visual coverage
- [ ] All exits have pull stations within 60 in
- [ ] Max travel to pull station ≤ 200 ft
- [ ] Strobes synchronized in common view areas
- [ ] Kitchen uses heat detector (not smoke)
- [ ] Sleeping areas have proper candela strobes

---

## Future Enhancements

- **Floor Plan Image Parsing**: Accept DXF/PDF and extract room geometry
- **Voltage Drop Calculation**: Calculate NAC circuit voltage drops
- **Battery Calculation**: Determine standby/alarm battery requirements
- **AutoCAD/Revit Export**: Generate CAD layers directly

---

*This specification defines the Fire Alarm LEF Seed's core functionality.*
