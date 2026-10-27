/**
 * PreTwinShop AI - Settings & Governance Controller
 */

async function loadSettings() {
  try {
    const data = await apiGet('/api/profile');
    const prefs = data.preferences || {};

    const minEl = document.getElementById('settingsBudgetMin');
    const maxEl = document.getElementById('settingsBudgetMax');

    if (minEl && prefs.budget_min !== undefined) minEl.value = prefs.budget_min;
    if (maxEl && prefs.budget_max !== undefined) maxEl.value = prefs.budget_max;
  } catch (err) {
    console.error('Failed to load settings:', err);
  }
}

function savePrivacyPreference() {
  const isPredictive = document.getElementById('togglePredictive')?.checked;
  const isAudit = document.getElementById('toggleAuditLogs')?.checked;

  localStorage.setItem('pretwinshop_privacy', JSON.stringify({
    predictive: isPredictive,
    auditLogs: isAudit,
  }));

  showToast('Privacy preferences updated successfully', 'success');
}

async function updateSettingsBudget() {
  const bMin = parseFloat(document.getElementById('settingsBudgetMin').value) || 0;
  const bMax = parseFloat(document.getElementById('settingsBudgetMax').value) || 0;

  if (bMax < bMin) {
    showToast('Maximum budget ceiling cannot be less than minimum budget', 'error');
    return;
  }

  try {
    await apiPut('/api/profile', {
      budget_min: bMin,
      budget_max: bMax,
    });
    showToast('Budget bounds updated successfully!', 'success');

    const topbarVal = document.getElementById('topbarBudgetValue');
    if (topbarVal) topbarVal.textContent = formatCurrency(bMax);
  } catch (err) {
    showToast(`Failed to update budget: ${err.message}`, 'error');
  }
}

async function exportUserData() {
  showToast('Exporting your Shopping Twin data...', 'info');

  try {
    const [profile, history, predictions, recs] = await Promise.all([
      apiGet('/api/profile'),
      apiGet('/api/purchase-history'),
      apiGet('/api/predictions'),
      apiGet('/api/recommendations'),
    ]);

    const exportData = {
      app: 'PreTwinShop AI',
      exported_at: new Date().toISOString(),
      twin_profile: profile,
      purchase_history: history,
      predictions: predictions,
      recommendations: recs,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pretwinshop_twin_export_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast('Twin data exported successfully!', 'success');
  } catch (err) {
    showToast(`Export failed: ${err.message}`, 'error');
  }
}

function confirmResetDemoProfile() {
  const bodyHtml = `
    <div class="confirm-reset-dialog">
      <p class="text-danger font-weight-bold">Are you sure you want to reset the demonstration profile?</p>
      <p class="text-muted text-sm">
        This action will wipe all recent prediction runs, smart recommendations, custom purchase items, and reset the profile back to Alex Johnson's initial 10 demo purchases.
      </p>
    </div>
  `;

  const footerHtml = `
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-danger" onclick="executeResetDemoProfile()">Yes, Reset Everything</button>
  `;

  openModal('Confirm Demo Reset', bodyHtml, footerHtml);
}

async function executeResetDemoProfile() {
  closeModal();
  showToast('Resetting demo profile and reseeding catalogue...', 'info');

  try {
    await apiDelete('/api/profile');
    localStorage.removeItem('pretwinshop_comparison_ids');
    showToast('Demo profile restored to original initial state!', 'success');
    setTimeout(() => {
      window.location.href = '/';
    }, 1000);
  } catch (err) {
    showToast(`Reset failed: ${err.message}`, 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
});
