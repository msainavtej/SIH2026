---
name: BorderAI Security Design System
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#ffb95f'
  on-tertiary: '#472a00'
  tertiary-container: '#ca8100'
  on-tertiary-container: '#3e2400'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
  mono-data:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  container-margin: 24px
  gutter: 12px
---

## Brand & Style

The design system is engineered for mission-critical environments where rapid information processing and high-stakes decision-making are constant. The brand personality is **authoritative, intelligent, and vigilant**. It eschews the playful aesthetics of consumer software in favor of a **Corporate Modern** style that emphasizes utility, precision, and trust.

The visual language draws inspiration from modern command-and-control centers, utilizing a high-density layout that maximizes screen real estate without compromising legibility. The interface focuses on "calm technology"—keeping the background subdued so that critical alerts and live data streams command the operator's immediate attention. Surfaces are structured with surgical precision, using thin borders and tonal shifts rather than heavy shadows to denote hierarchy.

## Colors

The color palette is built on a foundation of deep, stable neutrals to minimize eye strain during extended shifts. The **Neutral Base** (`#020617`) provides the canvas, while the **Seed Color** (`#0F172A`) defines the primary panel structure.

The accent system is strictly functional:
- **Blue (#3B82F6):** Used for primary actions, processing states, and informational callouts.
- **Green (#10B981):** Indicates operational health, successful scans, and secure status.
- **Amber (#F59E0B):** Reserved for warnings and medium-priority anomalies.
- **Red (#EF4444):** Exclusively for high-priority alerts, breaches, and critical system failures.

Contrast is maintained through a series of "Surface" tokens that allow for subtle depth separation between navigation, sidebars, and main content areas.

## Typography

This design system utilizes **Inter** for all primary UI elements to ensure maximum legibility across high-density data views. The type scale is optimized for information density, favoring smaller, well-spaced body text over large display type.

**Key Typographic Rules:**
- **Monospacing:** For timestamps, coordinates, and IP addresses, use a secondary monospaced font (e.g., JetBrains Mono) to ensure character alignment and rapid scanning.
- **Labeling:** Use the `label-md` style for section headers and table columns to provide clear structure without occupying excessive vertical space.
- **Line Heights:** Tighter line heights are used for labels and data points to allow more content to fit "above the fold" in complex dashboard layouts.

## Layout & Spacing

The layout philosophy follows a **Fluid Grid** model with strict 4px increments. The primary goal is to provide a "single pane of glass" view for security operators.

- **Grid Model:** A 12-column system is used for dashboard layouts, while side-panels often occupy fixed widths (e.g., 280px or 320px) to maximize the central workspace.
- **Density:** Spacing is "Tight." Use `8px` (sm) for internal element spacing within cards and `16px` (md) for the primary gutter between major panels.
- **Responsiveness:** On smaller screens, the system prioritizes "stacking" secondary metrics below primary video feeds or maps, though the design is fundamentally optimized for 1440p+ desktop environments.

## Elevation & Depth

In this design system, depth is conveyed through **Tonal Layers** and **Low-Contrast Outlines** rather than traditional shadows. This maintains the professional, "mission-critical" feel and prevents the UI from appearing overly heavy.

- **Level 0 (Background):** The darkest surface (`#020617`), used for the canvas and application frame.
- **Level 1 (Panels):** Sidebars and header bars (`#0F172A`) sit slightly above the background.
- **Level 2 (Cards/Containers):** Main content containers (`#1E293B`) use a subtle 1px border (`#334155`) to define their boundaries.
- **Overlays:** Modals and context menus utilize a 40% backdrop blur (glassmorphism) with a more pronounced border to ensure they pop against the high-density background.

## Shapes

The shape language is **Soft (0.25rem)**. This subtle rounding provides a modern touch that prevents the UI from feeling aggressive or dated, while maintaining the structural rigidity required for a professional enterprise tool.

- **Standard Elements:** Buttons, inputs, and small cards use `0.25rem`.
- **Large Containers:** Dashboard panels or video player containers use `0.5rem` (rounded-lg) to frame the content.
- **Badges:** Status indicators use `rounded-full` (pill) to clearly distinguish them from interactive buttons or inputs.

## Components

### Metric Cards
Metric cards are the heart of the dashboard. They feature a `label-md` title, a large `headline-md` primary value, and a small sparkline or percentage change indicator. Backgrounds should be `surface_card`.

### Video Players
Security feeds must include a semi-transparent overlay at the top (for camera ID/timestamp) and bottom (for playback controls). Use a `1px` inner border to define the video frame within the dark UI.

### High-Density Tables
Tables use `body-sm` text with `8px` vertical cell padding. Header rows are `label-md` with a subtle bottom border. Row hover states should use a slight lightening of the background (`#334155`).

### Status Badges
Badges are small, non-interactive indicators. They consist of a background with 10% opacity of the accent color and a solid text color (e.g., Red text on 10% Red background for 'Critical').

### Buttons
- **Primary:** Solid Blue (`#3B82F6`) with white text.
- **Secondary:** Transparent background with a `1px` border of `#334155`.
- **Alert:** Solid Red (`#EF4444`) for destructive or emergency actions.

### Input Fields
Inputs use a dark fill (`#0F172A`) with a subtle `1px` border. The focus state uses a Blue (`#3B82F6`) glow or 2px border.