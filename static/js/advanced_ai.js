/**
 * advanced_ai.js
 * Handles Advanced Features for Future Development:
 * 1. Roadmap overview cards
 * 2. Smart Gift Finder tab
 * 3. Predictive Shopping Calendar tab
 * 4. Conversational Voice Simulator tab
 * 5. 3D Virtual Try-On simulator tab
 */

document.addEventListener("DOMContentLoaded", () => {
  loadRoadmapFeatures();
  findGifts();
});

function switchAdvTab(tabName) {
  // Update buttons
  document.querySelectorAll(".adv-tab-btn").forEach(btn => {
    btn.style.borderColor = "#334155";
    btn.style.background = "transparent";
    btn.style.color = "#94a3b8";
  });
  const activeBtn = document.getElementById(`tabBtn_${tabName}`);
  if (activeBtn) {
    activeBtn.style.borderColor = "#6366f1";
    activeBtn.style.background = "rgba(99, 102, 241, 0.15)";
    activeBtn.style.color = "#fff";
  }

  // Update tabs
  document.querySelectorAll(".adv-tab-content").forEach(el => el.style.display = "none");
  const target = document.getElementById(`tabContent_${tabName}`);
  if (target) {
    target.style.display = "block";
  }
}

async function loadRoadmapFeatures() {
  try {
    const res = await fetch("/api/advanced/features");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    const container = document.getElementById("roadmapCardsGrid");
    if (!container) return;

    container.innerHTML = (data.features || []).map(f => {
      let badgeColor = "#10b981";
      if (f.status === "In Development") badgeColor = "#f59e0b";
      else if (f.status === "Planned") badgeColor = "#94a3b8";
      else if (f.status === "Beta Simulator") badgeColor = "#818cf8";

      return `
        <div class="card" style="background:#111827; border:1px solid #1e293b; border-radius:12px; padding:20px; display:flex; flex-direction:column; justify-content:space-between;">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
              <span style="font-size:1.8rem;">${f.icon}</span>
              <span style="background:${badgeColor}22; color:${badgeColor}; border:1px solid ${badgeColor}55; padding:3px 8px; border-radius:12px; font-size:0.75rem; font-weight:700;">
                ${f.status}
              </span>
            </div>
            <h4 style="margin:0 0 6px 0; color:#f1f5f9; font-size:1.05rem;">${f.title}</h4>
            <p style="margin:0; font-size:0.85rem; color:#94a3b8; line-height:1.4;">${f.tagline}</p>
          </div>
          <div style="margin-top:16px; pt-2; border-top:1px solid #1e293b; padding-top:12px; display:flex; justify-content:space-between; font-size:0.75rem; color:#64748b;">
            <span>PreTwin Strategic Initiative</span>
            <span>v2.4 Roadmap</span>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Roadmap features load error:", err);
  }
}

async function findGifts() {
  const recipient = document.getElementById("giftRecipient").value;
  const occasion = document.getElementById("giftOccasion").value;
  const budget = parseFloat(document.getElementById("giftBudget").value || 3000);

  const container = document.getElementById("giftResultsContainer");
  if (!container) return;

  container.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding:20px; color:#94a3b8;">Discovering personalized gift options...</div>`;

  try {
    const res = await fetch("/api/advanced/gift-finder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recipient, occasion, budget })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    const items = data.results || [];
    if (items.length === 0) {
      container.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding:20px; color:#94a3b8;">No matching gifts within ₹${budget}. Try increasing your budget.</div>`;
      return;
    }

    container.innerHTML = items.map(g => `
      <div style="background:#1e293b; border:1px solid #334155; border-radius:10px; padding:16px; display:flex; flex-direction:column; justify-content:space-between;">
        <div>
          <div style="position:relative; margin-bottom:10px;">
            ${g.image_url ? `<img src="${g.image_url}" style="width:100%; height:130px; object-fit:contain; border-radius:6px; background:#fff; padding:6px;">` : ""}
            <span style="position:absolute; top:6px; right:6px; background:#10b981; color:#fff; font-size:0.7rem; font-weight:700; padding:2px 6px; border-radius:4px;">🎁 Gift Wrap</span>
          </div>
          <div style="font-weight:600; color:#f1f5f9; font-size:0.9rem; margin-bottom:4px;">${g.name}</div>
          <div style="font-size:0.75rem; color:#c4b5fd; margin-bottom:8px;">${g.gift_note}</div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px; border-top:1px solid #334155; padding-top:10px;">
          <span style="font-weight:700; color:#22d3ee; font-size:1rem;">₹${Math.round(g.price).toLocaleString("en-IN")}</span>
          <button onclick="addGiftToCart('${g.name.replace(/'/g, "\\'")}', ${g.price}, '${g.image_url || ''}')" style="background:#6366f1; color:#fff; border:none; padding:6px 12px; border-radius:6px; font-size:0.8rem; font-weight:600; cursor:pointer;">
            Send Gift
          </button>
        </div>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<div style="grid-column: 1/-1; color:#ef4444;">Failed to generate gifts: ${err.message}</div>`;
  }
}

function addGiftToCart(name, price, img) {
  let cart = [];
  try {
    cart = JSON.parse(localStorage.getItem("pretwin_cart") || "[]");
  } catch (e) {
    cart = [];
  }
  cart.push({
    id: Date.now(),
    name: name,
    price: price,
    quantity: 1,
    category: "Gift Bundle",
    image_url: img
  });
  localStorage.setItem("pretwin_cart", JSON.stringify(cart));
  if (typeof showToast === "function") {
    showToast(`Added '${name}' to cart as gift!`, "success");
  } else {
    alert(`Added '${name}' to cart as gift!`);
  }
}

async function loadCalendarEvents() {
  const container = document.getElementById("calendarEventsList");
  if (!container) return;

  try {
    const res = await fetch("/api/calendar/events");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    const events = data.events || [];
    if (events.length === 0) {
      container.innerHTML = `<div style="color:#94a3b8; text-align:center; padding:20px;">No upcoming calendar milestones scheduled.</div>`;
      return;
    }

    container.innerHTML = events.map(ev => `
      <div style="background:#1e293b; border:1px solid #334155; border-radius:8px; padding:14px 18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
        <div style="display:flex; align-items:center; gap:14px;">
          <div style="background:rgba(168, 85, 247, 0.2); color:#c084fc; width:44px; height:44px; border-radius:8px; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:700;">
            <span style="font-size:0.7rem; text-transform:uppercase;">${ev.event_date ? ev.event_date.split("-")[1] : "NOV"}</span>
            <span style="font-size:1rem;">${ev.event_date ? ev.event_date.split("-")[2] : "15"}</span>
          </div>
          <div>
            <div style="font-weight:600; color:#f1f5f9; font-size:0.95rem;">${ev.title}</div>
            <div style="font-size:0.8rem; color:#94a3b8; margin-top:2px;">
              ${ev.event_type} • Budget: ₹${Math.round(ev.budget).toLocaleString("en-IN")}
            </div>
          </div>
        </div>
        <div>
          <span style="background:rgba(99, 102, 241, 0.15); color:#a5b4fc; border:1px solid rgba(99, 102, 241, 0.3); padding:4px 10px; border-radius:6px; font-size:0.8rem;">
            Auto-Scheduled
          </span>
        </div>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<div style="color:#ef4444;">Failed to load events: ${err.message}</div>`;
  }
}

function openAddEventModal() {
  const title = prompt("Enter event title (e.g., Sister's Birthday, Diwali):");
  if (!title) return;
  const dateStr = prompt("Enter event date (YYYY-MM-DD):", "2026-11-20");
  if (!dateStr) return;

  fetch("/api/calendar/events", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: title,
      event_date: dateStr,
      event_type: "Personal Milestone",
      budget: 3500
    })
  }).then(res => res.json()).then(data => {
    loadCalendarEvents();
  });
}

function setVoicePrompt(text) {
  document.getElementById("voiceInputTranscript").value = text;
  simulateVoiceCommand();
}

async function simulateVoiceCommand() {
  const input = document.getElementById("voiceInputTranscript");
  const transcript = input.value.trim();
  if (!transcript) return;

  try {
    const res = await fetch("/api/advanced/voice-simulator", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcript })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    const box = document.getElementById("voiceResponseBox");
    box.style.display = "block";
    document.getElementById("voiceReplyText").innerText = data.assistant_reply;
    document.getElementById("voiceActionText").innerText = `Triggered Action: [${data.detected_action.toUpperCase()}] with 96% linguistic confidence.`;
  } catch (err) {
    alert("Voice simulation error: " + err.message);
  }
}

async function simulateTryOn() {
  const cat = document.getElementById("tryOnCategory").value;
  const size = document.getElementById("tryOnSize").value;

  try {
    const res = await fetch("/api/advanced/try-on-simulator", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category: cat, size: size })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    document.getElementById("fitConfText").innerText = data.fit_confidence;
    document.getElementById("fitRecText").innerText = `${data.fit_recommendation} Return Risk: ${data.return_risk}`;
  } catch (err) {
    alert("Try-on error: " + err.message);
  }
}
