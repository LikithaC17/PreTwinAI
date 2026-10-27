/**
 * PreTwin Future Predictive Calendar Controller
 * Handles monthly grid rendering, event milestone tracking, PreTwin AI product suggestions,
 * and seamless cart/wishlist integration.
 */

let calCurrentDate = new Date();
let allCalendarEvents = [];
let currentCalendarView = 'grid';

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const EVENT_TYPE_BADGES = {
  "College": { label: "🎓 College & Campus", color: "#6366f1", bg: "#eef2ff" },
  "Interview": { label: "💼 Career & Interview", color: "#0284c7", bg: "#f0f9ff" },
  "Birthday": { label: "🎂 Birthday Celebration", color: "#ec4899", bg: "#fdf2f8" },
  "Festival": { label: "🪔 Festive & Holiday", color: "#d97706", bg: "#fffbeb" },
  "Household": { label: "🏠 Household Replenish", color: "#059669", bg: "#ecfdf5" },
  "Travel": { label: "✈️ Travel & Trip", color: "#8b5cf6", bg: "#f5f3ff" },
  "Fitness": { label: "💪 Fitness & Health", color: "#16a34a", bg: "#f0fdf4" },
  "General": { label: "🛍️ Personal Milestone", color: "#64748b", bg: "#f8fafc" }
};

document.addEventListener("DOMContentLoaded", () => {
  loadCalendarData();
});

async function loadCalendarData() {
  try {
    const res = await fetch("/api/calendar/events");
    const data = await res.json();
    allCalendarEvents = data.events || [];
    renderCalendar();
  } catch (err) {
    console.error("Failed to fetch calendar events:", err);
    showToast("Unable to load calendar events from server.", "error");
  }
}

function renderCalendar() {
  renderMonthHeader();
  renderGridDays();
  renderEventsList();
}

function renderMonthHeader() {
  const lbl = document.getElementById("currentMonthYearLabel");
  if (lbl) {
    const month = MONTH_NAMES[calCurrentDate.getMonth()];
    const year = calCurrentDate.getFullYear();
    lbl.textContent = `${month} ${year}`;
  }
}

function changeMonth(delta) {
  calCurrentDate.setMonth(calCurrentDate.getMonth() + delta);
  renderCalendar();
}

function goToToday() {
  calCurrentDate = new Date();
  renderCalendar();
}

function switchCalendarView(mode) {
  currentCalendarView = mode;
  const gridView = document.getElementById("calendarGridView");
  const listView = document.getElementById("calendarListView");
  const btnGrid = document.getElementById("viewBtnGrid");
  const btnList = document.getElementById("viewBtnList");

  if (mode === 'grid') {
    if (gridView) gridView.style.display = "block";
    if (listView) listView.style.display = "none";
    if (btnGrid) { btnGrid.style.background = "#7c3aed"; btnGrid.style.color = "#fff"; }
    if (btnList) { btnList.style.background = "#f8fafc"; btnList.style.color = "#64748b"; }
  } else {
    if (gridView) gridView.style.display = "none";
    if (listView) listView.style.display = "block";
    if (btnGrid) { btnGrid.style.background = "#f8fafc"; btnGrid.style.color = "#64748b"; }
    if (btnList) { btnList.style.background = "#7c3aed"; btnList.style.color = "#fff"; }
  }
}

function filterEvents() {
  renderGridDays();
  renderEventsList();
}

function getFilteredEvents() {
  const typeFilter = document.getElementById("eventFilterType")?.value || "ALL";
  if (typeFilter === "ALL") return allCalendarEvents;
  return allCalendarEvents.filter(e => e.event_type === typeFilter);
}

function renderGridDays() {
  const grid = document.getElementById("calendarDaysGrid");
  if (!grid) return;

  const year = calCurrentDate.getFullYear();
  const month = calCurrentDate.getMonth();
  const firstDayIndex = new Date(year, month, 1).getDay();
  const totalDays = new Date(year, month + 1, 0).getDate();
  const prevMonthTotalDays = new Date(year, month, 0).getDate();

  const today = new Date();
  const filteredEvents = getFilteredEvents();

  let html = "";

  // 1. Padding days from previous month
  for (let i = firstDayIndex - 1; i >= 0; i--) {
    const d = prevMonthTotalDays - i;
    html += `
      <div style="background:#f8fafc; border:1px solid #f1f5f9; border-radius:8px; min-height:105px; padding:8px; opacity:0.4;">
        <span style="font-size:0.82rem; font-weight:600; color:#94a3b8;">${d}</span>
      </div>
    `;
  }

  // 2. Days of current month
  for (let d = 1; d <= totalDays; d++) {
    const isToday = (today.getFullYear() === year && today.getMonth() === month && today.getDate() === d);
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    
    // Find events matching this date
    const dayEvents = filteredEvents.filter(ev => {
      const evDate = (ev.event_date || "").split("T")[0];
      return evDate === dateStr;
    });

    let eventsHtml = "";
    if (dayEvents.length > 0) {
      eventsHtml = dayEvents.map(ev => {
        const badgeMeta = EVENT_TYPE_BADGES[ev.event_type] || EVENT_TYPE_BADGES["General"];
        return `
          <div onclick="openEditEventModal(${ev.id})" title="${escapeHtml(ev.title)} (Click to view suggestions)" style="background:${badgeMeta.bg}; border-left:3px solid ${badgeMeta.color}; color:${badgeMeta.color}; font-size:0.75rem; font-weight:700; padding:3px 6px; border-radius:4px; margin-top:4px; cursor:pointer; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; transition:transform 0.15s ease;" onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
            ${escapeHtml(ev.title)}
          </div>
        `;
      }).join("");
    }

    html += `
      <div style="background:${isToday ? '#faf5ff' : '#ffffff'}; border:${isToday ? '2px solid #7c3aed' : '1px solid #e2e8f0'}; border-radius:8px; min-height:105px; padding:8px; display:flex; flex-direction:column; justify-content:space-between; transition:box-shadow 0.2s ease;" onmouseover="this.style.boxShadow='0 4px 12px rgba(0,0,0,0.06)'" onmouseout="this.style.boxShadow='none'">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:0.88rem; font-weight:${isToday ? '800' : '700'}; color:${isToday ? '#7c3aed' : '#1e293b'};">${d}</span>
          ${isToday ? '<span style="background:#7c3aed; color:#fff; font-size:0.65rem; font-weight:800; padding:1px 5px; border-radius:10px;">TODAY</span>' : ''}
        </div>
        <div style="flex:1; margin-top:4px; overflow-y:auto; max-height:80px;">
          ${eventsHtml}
        </div>
        <button onclick="openAddEventForDate('${dateStr}')" style="background:transparent; border:none; color:#94a3b8; font-size:0.75rem; cursor:pointer; align-self:flex-end; padding:2px;" title="Add milestone on this day">+</button>
      </div>
    `;
  }

  // 3. Trailing padding days to fill 7x5 or 7x6 grid
  const totalRendered = firstDayIndex + totalDays;
  const remainingCells = (Math.ceil(totalRendered / 7) * 7) - totalRendered;
  for (let i = 1; i <= remainingCells; i++) {
    html += `
      <div style="background:#f8fafc; border:1px solid #f1f5f9; border-radius:8px; min-height:105px; padding:8px; opacity:0.4;">
        <span style="font-size:0.82rem; font-weight:600; color:#94a3b8;">${i}</span>
      </div>
    `;
  }

  grid.innerHTML = html;
}

function renderEventsList() {
  const container = document.getElementById("calendarEventsCardsList");
  const countBadge = document.getElementById("eventsCountBadge");
  if (!container) return;

  const events = getFilteredEvents();
  if (countBadge) countBadge.textContent = `${events.length} Milestones Tracked`;

  if (events.length === 0) {
    container.innerHTML = `
      <div class="card" style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:40px; text-align:center;">
        <span style="font-size:3rem; margin-bottom:12px; display:inline-block;">📅</span>
        <h4 style="font-size:1.2rem; font-weight:700; color:#1e1b4b; margin:0 0 6px 0;">No Shopping Milestones Found</h4>
        <p style="color:#64748b; font-size:0.9rem; max-width:440px; margin:0 auto 18px auto;">
          Stay ahead of your college semester, birthdays, and household needs with synchronized predictive scheduling.
        </p>
        <button onclick="openAddEventModal()" style="padding:10px 20px; background:#7c3aed; color:#fff; border:none; border-radius:8px; font-weight:700; cursor:pointer;">
          + Add First Shopping Milestone
        </button>
      </div>
    `;
    return;
  }

  container.innerHTML = events.map(ev => {
    const badgeMeta = EVENT_TYPE_BADGES[ev.event_type] || EVENT_TYPE_BADGES["General"];
    const daysRem = ev.days_remaining;
    
    let daysBadge = "";
    if (daysRem < 0) {
      daysBadge = `<span style="background:#fee2e2; color:#b91c1c; font-size:0.75rem; font-weight:700; padding:3px 8px; border-radius:12px;">Elapsed Milestone</span>`;
    } else if (daysRem === 0) {
      daysBadge = `<span style="background:#fef08a; color:#854d0e; font-size:0.75rem; font-weight:800; padding:3px 8px; border-radius:12px;">⚡ Due Today!</span>`;
    } else if (daysRem <= 7) {
      daysBadge = `<span style="background:#fdf2f8; color:#be185d; font-size:0.75rem; font-weight:800; padding:3px 8px; border-radius:12px;">In ${daysRem} Days (Approaching Soon)</span>`;
    } else {
      daysBadge = `<span style="background:#ede9fe; color:#6d28d9; font-size:0.75rem; font-weight:700; padding:3px 8px; border-radius:12px;">In ${daysRem} Days</span>`;
    }

    const isAi = ev.is_ai_predicted === 1;
    const originBadge = isAi 
      ? `<span style="background:#faf5ff; border:1px solid #d8b4fe; color:#7c3aed; font-size:0.72rem; font-weight:700; padding:2px 8px; border-radius:10px;">✨ PreTwin AI Forecast</span>`
      : `<span style="background:#f8fafc; border:1px solid #cbd5e1; color:#475569; font-size:0.72rem; font-weight:700; padding:2px 8px; border-radius:10px;">👤 Personal Event</span>`;

    // Render suggested products
    let prodsHtml = "";
    const prods = ev.suggested_products || [];
    if (prods.length > 0) {
      prodsHtml = `
        <div style="margin-top:16px; padding-top:14px; border-top:1px solid #f1f5f9;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <div style="font-size:0.85rem; font-weight:700; color:#1e1b4b; display:flex; align-items:center; gap:6px;">
              <span>🛍️ PreTwin Verified Product Recommendations</span>
              <span style="font-size:0.75rem; color:#64748b; font-weight:normal;">(Within ₹${Number(ev.budget || 5000).toLocaleString('en-IN')} Budget)</span>
            </div>
            <span style="font-size:0.75rem; color:#10b981; font-weight:700;">● Catalogue Synced</span>
          </div>
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px;">
            ${prods.map(p => `
              <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px; display:flex; gap:10px; align-items:center;">
                <img src="${p.image_url || '/static/images/placeholder.jpg'}" alt="${escapeHtml(p.name)}" style="width:54px; height:54px; object-fit:contain; border-radius:6px; background:#fff; border:1px solid #f1f5f9;" onerror="this.src='/static/images/placeholder.jpg'">
                <div style="flex:1; min-width:0;">
                  <div style="font-size:0.82rem; font-weight:700; color:#1e293b; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(p.name)}">
                    ${escapeHtml(p.name)}
                  </div>
                  <div style="font-size:0.85rem; font-weight:800; color:#7c3aed;">
                    ₹${Number(p.price || 0).toLocaleString('en-IN')}
                  </div>
                  <div style="display:flex; gap:6px; margin-top:4px;">
                    <button onclick="addCalendarItemToCart(${p.id}, '${escapeHtml(p.name).replace(/'/g, "\\'")}', ${p.price}, '${p.image_url || ''}')" style="background:#7c3aed; color:#fff; border:none; padding:3px 8px; border-radius:4px; font-size:0.7rem; font-weight:700; cursor:pointer;">
                      + Cart
                    </button>
                    <button onclick="addCalendarItemToWishlist(${p.id})" style="background:#fff; color:#64748b; border:1px solid #cbd5e1; padding:3px 8px; border-radius:4px; font-size:0.7rem; font-weight:700; cursor:pointer;" title="Save to Wishlist">
                      ❤️
                    </button>
                    <button onclick="dismissEventSuggestion(${ev.id}, ${p.id})" style="background:transparent; border:none; color:#94a3b8; font-size:0.75rem; cursor:pointer;" title="Dismiss suggestion">
                      ✕
                    </button>
                  </div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    return `
      <div class="card" style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:20px 24px; box-shadow:0 2px 10px rgba(0,0,0,0.03);">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
          <div>
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px; flex-wrap:wrap;">
              <span style="background:${badgeMeta.bg}; color:${badgeMeta.color}; border:1px solid ${badgeMeta.color}44; font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:12px;">
                ${badgeMeta.label}
              </span>
              ${originBadge}
              ${daysBadge}
            </div>
            <h4 style="margin:0 0 6px 0; font-size:1.15rem; font-weight:800; color:#1e1b4b;">
              ${escapeHtml(ev.title)}
            </h4>
            <div style="font-size:0.85rem; color:#64748b; display:flex; align-items:center; gap:16px; flex-wrap:wrap;">
              <span>📅 Target Date: <strong>${ev.event_date ? ev.event_date.split('T')[0] : 'N/A'}</strong></span>
              <span>💰 Budget: <strong>₹${Number(ev.budget || 0).toLocaleString('en-IN')}</strong></span>
              <span>🏷️ Category: <strong>${escapeHtml(ev.category || 'All')}</strong></span>
            </div>
            ${ev.notes ? `<p style="margin:8px 0 0 0; font-size:0.85rem; color:#475569; line-height:1.4;">${escapeHtml(ev.notes)}</p>` : ''}
          </div>

          <div style="display:flex; gap:8px;">
            <button onclick="openEditEventModal(${ev.id})" style="background:#f8fafc; border:1px solid #cbd5e1; color:#475569; padding:6px 12px; border-radius:6px; font-size:0.8rem; font-weight:600; cursor:pointer;">
              ✏️ Edit
            </button>
            <button onclick="deleteCalendarEvent(${ev.id})" style="background:#fee2e2; border:1px solid #fecaca; color:#b91c1c; padding:6px 12px; border-radius:6px; font-size:0.8rem; font-weight:600; cursor:pointer;">
              🗑️ Delete
            </button>
          </div>
        </div>

        ${prodsHtml}
      </div>
    `;
  }).join("");
}

function openAddEventModal() {
  document.getElementById("calendarModalTitle").textContent = "Add Shopping Milestone";
  document.getElementById("calEventId").value = "";
  document.getElementById("calTitleInput").value = "";
  
  // Default date 14 days from now
  const defDate = new Date();
  defDate.setDate(defDate.getDate() + 14);
  document.getElementById("calDateInput").value = defDate.toISOString().split("T")[0];
  
  document.getElementById("calTypeInput").value = "College";
  document.getElementById("calCategoryInput").value = "All";
  document.getElementById("calBudgetInput").value = "5000";
  document.getElementById("calNotesInput").value = "";
  
  const modal = document.getElementById("calendarModal");
  if (modal) modal.style.display = "flex";
}

function openAddEventForDate(dateStr) {
  openAddEventModal();
  document.getElementById("calDateInput").value = dateStr;
}

function openEditEventModal(id) {
  const ev = allCalendarEvents.find(e => e.id === id);
  if (!ev) return;

  document.getElementById("calendarModalTitle").textContent = "Edit Shopping Milestone";
  document.getElementById("calEventId").value = ev.id;
  document.getElementById("calTitleInput").value = ev.title || "";
  document.getElementById("calDateInput").value = ev.event_date ? ev.event_date.split("T")[0] : "";
  document.getElementById("calTypeInput").value = ev.event_type || "College";
  document.getElementById("calCategoryInput").value = ev.category || "All";
  document.getElementById("calBudgetInput").value = ev.budget || 5000;
  document.getElementById("calNotesInput").value = ev.notes || "";

  const modal = document.getElementById("calendarModal");
  if (modal) modal.style.display = "flex";
}

function closeCalendarModal() {
  const modal = document.getElementById("calendarModal");
  if (modal) modal.style.display = "none";
}

async function handleCalendarFormSubmit(e) {
  e.preventDefault();
  const id = document.getElementById("calEventId").value;
  const title = document.getElementById("calTitleInput").value.trim();
  const event_date = document.getElementById("calDateInput").value;
  const event_type = document.getElementById("calTypeInput").value;
  const category = document.getElementById("calCategoryInput").value;
  const budget = parseFloat(document.getElementById("calBudgetInput").value || 5000);
  const notes = document.getElementById("calNotesInput").value.trim();

  if (!title || !event_date) {
    alert("Please enter both Title and Target Date.");
    return;
  }

  const payload = { title, event_date, event_type, category, budget, notes };
  const submitBtn = document.getElementById("calSubmitBtn");
  submitBtn.disabled = true;
  submitBtn.textContent = "Saving...";

  try {
    let url = "/api/calendar/events";
    let method = "POST";
    if (id) {
      url = `/api/calendar/events/${id}`;
      method = "PUT";
    }

    const res = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to save milestone");

    closeCalendarModal();
    if (typeof showToast === "function") {
      showToast(data.message || "Shopping milestone saved successfully!", "success");
    } else {
      alert("Shopping milestone saved successfully!");
    }
    await loadCalendarData();
  } catch (err) {
    alert("Error: " + err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Save Milestone";
  }
}

async function deleteCalendarEvent(id) {
  if (!confirm("Are you sure you want to remove this shopping milestone?")) return;

  try {
    const res = await fetch(`/api/calendar/events/${id}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    if (typeof showToast === "function") {
      showToast("Milestone removed from calendar.", "info");
    }
    await loadCalendarData();
  } catch (err) {
    alert("Delete failed: " + err.message);
  }
}

async function dismissEventSuggestion(eventId, productId) {
  try {
    await fetch(`/api/calendar/events/${eventId}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "dismiss", product_id: productId })
    });
    await loadCalendarData();
  } catch (e) {
    console.warn("Dismiss suggestion error:", e);
  }
}

function addCalendarItemToCart(id, name, price, imageUrl) {
  if (typeof addToCart === "function") {
    addToCart(id, name, price, imageUrl);
  } else {
    // Fallback direct storage
    let cart = [];
    try { cart = JSON.parse(localStorage.getItem("pretwin_cart") || "[]"); } catch(e){ cart = []; }
    const ex = cart.find(x => x.product_id === id);
    if (ex) ex.quantity += 1;
    else cart.push({ product_id: id, id: id, name, price, image_url: imageUrl, quantity: 1 });
    localStorage.setItem("pretwin_cart", JSON.stringify(cart));
    if (typeof showToast === "function") showToast(`Added ${name} to cart!`, "success");
  }
}

function addCalendarItemToWishlist(productId) {
  if (typeof toggleWishlist === "function") {
    toggleWishlist({ id: productId });
  } else {
    fetch("/api/wishlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: productId })
    }).then(() => {
      if (typeof showToast === "function") showToast("Saved to your Wishlist!", "success");
    });
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}