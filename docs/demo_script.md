# PreTwinShop AI - Symposium Demonstration Script

This walkthrough script is designed for live evaluation, technical symposia, or recorded demonstrations.

---

### Phase 1: Application Launch & Dashboard Inspection (0:00 - 1:30)
1. **Launch the Server:**
   ```bash
   python app.py
   ```
2. **Open Browser:** Navigate to `http://localhost:5000`.
3. **Presenter Dialogue:**
   > *"Welcome to PreTwinShop AI. Traditional e-commerce is inherently reactive: users must explicitly search for what they want, often after discovering a need too late. PreTwinShop AI turns this paradigm upside down by introducing an autonomous Digital Shopping Twin that proactively predicts your future shopping needs based on voluntary history and strict financial parameters."*
4. **Highlight Key Elements on the Dashboard (`/`):**
   - Note the personalized welcome for **Alex Johnson**.
   - Show the 4 stat cards updating in real time.
   - Point to the **Budget Overview** doughnut chart illustrating spending allocated vs remaining budget.
   - Point out the top 3 proactive predictions already derived by the system.

---

### Phase 2: Examining the Digital Twin Profile (1:30 - 3:00)
1. **Navigate to "My Shopping Twin" (`/twin`):**
2. **Presenter Dialogue:**
   > *"Here in the Shopping Twin interface, users retain complete transparency and control. You can see Alex's preferred categories (Electronics, Computer Accessories, Home Essentials), brand loyalties (Sony, Logitech, Philips), and budget ceiling ($5,000.00)."*
3. **Live Interaction:**
   - Add a brand affinity pill (e.g. `Anker` or `Apple`) and click **Save Preferences**.
   - Scroll down to the **Voluntarily Provided Purchase History** table. Point out the 10 realistic purchases spanning the last 6 months.
   - Click **+ Add Past Purchase**, enter an item (e.g. *Organic Coffee Beans*, *Everyday Consumables*, *$18.99*), and show that it appears immediately in the table.
   - Point out the **Profile Influence Transparency** card at the bottom, which clearly articulates how each attribute steers Agent A through F.

---

### Phase 3: Proactive Need Anticipation (3:00 - 4:15)
1. **Navigate to "Predictive Shopping" (`/predictions`):**
2. **Presenter Dialogue:**
   > *"Agent B analyzes the interval cadence of purchases. For example, consumables bought over 25 days ago trigger Rule 2 replenishment predictions, while repeat equipment categories trigger Rule 1 recurring cadence."*
3. **Live Interaction:**
   - Click **Generate Fresh Predictions**. Observe the spinner and subsequent instant generation.
   - Point out the confidence score badge (e.g. *70% Confidence*) and estimated timeframe (*Within 1-3 weeks*).
   - Click **Find Products &rarr;** on a prediction card to jump directly to product discovery with the category filter pre-applied.

---

### Phase 4: Product Discovery & Side-by-Side Comparison (4:15 - 5:30)
1. **Navigate to "Product Discovery" (`/discovery`):**
2. **Live Interaction:**
   - Filter by *Computer Accessories*.
   - Click **Details** on the *Logitech MX Master 3S Wireless Mouse* to view the full specifications table (DPI, sensor, connectivity, weight).
   - Click **Compare** on 2-3 products (e.g. *Logitech MX Master 3S*, *Keychron K8 Keyboard*, *Anker USB Hub*).
   - Point out the sticky comparison drawer popping up at the bottom showing: `3 products selected for comparison`.
   - Click **Compare Now &rarr;**.
3. **Navigate to "Product Comparison" (`/comparison`):**
   - Review the side-by-side comparison matrix.
   - Show how Agent D evaluated price, specifications richness, and brand affinities to declare the **Agent D Recommended Winner** banner at the top with clear justifications.

---

### Phase 5: Budget-Aware Recommendations & Explanation Evidence (5:30 - 6:45)
1. **Navigate to "Smart Recommendations" (`/recommendations`):**
2. **Presenter Dialogue:**
   > *"Agent E enforces a hard budget ceiling. Traditional recommendation systems try to upsell users; PreTwinShop AI greedily constructs an optimal basket strictly bounded by the customer's financial ceiling."*
3. **Live Interaction:**
   - Show the **Basket Budget Utilization Progress Bar** showing total cost safely below the ceiling.
   - Read the **Agent F Justification**:
     > *"Logitech MX Master 3S Wireless Mouse is recommended because you've purchased from the 'Computer Accessories' category 3 times, showing a strong repeat pattern. The price is well within your budget ceiling."*
   - Show the interactive rating buttons: click **👍 Helpful** to submit user feedback.

---

### Phase 6: Auditing Real Multi-Agent Telemetry & Reset (6:45 - 8:00)
1. **Navigate to "Agent Activity" (`/agents`):**
2. **Presenter Dialogue:**
   > *"PreTwinShop AI never fabricates logs or claims offline mockups. Every agent execution is a real Python function whose runtime and input/output summaries are audited in SQLite."*
3. **Live Interaction:**
   - Tour the horizontal pipeline diagram: A &rarr; B &rarr; C &rarr; D &rarr; E &rarr; F.
   - Inspect the exact execution times (e.g. *14ms*, *28ms*).
   - Navigate to **Settings (`/settings`)**.
   - Click **Export My Twin Data (JSON)** to download the complete profile.
   - Click **Reset Demo Profile to Defaults** to restore the system to factory demo state.
