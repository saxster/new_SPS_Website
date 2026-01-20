# Janus Design System: Titanium Dialect
> "Zero Overlap. High Contrast. Institutional Authority."

## Core Directives
1.  **Framework**: Tailwind CSS (v4 compatible).
2.  **Dialect**: Titanium (High-Security, Brutalist, Professional).
3.  **Layout**: **Zero overlap** is the Law. All content must respect the `pt-20` (80px) header clearance.

## Typography & Colors
- **Font**: Inter (Google Fonts).
- **Primary Text**: `text-slate-900` (Light Mode), `text-slate-100` (Dark Mode).
- **Secondary Text**: `text-slate-600` / `text-slate-400`.
- **Accent**: `text-amber-600` (Compliance Gold) for signals and key indicators.
- **Backgrounds**:
    - Page: `bg-slate-50` / `bg-slate-950` (Titanium Dark).
    - Surface: `bg-white` / `bg-slate-900`.
- **Borders**: `border-slate-200` / `border-slate-800`.

## Component Rules
### 1. Navigation
- **Type**: Side Drawer (Persistent).
- **Trigger**: Fixed Hamburger (Top-Left).
- **Z-Index**: `z-50` (Must be above everything).
- **Backdrop**: `backdrop-blur-md`.

### 2. Cards (JanusCard)
- **Rounded**: `rounded-xl` (Standard) or `rounded-none` (Brutalist Strict).
- **Shadow**: `shadow-sm` (Subtle) or `shadow-md` (Hover).
- **Border**: 1px solid `slate-200` (Light) / `slate-800` (Dark).

### 3. Signals
- **Status Indicators**: Use `w-2 h-2 rounded-full`.
    - Live/Good: `bg-emerald-500`.
    - Warning: `bg-amber-500`.
    - Critical: `bg-rose-600`.

## Prohibited Patterns
- ❌ **No Blue**: Do not use generic `text-blue-500` or `bg-blue-600`. Use Slate/Amber/Emerald/Rose.
- ❌ **No Overlap**: Content must NEVER slide under the header without padding.
- ❌ **No Gradients**: Avoid gradients unless explicitly identifying a "Premium" feature.
