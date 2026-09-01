---
name: Border-X Intelligence System
colors:
  surface: '#0f141b'
  surface-dim: '#0f141b'
  surface-bright: '#353941'
  surface-container-lowest: '#090e15'
  surface-container-low: '#171c23'
  surface-container: '#1b2027'
  surface-container-high: '#252a32'
  surface-container-highest: '#30353d'
  on-surface: '#dee2ed'
  on-surface-variant: '#c6c5d5'
  inverse-surface: '#dee2ed'
  inverse-on-surface: '#2c3138'
  outline: '#8f8f9f'
  outline-variant: '#454653'
  surface-tint: '#bcc3ff'
  primary: '#bcc3ff'
  on-primary: '#041c94'
  primary-container: '#7c8cff'
  on-primary-container: '#001892'
  inverse-primary: '#4353c3'
  secondary: '#a2c9ff'
  on-secondary: '#00315b'
  secondary-container: '#3994ef'
  on-secondary-container: '#002b50'
  tertiary: '#4ae08d'
  on-tertiary: '#00391d'
  tertiary-container: '#00ac63'
  on-tertiary-container: '#00371c'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dfe0ff'
  primary-fixed-dim: '#bcc3ff'
  on-primary-fixed: '#000c60'
  on-primary-fixed-variant: '#2839aa'
  secondary-fixed: '#d3e4ff'
  secondary-fixed-dim: '#a2c9ff'
  on-secondary-fixed: '#001c38'
  on-secondary-fixed-variant: '#004881'
  tertiary-fixed: '#6bfda7'
  tertiary-fixed-dim: '#4ae08d'
  on-tertiary-fixed: '#00210f'
  on-tertiary-fixed-variant: '#00522c'
  background: '#0f141b'
  on-background: '#dee2ed'
  surface-variant: '#30353d'
typography:
  display-lg:
    fontFamily: hankenGrotesk
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.02em
  display-md:
    fontFamily: hankenGrotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-md:
    fontFamily: geist
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  technical-sm:
    fontFamily: jetbrainsMono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  technical-xs:
    fontFamily: jetbrainsMono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
  label-caps:
    fontFamily: hankenGrotesk
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 12px
    letterSpacing: 0.06em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  panel-gap: 2px
  container-margin: 16px
---

## Brand & Style

The design system is engineered for the high-stakes environment of AI video intelligence and border surveillance. It adopts a **Premium Command Center** aesthetic, prioritizing technical precision, rapid information processing, and visual stability. 

The brand personality is authoritative, vigilant, and analytical. By leveraging Geist’s technical rigor and Hanken Grotesk’s sharp geometric clarity, the interface minimizes cognitive load while maximizing the density of actionable data. The style is a hybrid of **Minimalism** and **Technical Glassmorphism**, using subtle translucency and strict grid alignment to create a sense of depth without distracting from real-time video feeds and telemetry.

Every element is designed to feel like a mission-critical tool: no unnecessary ornamentation, high information density, and a focus on visual hierarchy that directs the eye to anomalies and critical alerts.

## Colors

The color palette is optimized for long-duration monitoring in low-light environments. The core background is a deep charcoal (`#080B10`), providing a high-contrast foundation for live video streams and luminous data overlays.

- **Surface Tiers:** Use a layered approach to hierarchy. `surface_main` is for the base application container, while `surface_elevated` highlights active interactive panels or modal overlays.
- **Accents:** The primary seed color (`#7C8CFF`) is used for primary actions and "system-active" states. The secondary blue (`#4DA3FF`) differentiates secondary intelligence data.
- **Semantic Feedback:** Critical alerts utilize a high-vibrancy Red (`#FF5C67`) to ensure immediate detection among dense data. Success and Warning states use high-visibility green and amber to denote system health and non-immediate threats.
- **Typography:** Contrast ratios are strictly maintained to ensure legibility of small metadata labels against dark backgrounds.

## Typography

This design system employs a three-tier typographic strategy:

1.  **Hanken Grotesk (Headlines):** Used for titles and navigation headers. Its sharp geometry lends a professional, modern authority to the interface.
2.  **Geist (Body):** Utilized for general interface text and descriptions. Its technical precision and high legibility at small scales make it ideal for dense data environments.
3.  **JetBrains Mono (Technical Data):** Reserved for mission-critical variables including timestamps, license plate characters, GPS coordinates, confidence scores, and system IDs. The monospaced nature ensures that numeric values do not "jump" during real-time updates.

Small metadata should utilize `technical-xs` to maximize screen real estate while maintaining OCR-like clarity.

## Layout & Spacing

The layout follows a **High-Density Fluid Grid** model designed for ultra-wide monitors and multi-screen arrays.

- **Rhythm:** A 4px base unit governs all dimensions. Spacing is intentionally compact to allow for multiple concurrent video streams and sidebar telemetry.
- **Grid:** A 12-column grid is used for dashboard layouts, with a strict 2px "panel-gap" to create a monolithic, integrated appearance where components feel interlocked rather than floating.
- **Margins:** Standard application margins are 16px, ensuring content doesn't bleed into screen bezels, while internal component padding is kept tight (8px to 12px).
- **Responsive Behavior:** On mobile/tablet, panels reflow into a single-column stack, prioritizing the video feed at the top of the viewport with actionable intelligence below.

## Elevation & Depth

In a dark, high-density environment, traditional shadows are replaced by **Tonal Layering** and **Luminous Outlines**.

- **Surface Tiering:** Hierarchy is established by increasing the brightness of the surface hex code as elements "rise" closer to the user.
- **Subtle Borders:** All containers utilize a 1px solid border (`#202A36`). This provides a crisp "CAD-like" definition between dense data clusters.
- **Active Glow:** When a panel or feed is "selected" or "active," it receives a subtle inner-glow or a primary-color border stroke (`#7C8CFF`) rather than a shadow, maintaining the flat, technical aesthetic.
- **Backdrop Blur:** Modals and temporary overlays use a 12px backdrop blur with a 60% opacity fill of `surface_elevated` to maintain context of the underlying live feeds.

## Shapes

The design system uses a **Soft** shape language to balance technical rigidity with modern UI ergonomics.

- **Standard Radius:** A 0.25rem (4px) radius is applied to small interactive elements like buttons and input fields.
- **Container Radius:** Larger panels and cards use a 0.5rem (8px) radius (`rounded-lg`) to clearly define the boundaries of major functional areas.
- **Technical Elements:** Elements representing "raw" data (like bounding boxes in video feeds) should remain at 0px radius (Sharp) to emphasize their computer-vision origin.

## Components

### Buttons
- **Primary:** Solid `#7C8CFF` with `#080B10` text. High-contrast for emergency actions.
- **Ghost/Outline:** 1px border of `#202A36` with `#F3F6FA` text. Used for secondary navigation.
- **Destructive:** Solid `#FF5C67` for "Terminate" or "Alert" functions.

### Inputs & Search
- Dark fills (`#0D1219`) with 1px borders. Focus states transition the border to `#7C8CFF`.
- Typography within inputs uses `geist` for text and `jetbrainsMono` for numeric data entry.

### Chips & Status Indicators
- **AI Confidence Tags:** Small, pill-shaped badges using `technical-xs` font. Backgrounds are low-opacity versions of semantic colors (e.g., Green at 15% opacity).
- **Object Markers:** Bounding boxes in video feeds use 1px strokes of accent colors with a corner-bracket style rather than a full box to avoid obscuring the subject.

### Video Feed Cards
- Zero-gap headers. Metadata overlays are positioned in the top-right corner with a `backdrop-blur` background.
- Real-time "Rec" indicators use a pulsing animation on a `#FF5C67` dot.

### Data Tables
- High-density rows (32px height).
- Alternating row zebra-striping using `surface_main` and `surface_secondary`.
- Header text uses `label-caps` for clear categorization.