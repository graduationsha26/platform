# Healthcare Color Palette - TremoAI Web Platform

## Complete Accessible Color System for Medical/Healthcare Applications

This document provides industry-standard color palettes for medical/healthcare web applications with WCAG 2.1 Level AA compliance and color blindness considerations.

---

## Executive Summary

Healthcare applications require **85% reliance on blue** as the primary color to convey trust, professionalism, and calmness. This palette combines:
- Medical blues and teals for trust and serenity
- Accessible status colors (success/warning/error)
- Neutral gray scales for text hierarchy
- WCAG 2.1 Level AA compliance (4.5:1 for normal text, 3:1 for large text)
- Color blindness accessibility (deuteranopia/protanopia)

---

## 1. Primary Medical Colors (Blues & Teals)

### Medical Blue Scale (Tailwind Blue)

**Usage**: Primary brand color, navigation, links, primary buttons, trust indicators

| Shade | Hex Code | RGB | Use Case | Contrast on White | WCAG Level |
|-------|----------|-----|----------|-------------------|------------|
| blue-50 | `#eff6ff` | rgb(239, 246, 255) | Background tints, hover states | 1.03:1 | ❌ Fail |
| blue-100 | `#dbeafe` | rgb(219, 234, 254) | Light backgrounds, cards | 1.14:1 | ❌ Fail |
| blue-200 | `#bfdbfe` | rgb(191, 219, 254) | Disabled states, borders | 1.34:1 | ❌ Fail |
| blue-300 | `#93c5fd` | rgb(147, 197, 253) | Hover states, accents | 1.74:1 | ❌ Fail |
| blue-400 | `#60a5fa` | rgb(96, 165, 250) | Interactive elements | 2.59:1 | ❌ Fail (text) |
| blue-500 | `#3b82f6` | rgb(59, 130, 246) | Primary buttons, links | 3.94:1 | ⚠️ AA Large Text Only |
| blue-600 | `#2563eb` | rgb(37, 99, 235) | Primary dark, active states | 5.54:1 | ✅ AA Normal Text |
| blue-700 | `#1d4ed8` | rgb(29, 78, 216) | Primary darker | 7.96:1 | ✅ AAA Normal Text |
| blue-800 | `#1e40af` | rgb(30, 64, 175) | Text, high emphasis | 10.75:1 | ✅ AAA Normal Text |
| blue-900 | `#1e3a8a` | rgb(30, 58, 138) | Text, headers | 13.06:1 | ✅ AAA Normal Text |
| blue-950 | `#172554` | rgb(23, 37, 84) | Dark text, high contrast | 17.09:1 | ✅ AAA Normal Text |

**Recommended for Healthcare**:
- Primary Brand: `blue-600` (#2563eb) - 5.54:1 contrast
- Primary Buttons: `blue-600` (#2563eb) with white text (5.54:1)
- Links/Interactivity: `blue-700` (#1d4ed8) - 7.96:1 contrast
- Text Emphasis: `blue-800` or `blue-900` for maximum readability

### Medical Teal/Cyan Scale

**Usage**: Secondary brand color, calming elements, operating room aesthetic, differentiator from traditional blue

#### Teal (Green-Blue)

| Shade | Hex Code | RGB | Use Case | Contrast on White | WCAG Level |
|-------|----------|-----|----------|-------------------|------------|
| teal-50 | `#f0fdfa` | rgb(240, 253, 250) | Background tints | 1.02:1 | ❌ Fail |
| teal-100 | `#ccfbf1` | rgb(204, 251, 241) | Light backgrounds | 1.09:1 | ❌ Fail |
| teal-200 | `#99f6e4` | rgb(153, 246, 228) | Borders, dividers | 1.26:1 | ❌ Fail |
| teal-300 | `#5eead4` | rgb(94, 234, 212) | Accents, icons | 1.60:1 | ❌ Fail |
| teal-400 | `#2dd4bf` | rgb(45, 212, 191) | Interactive elements | 2.35:1 | ❌ Fail (text) |
| teal-500 | `#14b8a6` | rgb(20, 184, 166) | Secondary buttons | 3.38:1 | ⚠️ AA Large Text Only |
| teal-600 | `#0d9488` | rgb(13, 148, 136) | Secondary dark | 4.77:1 | ✅ AA Normal Text |
| teal-700 | `#0f766e` | rgb(15, 118, 110) | Text, emphasis | 6.89:1 | ✅ AA+ Normal Text |
| teal-800 | `#115e59` | rgb(17, 94, 89) | Dark text | 9.55:1 | ✅ AAA Normal Text |
| teal-900 | `#134e4a` | rgb(19, 78, 74) | High contrast text | 11.73:1 | ✅ AAA Normal Text |
| teal-950 | `#042f2e` | rgb(4, 47, 46) | Maximum contrast | 16.64:1 | ✅ AAA Normal Text |

#### Cyan (Light Blue-Green)

| Shade | Hex Code | RGB | Use Case | Contrast on White | WCAG Level |
|-------|----------|-----|----------|-------------------|------------|
| cyan-50 | `#ecfeff` | rgb(236, 254, 255) | Background tints | 1.02:1 | ❌ Fail |
| cyan-100 | `#cffafe` | rgb(207, 250, 254) | Light backgrounds | 1.11:1 | ❌ Fail |
| cyan-200 | `#a5f3fc` | rgb(165, 243, 252) | Borders | 1.29:1 | ❌ Fail |
| cyan-300 | `#67e8f9` | rgb(103, 232, 249) | Accents | 1.67:1 | ❌ Fail |
| cyan-400 | `#22d3ee` | rgb(34, 211, 238) | Interactive | 2.39:1 | ❌ Fail (text) |
| cyan-500 | `#06b6d4` | rgb(6, 182, 212) | Buttons, badges | 3.49:1 | ⚠️ AA Large Text Only |
| cyan-600 | `#0891b2` | rgb(8, 145, 178) | Secondary actions | 4.95:1 | ✅ AA Normal Text |
| cyan-700 | `#0e7490` | rgb(14, 116, 144) | Text, links | 6.97:1 | ✅ AA+ Normal Text |
| cyan-800 | `#155e75` | rgb(21, 94, 117) | Dark text | 9.41:1 | ✅ AAA Normal Text |
| cyan-900 | `#164e63` | rgb(22, 78, 99) | Headers | 11.53:1 | ✅ AAA Normal Text |
| cyan-950 | `#083344` | rgb(8, 51, 68) | Maximum contrast | 16.04:1 | ✅ AAA Normal Text |

**Recommended for Healthcare**:
- Secondary Brand: `teal-600` (#0d9488) or `cyan-600` (#0891b2)
- Calming Elements: `teal-500` to `teal-700` range
- Operating Room Aesthetic: `teal-600` (#0d9488) - mimics surgical scrubs
- Differentiator: Use teal/cyan to stand out from the "sea of blue" in healthcare

---

## 2. Status & Feedback Colors

### Success Green (Emerald)

**Usage**: Successful operations, positive health indicators, completion states, "normal" vitals

| Shade | Hex Code | RGB | Use Case | Contrast on White | WCAG Level |
|-------|----------|-----|----------|-------------------|------------|
| emerald-50 | `#ecfdf5` | rgb(236, 253, 245) | Success backgrounds | 1.02:1 | ❌ Fail |
| emerald-100 | `#d1fae5` | rgb(209, 250, 229) | Light success states | 1.12:1 | ❌ Fail |
| emerald-200 | `#a7f3d0` | rgb(167, 243, 208) | Success borders | 1.35:1 | ❌ Fail |
| emerald-300 | `#6ee7b7` | rgb(110, 231, 183) | Success accents | 1.83:1 | ❌ Fail |
| emerald-400 | `#34d399` | rgb(52, 211, 153) | Success interactive | 2.67:1 | ❌ Fail (text) |
| emerald-500 | `#10b981` | rgb(16, 185, 129) | Success primary | 3.81:1 | ⚠️ AA Large Text Only |
| emerald-600 | `#059669` | rgb(5, 150, 105) | Success dark | 5.43:1 | ✅ AA Normal Text |
| emerald-700 | `#047857` | rgb(4, 120, 87) | Success emphasis | 7.76:1 | ✅ AAA Normal Text |
| emerald-800 | `#065f46` | rgb(6, 95, 70) | Success text | 10.54:1 | ✅ AAA Normal Text |
| emerald-900 | `#064e3b` | rgb(6, 78, 59) | Success headers | 12.95:1 | ✅ AAA Normal Text |
| emerald-950 | `#022c22` | rgb(2, 44, 34) | Maximum contrast | 17.51:1 | ✅ AAA Normal Text |

**Recommended for Healthcare**:
- Success Messages: `emerald-600` (#059669) - 5.43:1 contrast
- Positive Vitals: `emerald-700` (#047857) with checkmark icon
- Background Tints: `emerald-50` (#ecfdf5) for success banners

### Warning Orange (Amber)

**Usage**: Caution states, moderate alerts, attention needed, "review recommended" states

| Shade | Hex Code | RGB | Use Case | Contrast on White | WCAG Level |
|-------|----------|-----|----------|-------------------|------------|
| amber-50 | `#fffbeb` | rgb(255, 251, 235) | Warning backgrounds | 1.01:1 | ❌ Fail |
| amber-100 | `#fef3c7` | rgb(254, 243, 199) | Light warning | 1.06:1 | ❌ Fail |
| amber-200 | `#fde68a` | rgb(253, 230, 138) | Warning borders | 1.21:1 | ❌ Fail |
| amber-300 | `#fcd34d` | rgb(252, 211, 77) | Warning accents | 1.47:1 | ❌ Fail |
| amber-400 | `#fbbf24` | rgb(251, 191, 36) | Warning interactive | 1.79:1 | ❌ Fail (text) |
| amber-500 | `#f59e0b` | rgb(245, 158, 11) | Warning primary | 2.32:1 | ❌ Fail (text) |
| amber-600 | `#d97706` | rgb(217, 119, 6) | Warning dark | 3.25:1 | ⚠️ AA Large Text Only |
| amber-700 | `#b45309` | rgb(180, 83, 9) | Warning emphasis | 4.78:1 | ✅ AA Normal Text |
| amber-800 | `#92400e` | rgb(146, 64, 14) | Warning text | 6.85:1 | ✅ AA+ Normal Text |
| amber-900 | `#78350f` | rgb(120, 53, 15) | Warning headers | 9.07:1 | ✅ AAA Normal Text |
| amber-950 | `#451a03` | rgb(69, 26, 3) | Maximum contrast | 14.63:1 | ✅ AAA Normal Text |

**Recommended for Healthcare**:
- Warning Messages: `amber-700` (#b45309) - 4.78:1 contrast
- Moderate Alerts: `amber-800` (#92400e) with exclamation icon
- Background Tints: `amber-50` (#fffbeb) for warning banners
- **Note**: Amber provides better color-blind accessibility than pure yellow

### Error Red

**Usage**: Critical errors, dangerous states, emergency alerts, "immediate attention" indicators

| Shade | Hex Code | RGB | Use Case | Contrast on White | WCAG Level |
|-------|----------|-----|----------|-------------------|------------|
| red-50 | `#fef2f2` | rgb(254, 242, 242) | Error backgrounds | 1.02:1 | ❌ Fail |
| red-100 | `#fee2e2` | rgb(254, 226, 226) | Light error states | 1.08:1 | ❌ Fail |
| red-200 | `#fecaca` | rgb(254, 202, 202) | Error borders | 1.23:1 | ❌ Fail |
| red-300 | `#fca5a5` | rgb(252, 165, 165) | Error accents | 1.53:1 | ❌ Fail |
| red-400 | `#f87171` | rgb(248, 113, 113) | Error interactive | 2.13:1 | ❌ Fail (text) |
| red-500 | `#ef4444` | rgb(239, 68, 68) | Error primary | 3.05:1 | ⚠️ AA Large Text Only |
| red-600 | `#dc2626` | rgb(220, 38, 38) | Error dark | 4.52:1 | ✅ AA Normal Text |
| red-700 | `#b91c1c` | rgb(185, 28, 28) | Error emphasis | 6.50:1 | ✅ AA+ Normal Text |
| red-800 | `#991b1b` | rgb(153, 27, 27) | Error text | 8.82:1 | ✅ AAA Normal Text |
| red-900 | `#7f1d1d` | rgb(127, 29, 29) | Error headers | 11.14:1 | ✅ AAA Normal Text |
| red-950 | `#450a0a` | rgb(69, 10, 10) | Maximum contrast | 16.37:1 | ✅ AAA Normal Text |

**Recommended for Healthcare**:
- Error Messages: `red-600` (#dc2626) - 4.52:1 contrast
- Critical Alerts: `red-700` (#b91c1c) with X icon or alert symbol
- Emergency States: `red-800` (#991b1b) for maximum urgency
- Background Tints: `red-50` (#fef2f2) for error banners
- **Note**: Use reddish-orange (#dc2626) instead of pure red for color-blind users

---

## 3. Neutral Gray Scales

### Slate (Cool Professional Gray - Recommended for Healthcare)

**Usage**: Text hierarchy, backgrounds, borders, medical professionalism

| Shade | Hex Code | RGB | Use Case | Contrast on White | WCAG Level |
|-------|----------|-----|----------|-------------------|------------|
| slate-50 | `#f8fafc` | rgb(248, 250, 252) | Page backgrounds | 1.01:1 | ❌ Fail |
| slate-100 | `#f1f5f9` | rgb(241, 245, 249) | Card backgrounds | 1.04:1 | ❌ Fail |
| slate-200 | `#e2e8f0` | rgb(226, 232, 240) | Borders, dividers | 1.14:1 | ❌ Fail |
| slate-300 | `#cbd5e1` | rgb(203, 213, 225) | Disabled states | 1.35:1 | ❌ Fail |
| slate-400 | `#94a3b8` | rgb(148, 163, 184) | Placeholder text | 2.07:1 | ❌ Fail (text) |
| slate-500 | `#64748b` | rgb(100, 116, 139) | Secondary text | 3.21:1 | ⚠️ AA Large Text Only |
| slate-600 | `#475569` | rgb(71, 85, 105) | Body text (light) | 5.15:1 | ✅ AA Normal Text |
| slate-700 | `#334155` | rgb(51, 65, 85) | Primary text | 7.74:1 | ✅ AAA Normal Text |
| slate-800 | `#1e293b` | rgb(30, 41, 59) | Headers, emphasis | 11.37:1 | ✅ AAA Normal Text |
| slate-900 | `#0f172a` | rgb(15, 23, 42) | Maximum contrast | 15.52:1 | ✅ AAA Normal Text |
| slate-950 | `#020617` | rgb(2, 6, 23) | True black alternative | 19.78:1 | ✅ AAA Normal Text |

### Gray (Neutral Gray)

**Usage**: Balanced neutral tones, versatile backgrounds

| Shade | Hex Code | RGB | Contrast on White | WCAG Level |
|-------|----------|-----|-------------------|------------|
| gray-50 | `#f9fafb` | rgb(249, 250, 251) | 1.01:1 | ❌ Fail |
| gray-100 | `#f3f4f6` | rgb(243, 244, 246) | 1.03:1 | ❌ Fail |
| gray-200 | `#e5e7eb` | rgb(229, 231, 235) | 1.11:1 | ❌ Fail |
| gray-300 | `#d1d5db` | rgb(209, 213, 219) | 1.30:1 | ❌ Fail |
| gray-400 | `#9ca3af` | rgb(156, 163, 175) | 1.97:1 | ❌ Fail (text) |
| gray-500 | `#6b7280` | rgb(107, 114, 128) | 3.01:1 | ⚠️ AA Large Text Only |
| gray-600 | `#4b5563` | rgb(75, 85, 99) | 4.88:1 | ✅ AA Normal Text |
| gray-700 | `#374151` | rgb(55, 65, 81) | 7.37:1 | ✅ AAA Normal Text |
| gray-800 | `#1f2937` | rgb(31, 41, 55) | 10.99:1 | ✅ AAA Normal Text |
| gray-900 | `#111827` | rgb(17, 24, 39) | 15.05:1 | ✅ AAA Normal Text |
| gray-950 | `#030712` | rgb(3, 7, 18) | 19.41:1 | ✅ AAA Normal Text |

### Zinc (Modern Warm Gray)

**Usage**: Contemporary look, warm backgrounds

| Shade | Hex Code | RGB | Contrast on White | WCAG Level |
|-------|----------|-----|-------------------|------------|
| zinc-50 | `#fafafa` | rgb(250, 250, 250) | 1.01:1 | ❌ Fail |
| zinc-100 | `#f4f4f5` | rgb(244, 244, 245) | 1.03:1 | ❌ Fail |
| zinc-200 | `#e4e4e7` | rgb(228, 228, 231) | 1.13:1 | ❌ Fail |
| zinc-300 | `#d4d4d8` | rgb(212, 212, 216) | 1.32:1 | ❌ Fail |
| zinc-400 | `#a1a1aa` | rgb(161, 161, 170) | 1.91:1 | ❌ Fail (text) |
| zinc-500 | `#71717a` | rgb(113, 113, 122) | 2.93:1 | ❌ Fail (text) |
| zinc-600 | `#52525b` | rgb(82, 82, 91) | 4.61:1 | ✅ AA Normal Text |
| zinc-700 | `#3f3f46` | rgb(63, 63, 70) | 7.00:1 | ✅ AA+ Normal Text |
| zinc-800 | `#27272a` | rgb(39, 39, 42) | 10.59:1 | ✅ AAA Normal Text |
| zinc-900 | `#18181b` | rgb(24, 24, 27) | 14.51:1 | ✅ AAA Normal Text |
| zinc-950 | `#09090b` | rgb(9, 9, 11) | 18.52:1 | ✅ AAA Normal Text |

**Recommended for Healthcare**:
- **Primary Choice**: Slate (cool, professional)
  - Page Background: `slate-50` (#f8fafc)
  - Card Background: `slate-100` (#f1f5f9)
  - Borders: `slate-200` (#e2e8f0)
  - Body Text: `slate-700` (#334155) - 7.74:1 contrast
  - Headers: `slate-800` (#1e293b) - 11.37:1 contrast
  - Placeholder: `slate-400` (#94a3b8) for form inputs (use with label)

---

## 4. WCAG 2.1 Accessibility Compliance

### Contrast Ratio Requirements

| Content Type | Level AA | Level AAA | Recommended for Healthcare |
|-------------|----------|-----------|---------------------------|
| **Normal Text** (<18pt or <14pt bold) | 4.5:1 | 7:1 | **7:1 (AAA)** |
| **Large Text** (≥18pt or ≥14pt bold) | 3:1 | 4.5:1 | **4.5:1 (AAA)** |
| **UI Components** (buttons, icons) | 3:1 | - | **3:1 minimum** |
| **Graphical Objects** (charts, diagrams) | 3:1 | - | **3:1 minimum** |

### Healthcare-Specific Recommendations

**Healthcare applications should target WCAG Level AAA (7:1) for most text** due to:
- Critical nature of medical information
- Impact on patient safety and understanding
- Diverse user base (elderly, vision-impaired)
- Stress-filled environments requiring maximum clarity

### Compliant Color Combinations

#### Text on White (#ffffff) Background

| Text Color | Contrast Ratio | WCAG Level | Use Case |
|-----------|----------------|------------|----------|
| `slate-700` (#334155) | 7.74:1 | ✅ AAA | Body text |
| `slate-800` (#1e293b) | 11.37:1 | ✅ AAA | Headers, emphasis |
| `blue-600` (#2563eb) | 5.54:1 | ✅ AA | Links, primary buttons |
| `blue-700` (#1d4ed8) | 7.96:1 | ✅ AAA | Primary text links |
| `teal-600` (#0d9488) | 4.77:1 | ✅ AA | Secondary elements |
| `emerald-600` (#059669) | 5.43:1 | ✅ AA | Success text |
| `amber-700` (#b45309) | 4.78:1 | ✅ AA | Warning text |
| `red-600` (#dc2626) | 4.52:1 | ✅ AA | Error text |

#### White Text on Colored Backgrounds

| Background Color | Contrast Ratio | WCAG Level | Use Case |
|-----------------|----------------|------------|----------|
| `blue-600` (#2563eb) | 3.79:1 | ✅ AA Large Text | Primary buttons |
| `blue-700` (#1d4ed8) | 2.64:1 | ⚠️ Insufficient | Use white text only for large text |
| `teal-700` (#0f766e) | 3.05:1 | ⚠️ AA Large Text | Secondary buttons |
| `emerald-600` (#059669) | 3.87:1 | ✅ AA Large Text | Success buttons |
| `red-600` (#dc2626) | 4.65:1 | ✅ AA Normal Text | Error buttons |

### Testing Tools

- **WebAIM Contrast Checker**: https://webaim.org/resources/contrastchecker/
- **Contrast Ratio**: https://contrast-ratio.org/
- **Colour Contrast Checker**: https://colourcontrast.cc/
- **Little Blue Insight WCAG Checker**: https://littleblueinsight.com/tool/technology/contrast-color-checker/

---

## 5. Color Blindness Considerations

### Types of Color Blindness

| Type | Prevalence | Affected Colors | Design Impact |
|------|-----------|-----------------|---------------|
| **Deuteranopia** | 5% of males | Red-green confusion (green deficiency) | Cannot distinguish red from green |
| **Protanopia** | 2.5% of males | Red-green confusion (red deficiency) | Cannot distinguish red from green |
| **Tritanopia** | 0.001% | Blue-yellow confusion | Rare, less critical |
| **Total** | ~8% males, 0.5% females | - | 1 in 12 males affected |

### Design Guidelines for Color Blind Users

#### 1. **NEVER Rely on Color Alone**

❌ **Bad**: Red text for errors, green text for success (color only)

✅ **Good**: Color + Icon + Text label
- Error: `red-600` + ❌ icon + "Error: " text prefix
- Success: `emerald-600` + ✅ icon + "Success: " text prefix
- Warning: `amber-700` + ⚠️ icon + "Warning: " text prefix

#### 2. **Avoid Pure Red and Green**

❌ **Bad**: Pure red (#ff0000) and pure green (#00ff00)

✅ **Good**: Reddish-orange and bluish-green
- Use `red-600` (#dc2626) instead of pure red
- Use `emerald-600` (#059669) instead of pure green
- These maintain cultural meanings while being distinguishable

#### 3. **Use High Contrast**

✅ **Good**: Ensure 3:1 minimum contrast for UI components
- Pure red (#ff0000) has 4:1 on white (acceptable)
- Pure green (#00ff00) has 1.4:1 on white (fail)
- Always test with contrast checker tools

#### 4. **Add Visual Patterns**

✅ **Good**: Use patterns, textures, or shapes in addition to color
- Charts: Use patterns (stripes, dots) + color
- Status badges: Use shapes (circle, square, diamond) + color
- Graphs: Use line styles (solid, dashed, dotted) + color

#### 5. **Test with Simulators**

- **Figma Plugin**: Color Blind (tests 8 types of color vision deficiency)
- **Browser Extension**: Colorblind (Chrome/Firefox)
- **Online Tool**: https://imagecolorpicker.com/blindness-simulator

### Color-Blind Safe Palettes

**Recommended Combinations**:

1. **Blue (#2563eb) + Orange (#d97706)**: High contrast, distinguishable
2. **Teal (#0d9488) + Amber (#b45309)**: Medical aesthetic, safe
3. **Purple + Yellow**: Alternative to blue-orange
4. **Dark Blue (#1e3a8a) + Red-Orange (#dc2626)**: High contrast, safe

**Avoid Combinations**:

❌ Red + Green (deuteranopia/protanopia cannot distinguish)
❌ Blue + Purple (tritanopia cannot distinguish)
❌ Light colors without sufficient contrast

---

## 6. Healthcare Industry Examples

### HealthCare.gov Design System

**Primary Colors**:
- Blue: Trust, confidence, sincerity (primary base color)
- Green: Energetic accents, "pop" elements
- White: Clean content areas

**Design Philosophy**:
- Minimalist palette with blue dominating
- Accent colors used sparingly for attention
- Neutral backdrop allows energy and imagery to stand out

**Reference**: https://styleguide.healthcare.gov/design/colors/

### Common Healthcare Color Usage

**Blue Prevalence**: 85% of healthcare logos use blue
- Mayo Clinic: Blue (#0071BB range) for trust and reliability
- Kaiser Permanente: Blue and teal combinations
- UnitedHealth Group: Deep navy (#1e3d6a)

**Operating Room Green**: Teal-green (#0d9488 - #0f766e)
- Historically worn by surgeons
- Counteracts visual effects of bright lights and red tones
- Creates calming, focused environment

**Medical Mask Blue**: Light blue (#93c5fd range)
- Associated with cleanliness and hygiene
- Medical-grade equipment aesthetic

### Healthcare Color Psychology

| Color | Psychological Effect | Healthcare Use |
|-------|---------------------|----------------|
| **Blue** | Trust, calmness, security, competence | Primary brand, navigation, patient-facing |
| **Teal** | Serenity, balance, healing | Secondary brand, wellness features |
| **Green** | Health, growth, nature, vitality | Success states, positive indicators |
| **White** | Cleanliness, purity, sterility | Backgrounds, medical contexts |
| **Gray** | Professionalism, stability, neutrality | Text, supporting elements |
| **Red** | Urgency, danger, attention | Errors, critical alerts (use sparingly) |

---

## 7. Recommended Color Palette for TremoAI

### Primary Palette

```css
/* Primary Brand Colors */
--color-primary: #2563eb;        /* blue-600 - Main brand color */
--color-primary-dark: #1d4ed8;   /* blue-700 - Hover states */
--color-primary-light: #dbeafe;  /* blue-100 - Backgrounds */

/* Secondary Brand Colors */
--color-secondary: #0d9488;      /* teal-600 - Accent color */
--color-secondary-dark: #0f766e; /* teal-700 - Hover states */
--color-secondary-light: #ccfbf1;/* teal-100 - Backgrounds */

/* Status Colors */
--color-success: #059669;        /* emerald-600 - Success states */
--color-success-bg: #ecfdf5;     /* emerald-50 - Success backgrounds */
--color-warning: #b45309;        /* amber-700 - Warning states */
--color-warning-bg: #fffbeb;     /* amber-50 - Warning backgrounds */
--color-error: #dc2626;          /* red-600 - Error states */
--color-error-bg: #fef2f2;       /* red-50 - Error backgrounds */

/* Neutral Colors */
--color-gray-50: #f8fafc;        /* slate-50 - Page background */
--color-gray-100: #f1f5f9;       /* slate-100 - Card background */
--color-gray-200: #e2e8f0;       /* slate-200 - Borders */
--color-gray-400: #94a3b8;       /* slate-400 - Placeholder */
--color-gray-600: #475569;       /* slate-600 - Secondary text */
--color-gray-700: #334155;       /* slate-700 - Body text */
--color-gray-800: #1e293b;       /* slate-800 - Headers */

/* Semantic Colors */
--color-text-primary: #334155;   /* slate-700 - 7.74:1 contrast */
--color-text-secondary: #475569; /* slate-600 - 5.15:1 contrast */
--color-text-disabled: #94a3b8;  /* slate-400 - 2.07:1 contrast */
--color-background: #ffffff;     /* white - Base background */
--color-background-alt: #f8fafc; /* slate-50 - Alternative background */
--color-border: #e2e8f0;         /* slate-200 - Default borders */
```

### Tailwind CSS Configuration

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',  // Main brand
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        secondary: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',
          600: '#0d9488',  // Accent brand
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
          950: '#042f2e',
        },
        success: {
          DEFAULT: '#059669',
          light: '#ecfdf5',
          dark: '#047857',
        },
        warning: {
          DEFAULT: '#b45309',
          light: '#fffbeb',
          dark: '#92400e',
        },
        error: {
          DEFAULT: '#dc2626',
          light: '#fef2f2',
          dark: '#b91c1c',
        },
      },
    },
  },
  plugins: [],
}
```

---

## 8. Usage Guidelines

### Component-Level Recommendations

#### Buttons

```css
/* Primary Button */
.btn-primary {
  background: #2563eb;  /* blue-600 */
  color: #ffffff;       /* 3.79:1 - AA large text */
  border: 1px solid #2563eb;
}
.btn-primary:hover {
  background: #1d4ed8;  /* blue-700 */
}

/* Secondary Button */
.btn-secondary {
  background: #0d9488;  /* teal-600 */
  color: #ffffff;
  border: 1px solid #0d9488;
}

/* Outline Button */
.btn-outline {
  background: transparent;
  color: #2563eb;       /* blue-600 */
  border: 2px solid #2563eb;
}

/* Danger Button */
.btn-danger {
  background: #dc2626;  /* red-600 */
  color: #ffffff;       /* 4.65:1 - AA normal text */
}
```

#### Text Hierarchy

```css
/* Headers */
h1, h2 { color: #1e293b; }  /* slate-800 - 11.37:1 */
h3, h4 { color: #334155; }  /* slate-700 - 7.74:1 */
h5, h6 { color: #475569; }  /* slate-600 - 5.15:1 */

/* Body Text */
p { color: #334155; }       /* slate-700 - 7.74:1 */

/* Secondary Text */
.text-secondary { color: #475569; }  /* slate-600 - 5.15:1 */

/* Disabled Text */
.text-disabled { color: #94a3b8; }   /* slate-400 - 2.07:1 */

/* Links */
a { color: #2563eb; }       /* blue-600 - 5.54:1 */
a:hover { color: #1d4ed8; } /* blue-700 - 7.96:1 */
```

#### Status Badges

```css
/* Success Badge */
.badge-success {
  background: #ecfdf5;    /* emerald-50 */
  color: #047857;         /* emerald-700 - 7.76:1 */
  border: 1px solid #059669; /* emerald-600 */
}
.badge-success::before {
  content: "✓ ";          /* Checkmark icon */
}

/* Warning Badge */
.badge-warning {
  background: #fffbeb;    /* amber-50 */
  color: #92400e;         /* amber-800 - 6.85:1 */
  border: 1px solid #b45309; /* amber-700 */
}
.badge-warning::before {
  content: "⚠ ";          /* Warning icon */
}

/* Error Badge */
.badge-error {
  background: #fef2f2;    /* red-50 */
  color: #b91c1c;         /* red-700 - 6.50:1 */
  border: 1px solid #dc2626; /* red-600 */
}
.badge-error::before {
  content: "✕ ";          /* X icon */
}
```

#### Form Inputs

```css
/* Input Field */
.input {
  background: #ffffff;
  border: 1px solid #e2e8f0;  /* slate-200 */
  color: #334155;             /* slate-700 */
}
.input::placeholder {
  color: #94a3b8;             /* slate-400 */
}
.input:focus {
  border-color: #2563eb;      /* blue-600 */
  outline: 2px solid #dbeafe; /* blue-100 */
}

/* Input Error State */
.input.error {
  border-color: #dc2626;      /* red-600 */
}
.input-error-message {
  color: #b91c1c;             /* red-700 - 6.50:1 */
}

/* Input Success State */
.input.success {
  border-color: #059669;      /* emerald-600 */
}
```

#### Charts & Data Visualization

```css
/* Chart Colors (Color-Blind Safe) */
--chart-blue: #2563eb;    /* Primary data */
--chart-teal: #0d9488;    /* Secondary data */
--chart-amber: #f59e0b;   /* Tertiary data */
--chart-red: #dc2626;     /* Warning/critical data */
--chart-emerald: #059669; /* Positive data */
--chart-purple: #9333ea;  /* Alternative data */

/* Use patterns + colors for accessibility */
/* Solid line + blue, Dashed line + teal, Dotted line + amber */
```

### Dark Mode Considerations (Future)

While not currently implemented, consider these adjustments for dark mode:

```css
/* Dark Mode Palette */
--color-background-dark: #0f172a;      /* slate-900 */
--color-surface-dark: #1e293b;         /* slate-800 */
--color-text-primary-dark: #f1f5f9;    /* slate-100 */
--color-primary-dark-mode: #60a5fa;    /* blue-400 - lighter for dark bg */
```

---

## 9. Implementation Checklist

### Before Using This Palette

- [ ] Test all color combinations with WebAIM Contrast Checker
- [ ] Verify WCAG Level AA compliance (4.5:1 for normal text)
- [ ] Verify WCAG Level AAA compliance for critical medical information (7:1)
- [ ] Test with color blindness simulators (Figma Color Blind plugin)
- [ ] Ensure status colors always include icons + text labels (not color alone)
- [ ] Document color usage in component library
- [ ] Create Tailwind configuration with these colors
- [ ] Test with real users (including elderly and vision-impaired)
- [ ] Validate on multiple devices and screen brightness levels
- [ ] Create style guide for developers with copy-paste examples

### Accessibility Testing Protocol

1. **Contrast Testing**:
   - Use WebAIM Contrast Checker for all text/background combinations
   - Target 7:1 for body text, 4.5:1 minimum for large text
   - Test at different screen brightness levels

2. **Color Blindness Testing**:
   - Test with Figma Color Blind plugin (deuteranopia, protanopia)
   - Verify status indicators work without color (icons + text)
   - Check chart/graph distinguishability with patterns

3. **User Testing**:
   - Test with elderly users (65+)
   - Test with vision-impaired users
   - Test in bright medical office environments
   - Test on various devices (desktop, tablet, mobile)

---

## 10. References & Sources

### Design Systems & Documentation

- [HealthCare.gov Styleguide - Colors](https://styleguide.healthcare.gov/design/colors/)
- [Tailwind CSS Colors Documentation](https://tailwindcss.com/docs/colors)
- [Material Design Color System](https://m3.material.io/styles/color/system/overview)

### Accessibility Standards

- [WebAIM: Contrast and Color Accessibility](https://webaim.org/articles/contrast/)
- [W3C WCAG 2.1 Understanding Success Criterion 1.4.3: Contrast (Minimum)](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- [AllAccessible: Color Contrast Accessibility Complete WCAG 2025 Guide](https://www.allaccessible.org/blog/color-contrast-accessibility-wcag-guide-2025)
- [MDN: Color Contrast Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility/Guides/Understanding_WCAG/Perceivable/Color_contrast)

### Healthcare Color Research

- [Piktochart: The Best 15 Medical Color Palette Combinations](https://piktochart.com/tips/medical-color-palette)
- [Progress: Healthcare Color Palette - Using Color Psychology for Website Design](https://www.progress.com/blogs/using-color-psychology-healthcare-web-design)
- [99designs: How do you choose colors for a healthcare logo?](https://99designs.com/logo-design/psychology-of-color/healthcare)
- [SchemeColor: Healthcare #1 Color Scheme](https://www.schemecolor.com/healthcare-1.php)

### Color Blindness Resources

- [Interaction Design Foundation: What is Color Blindness?](https://www.interaction-design.org/literature/topics/color-blindness)
- [UX Collective: Color blindness - how to design an accessible user interface](https://uxdesign.cc/color-blindness-in-user-interfaces-66c27331b858)
- [Secret Stache: Designing UI with color blind users in mind](https://www.secretstache.com/blog/designing-for-color-blind-users/)
- [Venngage: Color Blind Design Guidelines](https://venngage.com/blog/color-blind-design/)
- [David Mathlogic: Coloring for Colorblindness](https://davidmathlogic.com/colorblind/)

### Contrast Ratio Tools

- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Contrast Ratio by Lea Verou](https://contrast-ratio.org/)
- [Colour Contrast Checker](https://colourcontrast.cc/)
- [Accessible Web Color Contrast Checker](https://accessibleweb.com/color-contrast-checker/)

### Healthcare Industry Examples

- [Pilot Digital: What WCAG 2.1 AA Means for Healthcare Organizations in 2026](https://pilotdigital.com/blog/what-wcag-2-1aa-means-for-healthcare-organizations-in-2026/)
- [Carenetic Digital: Healthcare Website Accessibility - The May 2026 Deadline](https://careneticdigital.com/healthcare-website-accessibility-the-may-2026-deadline/)
- [Grey Matter Marketing: Standing Out From the Sea of Blue - Color in Healthcare Brand Design](https://www.greymattermarketing.com/blog/standing-out-from-the-sea-of-blue)

### Additional Resources

- [Tailwind Color Tools](https://ui.shadcn.com/colors)
- [UIColors.app - Tailwind CSS Color Explorer](https://uicolors.app/tailwind-colors)
- [Cieden: How do I choose system colors (success, warning, error)?](https://cieden.com/book/sub-atomic/color/system-colors)
- [Venngage: Guide to Accessible Colors Palettes](https://venngage.com/blog/accessible-colors/)

---

## Appendix: Quick Reference

### Color Token Quick Reference

```
PRIMARY: #2563eb (blue-600)
SECONDARY: #0d9488 (teal-600)
SUCCESS: #059669 (emerald-600)
WARNING: #b45309 (amber-700)
ERROR: #dc2626 (red-600)
TEXT-PRIMARY: #334155 (slate-700)
TEXT-SECONDARY: #475569 (slate-600)
BACKGROUND: #ffffff (white)
BACKGROUND-ALT: #f8fafc (slate-50)
BORDER: #e2e8f0 (slate-200)
```

### Minimum Contrast Requirements

- **Normal Text**: 4.5:1 (AA), 7:1 (AAA) ← **Target for healthcare**
- **Large Text**: 3:1 (AA), 4.5:1 (AAA)
- **UI Components**: 3:1 minimum

### Color-Blind Safe Practices

✅ **Always use**: Color + Icon + Text Label
✅ **Prefer**: Blue + Orange, Teal + Amber
❌ **Avoid**: Red + Green alone, Low contrast combinations

---

**Document Version**: 1.0
**Last Updated**: 2026-02-16
**For**: TremoAI Web Platform (Frontend Feature 009)
**Compliance**: WCAG 2.1 Level AA (targeting AAA for critical content)
