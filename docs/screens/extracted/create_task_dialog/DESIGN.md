# Design System Specification: Kinetic Precision

## 1. Overview & Creative North Star
**The Creative North Star: "The Neon Observatory"**
This design system moves away from the static, "flat" productivity tools of the past decade. It embraces a "Neon Observatory" aesthetic—combining the vast, infinite depth of a deep-space obsidian environment with the high-energy precision of technical instrumentation. 

We break the "standard template" look by utilizing **intentional asymmetry** and **chromatic depth**. Instead of rigid, boxed-in columns, we use overlapping glass layers and "light-leak" accents. The goal is to make the user feel like they are commanding a high-end flight deck, where data isn't just displayed—it's illuminated.

---

## 2. Colors & Surface Philosophy
The palette is rooted in a high-contrast relationship between the void (`surface`) and the spark (`primary`).

### The Palette
- **Primary (Vibrant Orange):** `#ff9153` (Primary) to `#ff7a23` (Container). This is our "Action" color. It represents momentum.
- **Secondary (Cyan):** `#53ddfc`. Used for secondary data streams, technical metadata, and "active" states that require a cooler temperament.
- **Surface (Deep Navy/Slate):** `#060e1f`. The foundation of the entire experience.

### The "No-Line" Rule
**Standard 1px borders are strictly prohibited for sectioning.** 
To define boundaries, use **Tonal Transitions**. A Kanban column should not be outlined; it should be defined by sitting on a `surface-container-low` background against the `surface` main floor. If a visual break is needed, use a `24px` or `32px` gutter (Spacing Scale 6 or 8) to let the background "breathe" between content blocks.

### The "Glass & Gradient" Rule
Floating elements (Modals, Hovering Cards) must utilize **Glassmorphism**:
- **Fill:** `surface-container-high` at 60% opacity.
- **Backdrop Blur:** 12px to 20px.
- **Signature Glow:** Instead of a border, use a `primary` inner-shadow or a 1px `outline-variant` at 15% opacity to catch the light.

---

## 3. Typography: The Editorial Scale
We use **Inter** exclusively. It is a workhorse that provides a "technical-chic" feel when spaced correctly.

| Level | Token | Size | Tracking | Weight | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Display** | `display-lg` | 3.5rem | -0.02em | 700 | High-impact dashboard metrics |
| **Headline** | `headline-sm` | 1.5rem | -0.01em | 600 | Board Titles / Column Headers |
| **Title** | `title-md` | 1.125rem | 0 | 500 | Task Card Titles |
| **Body** | `body-md` | 0.875rem | 0 | 400 | Descriptions & Comments |
| **Label** | `label-sm` | 0.6875rem | +0.05em | 600 | Uppercase Tags / Metadata |

**Editorial Note:** Use `display-md` for empty states or "Zero Inbox" screens to create a bold, confident focal point that breaks the repetitive grid of the Kanban board.

---

## 4. Elevation & Depth: The Layering Principle
Depth is achieved through **Tonal Stacking**, not shadows alone.

1.  **Base Layer:** `surface` (#060e1f) – The "Floor."
2.  **Middle Layer:** `surface-container-low` – Kanban Columns / Navigation Sidebar.
3.  **Top Layer:** `surface-container-highest` – Active Task Cards.
4.  **Floating Layer:** Glassmorphic Modals with `surface-tint` (#ff9153) at 5% opacity to give a "warm lens" effect.

### Ambient Shadows
Forget `#000000` shadows. Use tinted shadows for a premium feel:
- **Value:** `0px 12px 32px`
- **Color:** `on-surface` (#dde5fe) at 4% opacity. 
This creates a "natural lift" that feels like the card is floating in a pressurized environment.

---

## 5. Components

### Task Cards (The Hero Component)
- **Background:** `surface-container-highest` at 80% opacity with 16px blur.
- **Border:** A "Ghost Border" using `primary` (#ff9153) at 10% opacity.
- **Corner Radius:** `xl` (1.5rem / 24px) for a modern, oversized feel.
- **Interaction:** On hover, the border opacity increases to 40% and a subtle `primary` glow (4px spread) appears.

### Buttons
- **Primary:** Gradient fill from `primary` (#ff9153) to `primary-container` (#ff7a23). No border. White text (`on-primary-fixed`).
- **Tertiary (Ghost):** No background. `secondary` (#53ddfc) text. Use for "Add Task" buttons to keep the UI clean.

### Input Fields
- **Style:** Underline only or "Soft Inset." 
- **Focus State:** Transition the underline to `primary` (#ff9153) with a 2px height. Forbid the "box focus" look.

### Chips & Tags
- **Selection Chips:** Use `secondary-container` with `on-secondary` text. 
- **Rule:** Never use dividers in lists. Use **Spacing Scale 4 (1rem)** to separate items.

---

## 6. Do’s and Don’ts

### Do:
- **Embrace Negative Space:** Use `Spacing 10` (2.5rem) between major columns. Let the dark background provide the structure.
- **Use "Signature Textures":** Apply a subtle `primary` to `transparent` linear gradient (at 5% opacity) in the background of a "High Priority" card.
- **Animate Transitions:** Use "Spring" physics for card dragging. The UI should feel kinetic and reactive.

### Don’t:
- **Don't use 100% White:** Use `on-surface` (#dde5fe) for text to prevent eye strain against the dark background.
- **Don't use Dividers:** If you feel the need to draw a line, increase the `Spacing` or change the `surface-container` tier instead.
- **Don't use Sharp Corners:** Everything must adhere to the `lg` (16px) or `xl` (24px) radius to maintain the sophisticated, high-end tech vibe.