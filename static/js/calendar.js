/**
 * static/js/calendar.js
 * =====================
 * PreTwin AI - Future Predictive Calendar Controller (Feature 6)
 * Implements the Seven Dedicated Sections:
 * 1. My Shopping Calendar (Month, Week, Day views; leap years; status coloring)
 * 2. Upcoming Predictions (Replenishment models, confidence ratings, convert to plan)
 * 3. My Shopping Plans (Active, Overdue, Completed, Cancelled tabs, priority badges)
 * 4. Occasions and Events (Personal occasions, budgets, preparation dates)
 * 5. Future Shopping Budget (Planned vs Estimated vs Actual, Feature 4 integration)
 * 6. Reminders and Notifications (In-app notification list, snooze, dismiss)
 * 7. Calendar Insights and History (Completion stats, on-time rate)
 */

let calCurrentDate = new Date();
let currentViewMode = 'month'; // 'month' | 'week' | 'day'
let allUnifiedActivities = [];
let cachedCalendarView = null;

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

function formatCurrency(val) {
  const num = Number(val) || 0;
  return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function notifyToast(msg, type = 'info') {
  if (typeof window.showToast === 'function') {
    window.showToast(msg, type);
  } else {
    alert(msg);
  }
}

// =============================================================================
// Initialization
// =============================================================================

document.addEventListener("DOMContentLoaded", () => {
  initCalendarDashboard();
});

async function initCalendarDashboard() {
  updateHeaderTodayDate();
  await loadCalendarView();
  await loadUpcomingPredictions();
  await loadShoppingPlans('active');
  await loadOccasions();
  await loadFutureBudgetSummary();
  await loadInAppReminders();
  await loadCalendarInsights();
}

function updateHeaderTodayDate() {
  const el = document.getElementById('headerTodayDate');
  if (el) {
    const today = new Date();
    const options = { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' };
    el.textContent = today.toLocaleDateString('en-IN', options);
  }
}

// =============================================================================
// SECTION 1: MY SHOPPING CALENDAR
// =============================================================================

async function loadCalendarView() {
  const dateStr = calCurrentDate.toISOString().split('T')[0];
  const typeFilter = document.getElementById('eventFilterType') ? document.getElementById('eventFilterType').value : 'ALL';

  try {
    const res = await fetch(`/api/calendar/view?mode=${currentViewMode}&date=${dateStr}&event_type=${encodeURIComponent(typeFilter)}`);
    if (!res.ok) throw new Error('Failed to load calendar view');
    const data = await res.json();
    cachedCalendarView = data;

    renderMonthYearHeader(data);

    if (currentViewMode === 'month') {
      renderMonthGrid(data);
    } else if (currentViewMode === 'week') {
      renderWeekGrid(data);
    } else if (currentViewMode === 'day') {
      renderDayTimeline(data);
    }
  } catch (err) {
    console.error('loadCalendarView error:', err);
  }
}

function renderMonthYearHeader(data) {
  const lbl = document.getElementById("currentMonthYearLabel");
  if (lbl) {
    lbl.textContent = data.display_title || `${MONTH_NAMES[calCurrentDate.getMonth()]} ${calCurrentDate.getFullYear()}`;
  }
}

function renderMonthGrid(data) {
  const grid = document.getElementById("calendarDaysGrid");
  if (!grid || !data.days) return;

  grid.innerHTML = data.days.map(cell => {
    const isToday = cell.is_today;
    const isPadding = !cell.is_current_month;
    const acts = cell.activities || [];

    const actsHtml = acts.map(act => {
      const c = act.color_info || { color: '#7C3AED', bg: '#F5EEFF', border: '#C4A6F5' };
      return `
        <div class="cal-event-chip" style="background:${c.bg}; color:${c.color}; border-left:3px solid ${c.border};"
             title="${escapeHtml(act.title)} (${formatCurrency(act.budget)})"
             onclick="event.stopPropagation(); showActivityDetails('${act.id}', '${escapeHtml(act.title)}', '${act.date}', '${formatCurrency(act.budget)}', '${escapeHtml(act.notes)}')">
          ${escapeHtml(act.title)}
        </div>
      `;
    }).join('');

    return `
      <div class="calendar-cell ${isToday ? 'is-today' : ''} ${isPadding ? 'is-padding' : ''}"
           onclick="openAddEventForDate('${cell.date}')">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:0.85rem; font-weight:${isToday ? '800' : '700'}; color:${isToday ? '#7C3AED' : 'var(--cal-text)'};">${cell.day_number}</span>
          ${isToday ? '<span style="background:#7C3AED; color:#FFFFFF; font-size:0.6rem; font-weight:800; padding:1px 5px; border-radius:8px;">TODAY</span>' : ''}
        </div>
        <div style="flex:1; margin-top:4px; overflow-y:auto; max-height:80px;">
          ${actsHtml}
        </div>
        <div style="text-align:right; font-size:0.7rem; color:var(--cal-text-muted); opacity:0.6;">+</div>
      </div>
    `;
  }).join('');
}

function renderWeekGrid(data) {
  const grid = document.getElementById("calendarWeekGrid");
  if (!grid || !data.days) return;

  grid.innerHTML = data.days.map(day => `
    <div style="background:#FFFFFF; border:1px solid var(--cal-border); border-radius:12px; min-height:220px; padding:12px; display:flex; flex-direction:column;">
      <div style="text-align:center; padding-bottom:8px; border-bottom:1px solid var(--cal-border); margin-bottom:8px;">
        <span style="display:block; font-size:0.75rem; color:var(--cal-text-muted); font-weight:700; text-transform:uppercase;">${day.day_name}</span>
        <strong style="font-size:1.15rem; color:${day.is_today ? '#7C3AED' : 'var(--cal-text)'};">${day.day_number}</strong>
      </div>
      <div style="flex:1; overflow-y:auto;">
        ${(day.activities || []).map(act => {
          const c = act.color_info || { color: '#7C3AED', bg: '#F5EEFF', border: '#C4A6F5' };
          return `
            <div class="cal-event-chip" style="background:${c.bg}; color:${c.color}; border-left:3px solid ${c.border}; margin-bottom:6px; padding:6px;"
                 title="${escapeHtml(act.title)}">
              <strong>${escapeHtml(act.title)}</strong>
              <div style="font-size:0.68rem; opacity:0.8;">${formatCurrency(act.budget)}</div>
            </div>
          `;
        }).join('')}
      </div>
      <button class="btn-outline-cal" style="font-size:0.72rem; padding:4px 8px; width:100%; justify-content:center; margin-top:6px;"
              onclick="openAddEventForDate('${day.date}')">+ Add Activity</button>
    </div>
  `).join('');
}

function renderDayTimeline(data) {
  const container = document.getElementById("calendarDayTimeline");
  if (!container) return;

  const acts = data.activities || [];
  if (acts.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding:32px; color:var(--cal-text-muted);">
        <span style="font-size:2rem; display:block; margin-bottom:8px;">📅</span>
        <h4 style="margin:0 0 4px 0; color:var(--cal-text);">No Activities Scheduled for this Day</h4>
        <p style="font-size:0.88rem; margin:0 0 16px 0;">Organise a future purchase, set an occasion, or add a shopping milestone.</p>
        <button class="btn-primary-cal" onclick="openAddEventForDate('${data.current_date}')">+ Add Activity on this Day</button>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
      <h3 style="margin:0; font-size:1.15rem; font-weight:800; color:var(--cal-text);">${data.display_title}</h3>
      <button class="btn-outline-cal" onclick="openAddEventForDate('${data.current_date}')">+ Add Activity</button>
    </div>
    <div style="display:flex; flex-direction:column; gap:10px;">
      ${acts.map(act => {
        const c = act.color_info || { color: '#7C3AED', bg: '#F5EEFF', border: '#C4A6F5' };
        return `
          <div style="background:${c.bg}; border-left:4px solid ${c.border}; border:1px solid var(--cal-border); border-left-width:4px; border-radius:10px; padding:14px 18px; display:flex; justify-content:space-between; align-items:center;">
            <div>
              <div style="display:inline-block; font-size:0.72rem; font-weight:800; color:${c.color}; text-transform:uppercase; margin-bottom:4px;">${act.activity_type}</div>
              <h4 style="margin:0 0 4px 0; font-size:1rem; font-weight:800; color:var(--cal-text);">${escapeHtml(act.title)}</h4>
              <p style="margin:0; font-size:0.82rem; color:var(--cal-text-muted);">${escapeHtml(act.notes || 'No extra notes provided.')}</p>
            </div>
            <div style="text-align:right;">
              <strong style="color:${c.color}; font-size:1.1rem; display:block;">${formatCurrency(act.budget)}</strong>
              <span style="font-size:0.75rem; color:var(--cal-text-muted); text-transform:capitalize;">${act.status}</span>
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

function changeMonth(delta) {
  if (currentViewMode === 'month') {
    calCurrentDate.setMonth(calCurrentDate.getMonth() + delta);
  } else if (currentViewMode === 'week') {
    calCurrentDate.setDate(calCurrentDate.getDate() + (delta * 7));
  } else if (currentViewMode === 'day') {
    calCurrentDate.setDate(calCurrentDate.getDate() + delta);
  }
  loadCalendarView();
}

function goToToday() {
  calCurrentDate = new Date();
  loadCalendarView();
}

function switchCalendarView(mode) {
  currentViewMode = mode;
  const monthView = document.getElementById("calendarGridView");
  const weekView = document.getElementById("calendarWeekView");
  const dayView = document.getElementById("calendarDayView");

  const btnMonth = document.getElementById("viewBtnMonth");
  const btnWeek = document.getElementById("viewBtnWeek");
  const btnDay = document.getElementById("viewBtnDay");

  [btnMonth, btnWeek, btnDay].forEach(btn => {
    if (btn) {
      btn.style.background = "#FFFDF9";
      btn.style.color = "var(--cal-text-muted)";
    }
  });

  if (monthView) monthView.style.display = mode === 'month' ? 'block' : 'none';
  if (weekView) weekView.style.display = mode === 'week' ? 'block' : 'none';
  if (dayView) dayView.style.display = mode === 'day' ? 'block' : 'none';

  if (mode === 'month' && btnMonth) { btnMonth.style.background = "var(--cal-secondary)"; btnMonth.style.color = "var(--cal-text)"; }
  if (mode === 'week' && btnWeek) { btnWeek.style.background = "var(--cal-secondary)"; btnWeek.style.color = "var(--cal-text)"; }
  if (mode === 'day' && btnDay) { btnDay.style.background = "var(--cal-secondary)"; btnDay.style.color = "var(--cal-text)"; }

  loadCalendarView();
}

function filterEvents() {
  loadCalendarView();
}

function showActivityDetails(id, title, date, budget, notes) {
  alert(`Activity: ${title}\nDate: ${date}\nBudget: ${budget}\nNotes: ${notes}`);
}

// =============================================================================
// SECTION 2: UPCOMING SHOPPING PREDICTIONS
// =============================================================================

async function loadUpcomingPredictions() {
  const container = document.getElementById('predictionsCardsGrid');
  if (!container) return;

  try {
    const res = await fetch('/api/calendar/predictions');
    if (!res.ok) throw new Error('Failed to load predictions');
    const data = await res.json();
    const preds = data.predictions || [];

    if (!data.has_sufficient_data || preds.length === 0) {
      container.innerHTML = `
        <div style="grid-column:1/-1; background:#FFFDF9; border:1px dashed var(--cal-border); border-radius:14px; padding:32px; text-align:center;">
          <span style="font-size:2rem; display:block; margin-bottom:8px;">📊</span>
          <h4 style="margin:0 0 6px 0; font-size:1.05rem; font-weight:800; color:var(--cal-text);">Insufficient Repeat Purchase Records</h4>
          <p style="margin:0; font-size:0.88rem; color:var(--cal-text-muted); max-width:520px; margin:0 auto; line-height:1.5;">
            ${data.message || 'Complete additional repeat orders to enable statistically reliable replenishment predictions.'}
          </p>
        </div>
      `;
      return;
    }

    container.innerHTML = preds.map(p => `
      <div style="background:#FFFDF9; border:1.5px solid var(--cal-border); border-radius:14px; padding:20px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 4px 14px rgba(64,54,83,0.03);">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
            <span style="background:#F5EEFF; color:#7C3AED; border:1px solid #C4A6F5; font-size:0.75rem; font-weight:800; padding:2px 8px; border-radius:10px;">
              ${p.confidence_level} Confidence
            </span>
            <span style="font-size:0.75rem; color:var(--cal-text-muted); font-weight:600;">Every ~${p.estimated_interval_days} Days</span>
          </div>

          <h4 style="margin:0 0 6px 0; font-size:1.05rem; font-weight:800; color:var(--cal-text);">${escapeHtml(p.product_name)}</h4>
          <p style="margin:0 0 10px 0; font-size:0.82rem; color:var(--cal-text-muted); line-height:1.4;">${escapeHtml(p.explanation)}</p>

          <div style="background:var(--cal-bg); padding:10px 12px; border-radius:8px; font-size:0.82rem; margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
              <span style="color:var(--cal-text-muted);">Estimated Next Date:</span>
              <strong style="color:#7C3AED;">${p.predicted_next_date} (${p.days_until_next_purchase} days left)</strong>
            </div>
            <div style="display:flex; justify-content:space-between;">
              <span style="color:var(--cal-text-muted);">Estimated Budget:</span>
              <strong>${formatCurrency(p.estimated_budget)}</strong>
            </div>
          </div>
        </div>

        <div style="display:flex; gap:8px;">
          <button class="btn-primary-cal" style="flex:1; font-size:0.78rem; padding:7px 10px;"
                  onclick="convertPredictionToPlan('${escapeHtml(p.product_name)}', '${escapeHtml(p.category)}', '${p.predicted_next_date}', ${p.estimated_budget})">
            ✓ Accept &amp; Convert to Plan
          </button>
        </div>
      </div>
    `).join('');

  } catch (err) {
    console.error('loadUpcomingPredictions error:', err);
  }
}

async function convertPredictionToPlan(productName, category, date, budget) {
  try {
    const res = await fetch('/api/calendar/predictions/convert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_name: productName,
        category: category,
        predicted_next_date: date,
        estimated_budget: budget
      })
    });
    if (!res.ok) throw new Error('Conversion failed');
    notifyToast(`Converted "${productName}" to shopping plan!`, 'success');
    await loadShoppingPlans('active');
    await loadCalendarView();
    await loadFutureBudgetSummary();
  } catch (err) {
    notifyToast(err.message, 'error');
  }
}

// =============================================================================
// SECTION 3: MY SHOPPING PLANS
// =============================================================================

async function loadShoppingPlans(status = 'active') {
  const container = document.getElementById('shoppingPlansCardsGrid');
  if (!container) return;

  try {
    const res = await fetch(`/api/calendar/plans?status=${status}`);
    if (!res.ok) throw new Error('Failed to load plans');
    const data = await res.json();
    const plans = data.plans || [];

    if (plans.length === 0) {
      container.innerHTML = `
        <div style="grid-column:1/-1; background:#FFFDF9; border:1px dashed var(--cal-border); border-radius:14px; padding:32px; text-align:center;">
          <span style="font-size:2rem; display:block; margin-bottom:8px;">📋</span>
          <h4 style="margin:0 0 6px 0; font-size:1.05rem; font-weight:800; color:var(--cal-text);">No ${status} shopping plans found</h4>
          <p style="margin:0 0 16px 0; font-size:0.88rem; color:var(--cal-text-muted);">Create a future shopping plan with your desired target date and budget cap.</p>
          <button class="btn-primary-cal" onclick="openCreatePlanModal()">+ Create Shopping Plan</button>
        </div>
      `;
      return;
    }

    container.innerHTML = plans.map(p => {
      const isOverdue = p.is_overdue;
      const isCompleted = p.status === 'completed';
      const priorityColor = p.priority === 'High' ? '#DC2626' : (p.priority === 'Low' ? '#475569' : '#D97706');

      return `
        <div style="background:#FFFDF9; border:1.5px solid ${isOverdue ? '#EF4444' : 'var(--cal-border)'}; border-radius:14px; padding:18px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 4px 14px rgba(64,54,83,0.03);">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
              <span style="font-size:0.75rem; font-weight:800; color:${priorityColor}; background:var(--cal-bg); border:1px solid var(--cal-border); padding:2px 8px; border-radius:10px;">
                ${p.priority || 'Medium'} Priority
              </span>
              <span style="font-size:0.75rem; font-weight:700; color:${isOverdue ? '#DC2626' : (isCompleted ? '#059669' : '#2563EB')}; text-transform:uppercase;">
                ${p.display_status || p.status}
              </span>
            </div>

            <h4 style="margin:0 0 6px 0; font-size:1.05rem; font-weight:800; color:var(--cal-text);">${escapeHtml(p.title)}</h4>
            <div style="font-size:0.8rem; color:var(--cal-text-muted); margin-bottom:10px;">${p.category || 'All Categories'}</div>

            <div style="background:var(--cal-bg); padding:10px 12px; border-radius:8px; font-size:0.82rem; margin-bottom:14px;">
              <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                <span style="color:var(--cal-text-muted);">Target Date:</span>
                <strong>${p.target_date}</strong>
              </div>
              <div style="display:flex; justify-content:space-between;">
                <span style="color:var(--cal-text-muted);">Budget Cap:</span>
                <strong style="color:#7C3AED;">${formatCurrency(p.estimated_budget)}</strong>
              </div>
            </div>
          </div>

          <div style="display:flex; gap:6px; flex-wrap:wrap; border-top:1px solid var(--cal-border); padding-top:12px;">
            ${!isCompleted ? `
              <button class="btn-primary-cal" style="flex:1; font-size:0.75rem; padding:6px 10px;" onclick="markPlanCompleted(${p.id})">
                ✓ Mark Done
              </button>
            ` : ''}
            <button class="btn-outline-cal" style="font-size:0.75rem; padding:6px 10px; color:#DC2626; border-color:#FCA5A5;" onclick="deleteShoppingPlan(${p.id})">
              Delete
            </button>
          </div>
        </div>
      `;
    }).join('');

  } catch (err) {
    console.error('loadShoppingPlans error:', err);
  }
}

function filterPlansByStatus(status, btn) {
  document.querySelectorAll('.active-plan-tab').forEach(b => {
    b.classList.remove('active-plan-tab');
    b.style.background = '#FFFFFF';
  });
  if (btn) {
    btn.classList.add('active-plan-tab');
    btn.style.background = 'var(--cal-secondary)';
  }
  loadShoppingPlans(status);
}

async function markPlanCompleted(planId) {
  try {
    const res = await fetch(`/api/calendar/plans/${planId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'completed' })
    });
    if (!res.ok) throw new Error('Update failed');
    notifyToast('Plan marked as completed!', 'success');
    await loadShoppingPlans('active');
    await loadCalendarView();
    await loadCalendarInsights();
  } catch (err) {
    notifyToast(err.message, 'error');
  }
}

async function deleteShoppingPlan(planId) {
  if (!confirm('Are you sure you want to delete this shopping plan?')) return;
  try {
    const res = await fetch(`/api/calendar/plans/${planId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Delete failed');
    notifyToast('Shopping plan deleted', 'info');
    await loadShoppingPlans('active');
    await loadCalendarView();
    await loadFutureBudgetSummary();
    await loadCalendarInsights();
  } catch (err) {
    notifyToast(err.message, 'error');
  }
}

// =============================================================================
// SECTION 4: OCCASIONS AND EVENTS
// =============================================================================

async function loadOccasions() {
  const container = document.getElementById('occasionsCardsGrid');
  if (!container) return;

  try {
    const res = await fetch('/api/calendar/occasions');
    if (!res.ok) throw new Error('Failed to load occasions');
    const data = await res.json();
    const occs = data.occasions || [];

    if (occs.length === 0) {
      container.innerHTML = `
        <div style="grid-column:1/-1; background:#FFFDF9; border:1px dashed var(--cal-border); border-radius:14px; padding:32px; text-align:center;">
          <span style="font-size:2rem; display:block; margin-bottom:8px;">🎉</span>
          <h4 style="margin:0 0 6px 0; font-size:1.05rem; font-weight:800; color:var(--cal-text);">No Personal Occasions Added Yet</h4>
          <p style="margin:0 0 16px 0; font-size:0.88rem; color:var(--cal-text-muted);">Add Birthdays, Festivals, Weddings, Vacations, or College Milestones.</p>
          <button class="btn-primary-cal" onclick="openCreateOccasionModal()">+ Add Personal Occasion</button>
        </div>
      `;
      return;
    }

    container.innerHTML = occs.map(o => `
      <div style="background:#FFFDF9; border:1.5px solid var(--cal-border); border-radius:14px; padding:18px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 4px 14px rgba(64,54,83,0.03);">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="background:#FFFBEB; color:#D97706; border:1px solid #FCD34D; font-size:0.75rem; font-weight:800; padding:2px 8px; border-radius:10px;">
              ${o.occasion_type || 'Special Occasion'}
            </span>
            <span style="font-size:0.78rem; font-weight:700; color:#7C3AED;">${o.event_date}</span>
          </div>

          <h4 style="margin:0 0 6px 0; font-size:1.05rem; font-weight:800; color:var(--cal-text);">${escapeHtml(o.event_name)}</h4>
          <p style="margin:0 0 12px 0; font-size:0.82rem; color:var(--cal-text-muted); line-height:1.4;">${escapeHtml(o.shopping_requirements || 'No specific requirements.')}</p>

          <div style="background:var(--cal-bg); padding:10px 12px; border-radius:8px; font-size:0.82rem; margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between;">
              <span style="color:var(--cal-text-muted);">Planned Budget:</span>
              <strong style="color:#D97706;">${formatCurrency(o.estimated_budget)}</strong>
            </div>
          </div>
        </div>

        <div style="display:flex; justify-content:flex-end;">
          <button class="btn-outline-cal" style="font-size:0.75rem; padding:5px 10px; color:#DC2626; border-color:#FCA5A5;" onclick="deleteOccasion(${o.id})">
            Remove
          </button>
        </div>
      </div>
    `).join('');

  } catch (err) {
    console.error('loadOccasions error:', err);
  }
}

async function deleteOccasion(id) {
  if (!confirm('Remove this occasion from calendar?')) return;
  try {
    const res = await fetch(`/api/calendar/occasions/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Delete failed');
    notifyToast('Occasion removed', 'info');
    await loadOccasions();
    await loadCalendarView();
    await loadFutureBudgetSummary();
  } catch (err) {
    notifyToast(err.message, 'error');
  }
}

// =============================================================================
// SECTION 5: FUTURE SHOPPING BUDGET
// =============================================================================

async function loadFutureBudgetSummary() {
  try {
    const res = await fetch('/api/calendar/budget-summary');
    if (!res.ok) return;
    const data = await res.json();

    const totEl = document.getElementById('totalFutureExpensesVal');
    const monthEl = document.getElementById('currentMonthPlannedVal');
    const limitEl = document.getElementById('activeMonthlyBudgetVal');
    const badgeEl = document.getElementById('currentMonthKeyBadge');
    const statusEl = document.getElementById('budgetStatusNotice');

    if (totEl) totEl.textContent = formatCurrency(data.total_estimated_future_expenses);
    if (monthEl) monthEl.textContent = formatCurrency(data.current_month_planned);
    if (limitEl) limitEl.textContent = formatCurrency(data.active_monthly_budget);
    if (badgeEl) badgeEl.textContent = `Month: ${data.current_month_key}`;

    if (statusEl) {
      if (data.is_within_monthly_budget) {
        statusEl.textContent = '✓ Within Monthly Budget';
        statusEl.style.color = '#059669';
      } else {
        statusEl.textContent = '⚠ Exceeds Active Budget Limit';
        statusEl.style.color = '#DC2626';
      }
    }

    // Monthly breakdown list
    const mList = document.getElementById('monthlyBreakdownList');
    if (mList) {
      const breakdown = data.monthly_planned_breakdown || {};
      const keys = Object.keys(breakdown);
      if (keys.length === 0) {
        mList.innerHTML = `<span style="font-size:0.8rem; color:var(--cal-text-muted); font-style:italic;">No upcoming planned expenses.</span>`;
      } else {
        mList.innerHTML = keys.map(k => `
          <div style="display:flex; justify-content:space-between; font-size:0.82rem; padding:4px 0; border-bottom:1px solid var(--cal-border);">
            <span>${k}</span>
            <strong style="color:#7C3AED;">${formatCurrency(breakdown[k])}</strong>
          </div>
        `).join('');
      }
    }

    // Category breakdown list
    const cList = document.getElementById('categoryBreakdownList');
    if (cList) {
      const cBreakdown = data.category_planned_breakdown || {};
      const cKeys = Object.keys(cBreakdown);
      if (cKeys.length === 0) {
        cList.innerHTML = `<span style="font-size:0.8rem; color:var(--cal-text-muted); font-style:italic;">No category expenses tracked.</span>`;
      } else {
        cList.innerHTML = cKeys.map(k => `
          <div style="display:flex; justify-content:space-between; font-size:0.82rem; padding:4px 0; border-bottom:1px solid var(--cal-border);">
            <span>${k}</span>
            <strong>${formatCurrency(cBreakdown[k])}</strong>
          </div>
        `).join('');
      }
    }

  } catch (err) {
    console.error('loadFutureBudgetSummary error:', err);
  }
}

// =============================================================================
// SECTION 6: REMINDERS AND NOTIFICATIONS
// =============================================================================

async function loadInAppReminders() {
  const container = document.getElementById('inAppRemindersList');
  if (!container) return;

  try {
    const res = await fetch('/api/calendar/reminders');
    if (!res.ok) throw new Error('Failed to load reminders');
    const data = await res.json();
    const reminders = data.reminders || [];

    if (reminders.length === 0) {
      container.innerHTML = `
        <div style="background:#FFFDF9; border:1px dashed var(--cal-border); border-radius:12px; padding:24px; text-align:center; color:var(--cal-text-muted);">
          <span>🔔 No pending in-app alerts at this time.</span>
        </div>
      `;
      return;
    }

    container.innerHTML = reminders.map(r => {
      const isSnoozed = r.is_currently_snoozed;
      return `
        <div style="background:#FFFDF9; border:1px solid var(--cal-border); border-radius:12px; padding:14px 18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
          <div style="display:flex; align-items:center; gap:12px;">
            <span style="font-size:1.4rem;">🔔</span>
            <div>
              <strong style="display:block; font-size:0.92rem; color:var(--cal-text);">${escapeHtml(r.title)}</strong>
              <span style="font-size:0.78rem; color:var(--cal-text-muted);">
                ${r.category} • Scheduled: ${r.next_reminder_date} ${isSnoozed ? `(Snoozed for ${r.snooze_days_remaining}d)` : ''}
              </span>
            </div>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn-outline-cal" style="font-size:0.75rem; padding:5px 10px;" onclick="snoozeReminder(${r.id}, 3)">
              💤 Snooze 3 Days
            </button>
            <button class="btn-outline-cal" style="font-size:0.75rem; padding:5px 10px; color:#DC2626; border-color:#FCA5A5;" onclick="dismissReminder(${r.id})">
              ✕ Dismiss
            </button>
          </div>
        </div>
      `;
    }).join('');

  } catch (err) {
    console.error('loadInAppReminders error:', err);
  }
}

async function snoozeReminder(id, days) {
  try {
    const res = await fetch(`/api/calendar/reminders/${id}/snooze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ days: days })
    });
    if (!res.ok) throw new Error('Snooze failed');
    notifyToast(`Alert snoozed for ${days} days.`, 'info');
    loadInAppReminders();
  } catch (err) {
    notifyToast(err.message, 'error');
  }
}

async function dismissReminder(id) {
  try {
    const res = await fetch(`/api/calendar/reminders/${id}/dismiss`, { method: 'POST' });
    if (!res.ok) throw new Error('Dismiss failed');
    notifyToast('Alert dismissed.', 'info');
    loadInAppReminders();
  } catch (err) {
    notifyToast(err.message, 'error');
  }
}

// =============================================================================
// SECTION 7: CALENDAR INSIGHTS AND HISTORY
// =============================================================================

async function loadCalendarInsights() {
  const container = document.getElementById('calendarInsightsGrid');
  if (!container) return;

  try {
    const res = await fetch('/api/calendar/analytics');
    if (!res.ok) return;
    const data = await res.json();

    container.innerHTML = `
      <div style="background:#FFFDF9; border:1px solid var(--cal-border); border-radius:12px; padding:16px; text-align:center;">
        <span style="font-size:0.75rem; font-weight:700; color:var(--cal-text-muted); text-transform:uppercase;">Plan Completion Rate</span>
        <div style="font-size:1.8rem; font-weight:800; color:#059669; margin:4px 0;">${data.completion_rate_percentage || 0}%</div>
        <span style="font-size:0.72rem; color:var(--cal-text-muted);">Completed vs total planned</span>
      </div>

      <div style="background:#FFFDF9; border:1px solid var(--cal-border); border-radius:12px; padding:16px; text-align:center;">
        <span style="font-size:0.75rem; font-weight:700; color:var(--cal-text-muted); text-transform:uppercase;">Active Plans</span>
        <div style="font-size:1.8rem; font-weight:800; color:#2563EB; margin:4px 0;">${data.active_plans || 0}</div>
        <span style="font-size:0.72rem; color:var(--cal-text-muted);">Awaiting scheduled date</span>
      </div>

      <div style="background:#FFFDF9; border:1px solid var(--cal-border); border-radius:12px; padding:16px; text-align:center;">
        <span style="font-size:0.75rem; font-weight:700; color:var(--cal-text-muted); text-transform:uppercase;">Overdue Milestones</span>
        <div style="font-size:1.8rem; font-weight:800; color:#DC2626; margin:4px 0;">${data.overdue_plans || 0}</div>
        <span style="font-size:0.72rem; color:var(--cal-text-muted);">Target date passed</span>
      </div>

      <div style="background:#FFFDF9; border:1px solid var(--cal-border); border-radius:12px; padding:16px; text-align:center;">
        <span style="font-size:0.75rem; font-weight:700; color:var(--cal-text-muted); text-transform:uppercase;">Total Tracked</span>
        <div style="font-size:1.8rem; font-weight:800; color:var(--cal-text); margin:4px 0;">${data.total_plans || 0}</div>
        <span style="font-size:0.72rem; color:var(--cal-text-muted);">Lifetime shopping plans</span>
      </div>
    `;

  } catch (err) {
    console.error('loadCalendarInsights error:', err);
  }
}

// =============================================================================
// MODAL CONTROLLERS & FORM SUBMISSIONS
// =============================================================================

function openAddEventModal() {
  const modal = document.getElementById('calendarModal');
  const titleInput = document.getElementById('calTitleInput');
  const dateInput = document.getElementById('calDateInput');
  const idInput = document.getElementById('calEventId');

  if (idInput) idInput.value = '';
  if (titleInput) titleInput.value = '';
  if (dateInput) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
  }
  if (modal) modal.style.display = 'flex';
}

function openAddEventForDate(dateStr) {
  openAddEventModal();
  const dateInput = document.getElementById('calDateInput');
  if (dateInput && dateStr) dateInput.value = dateStr;
}

function closeCalendarModal() {
  const modal = document.getElementById('calendarModal');
  if (modal) modal.style.display = 'none';
}

async function handleCalendarFormSubmit(event) {
  event.preventDefault();
  const title = document.getElementById('calTitleInput')?.value;
  const eventDate = document.getElementById('calDateInput')?.value;
  const eventType = document.getElementById('calTypeInput')?.value || 'College';
  const category = document.getElementById('calCategoryInput')?.value || 'All';
  const budget = parseFloat(document.getElementById('calBudgetInput')?.value || 3000);
  const notes = document.getElementById('calNotesInput')?.value || '';
  const eventId = document.getElementById('calEventId')?.value;

  try {
    let res;
    if (eventId) {
      res = await fetch(`/api/calendar/events/${eventId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, event_date: eventDate, event_type: eventType, category, budget, notes })
      });
    } else {
      res = await fetch('/api/calendar/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, event_date: eventDate, event_type: eventType, category, budget, notes })
      });
    }

    if (!res.ok) throw new Error('Failed to save milestone');
    closeCalendarModal();
    notifyToast('Milestone saved to calendar!', 'success');
    await loadCalendarView();
    await loadFutureBudgetSummary();
  } catch (err) {
    notifyToast(err.message, 'error');
  }
}

// Plan Modal
function openCreatePlanModal() {
  const modal = document.getElementById('planModal');
  const dateInput = document.getElementById('planDateInput');
  if (dateInput) dateInput.value = new Date().toISOString().split('T')[0];
  if (modal) modal.style.display = 'flex';
}

function closePlanModal() {
  const modal = document.getElementById('planModal');
  if (modal) modal.style.display = 'none';
}

async function handleCreatePlanSubmit(event) {
  event.preventDefault();
  const title = document.getElementById('planTitleInput')?.value;
  const targetDate = document.getElementById('planDateInput')?.value;
  const category = document.getElementById('planCategoryInput')?.value || 'All';
  const budget = parseFloat(document.getElementById('planBudgetInput')?.value || 2500);
  const priority = document.getElementById('planPriorityInput')?.value || 'Medium';
  const notes = document.getElementById('planNotesInput')?.value || '';

  try {
    const res = await fetch('/api/calendar/plans', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, target_date: targetDate, category, estimated_budget: budget, priority, notes })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'Failed to create plan');
    }
    closePlanModal();
    notifyToast('Shopping plan created!', 'success');
    await loadShoppingPlans('active');
    await loadCalendarView();
    await loadFutureBudgetSummary();
    await loadCalendarInsights();
  } catch (err) {
    notifyToast(err.message, 'error');
  }
}

// Occasion Modal
function openCreateOccasionModal() {
  const modal = document.getElementById('occasionModal');
  const dateInput = document.getElementById('occDateInput');
  if (dateInput) dateInput.value = new Date().toISOString().split('T')[0];
  if (modal) modal.style.display = 'flex';
}

function closeOccasionModal() {
  const modal = document.getElementById('occasionModal');
  if (modal) modal.style.display = 'none';
}

async function handleCreateOccasionSubmit(event) {
  event.preventDefault();
  const name = document.getElementById('occNameInput')?.value;
  const date = document.getElementById('occDateInput')?.value;
  const type = document.getElementById('occTypeInput')?.value || 'Custom';
  const budget = parseFloat(document.getElementById('occBudgetInput')?.value || 5000);
  const notes = document.getElementById('occNotesInput')?.value || '';

  try {
    const res = await fetch('/api/calendar/occasions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_name: name, event_date: date, occasion_type: type, estimated_budget: budget, shopping_requirements: notes })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'Failed to save occasion');
    }
    closeOccasionModal();
    notifyToast('Occasion added to calendar!', 'success');
    await loadOccasions();
    await loadCalendarView();
    await loadFutureBudgetSummary();
  } catch (err) {
    notifyToast(err.message, 'error');
  }
}
