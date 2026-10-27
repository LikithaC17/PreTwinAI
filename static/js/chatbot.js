/**
 * PreTwin AI Shopping Assistant – Frontend Chatbot Controller
 * Handles interactive floating assistant, speech recognition (Web Speech API),
 * voice shopping queries, product cards rendering, and quick query pills.
 */

let pretwinChatSessionId = sessionStorage.getItem("pretwin_chat_session_id");
if (!pretwinChatSessionId) {
  pretwinChatSessionId = "session_" + Math.random().toString(36).substring(2, 12);
  sessionStorage.setItem("pretwin_chat_session_id", pretwinChatSessionId);
}

function toggleChatbot() {
  const panel = document.getElementById("pretwinChatPanel");
  if (!panel) return;
  
  const isHidden = panel.style.display === "none" || !panel.style.display;
  panel.style.display = isHidden ? "flex" : "none";
  
  if (isHidden) {
    const input = document.getElementById("pretwinChatInput");
    if (input) input.focus();
    scrollChatToBottom();
  }
}

function scrollChatToBottom() {
  const body = document.getElementById("pretwinChatBody");
  if (body) {
    body.scrollTop = body.scrollHeight;
  }
}

function sendChatPrompt(promptText) {
  const input = document.getElementById("pretwinChatInput");
  if (input) {
    input.value = promptText;
    const form = document.querySelector(".pretwin-chat-input-form");
    if (form) {
      handleChatSubmit(new Event("submit"));
    }
  }
}

async function handleChatSubmit(event) {
  if (event) event.preventDefault();
  
  const input = document.getElementById("pretwinChatInput");
  if (!input) return;
  
  const rawMsg = input.value.trim();
  if (!rawMsg) return;
  
  // Clear input
  input.value = "";
  
  // Append user message
  appendUserMessage(rawMsg);
  
  // Show typing indicator
  const typingId = showTypingIndicator();
  scrollChatToBottom();
  
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: rawMsg,
        session_id: pretwinChatSessionId
      })
    });
    
    removeTypingIndicator(typingId);
    
    if (!res.ok) {
      appendAssistantMessage("I apologize, but I am momentarily recalibrating my prediction engine. Please try asking again in a moment.");
      return;
    }
    
    const data = await res.json();
    appendAssistantMessage(data.reply || "How else can I assist your shopping journey today?", data.products, data.actions, data.suggestions);
  } catch (err) {
    console.error("Chat error:", err);
    removeTypingIndicator(typingId);
    appendAssistantMessage("I had trouble reaching the PreTwin AI server. You can still browse products under the Category bar or view predictions at /predictions.");
  }
  
  scrollChatToBottom();
}

function appendUserMessage(text) {
  const body = document.getElementById("pretwinChatBody");
  if (!body) return;
  
  const msgEl = document.createElement("div");
  msgEl.className = "pretwin-chat-msg user";
  msgEl.innerHTML = `
    <div class="pretwin-msg-content">${escapeHtml(text)}</div>
  `;
  body.appendChild(msgEl);
}

function appendAssistantMessage(replyText, products = [], actions = [], suggestions = []) {
  const body = document.getElementById("pretwinChatBody");
  if (!body) return;
  
  const msgEl = document.createElement("div");
  msgEl.className = "pretwin-chat-msg assistant";
  
  let productsHtml = "";
  if (products && products.length > 0) {
    productsHtml = `
      <div class="pretwin-chat-products-grid">
        ${products.slice(0, 4).map(p => `
          <div class="pretwin-chat-product-card">
            <img src="${p.image_url || '/static/images/placeholder.jpg'}" alt="${escapeHtml(p.name)}" class="pretwin-chat-p-img" onerror="this.src='/static/images/placeholder.jpg'">
            <div class="pretwin-chat-p-info">
              <div class="pretwin-chat-p-name" title="${escapeHtml(p.name)}">${escapeHtml(p.name)}</div>
              <div class="pretwin-chat-p-price">₹${Number(p.price || 0).toLocaleString('en-IN')}</div>
              <button class="pretwin-chat-p-btn" onclick="addChatProductToCart(${p.id}, '${escapeHtml(p.name).replace(/'/g, "\\'")}', ${p.price}, '${p.image_url || ''}')">+ Add to Cart</button>
            </div>
          </div>
        `).join("")}
      </div>
    `;
  }
  
  let actionsHtml = "";
  if (actions && actions.length > 0) {
    actionsHtml = `
      <div class="pretwin-chat-actions">
        ${actions.map(act => `
          <a href="${act.url}" class="pretwin-chat-action-btn">${escapeHtml(act.title)} ➔</a>
        `).join("")}
      </div>
    `;
  }
  
  let formattedReply = replyText.replace(/\n/g, "<br>");
  const cleanReplyJson = JSON.stringify(replyText);

  msgEl.innerHTML = `
    <div class="pretwin-msg-avatar">🧚</div>
    <div class="pretwin-msg-content">
      ${formattedReply}
      ${productsHtml}
      ${actionsHtml}
      <div>
        <button type="button" class="pretwin-chat-tts-btn" onclick='toggleSpeakAssistantMessage(this, ${cleanReplyJson})' title="Read message aloud">
          <span>🔊</span>
          <span>Read Aloud</span>
        </button>
      </div>
    </div>
  `;
  body.appendChild(msgEl);
  scrollChatToBottom();
}

function showTypingIndicator() {
  const body = document.getElementById("pretwinChatBody");
  if (!body) return null;
  
  const id = "typing_" + Date.now();
  const el = document.createElement("div");
  el.id = id;
  el.className = "pretwin-chat-msg assistant typing-indicator";
  el.innerHTML = `
    <div class="pretwin-msg-avatar">🧚</div>
    <div class="pretwin-msg-content typing-dots">
      <span></span><span></span><span></span>
    </div>
  `;
  body.appendChild(el);
  return id;
}

function removeTypingIndicator(id) {
  if (!id) return;
  const el = document.getElementById(id);
  if (el) el.remove();
}

async function resetChatbotSession() {
  try {
    await fetch("/api/chat/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: pretwinChatSessionId })
    });
  } catch (e) {
    console.warn("Reset error:", e);
  }
  
  const body = document.getElementById("pretwinChatBody");
  if (body) {
    body.innerHTML = `
      <div class="pretwin-chat-msg assistant">
        <div class="pretwin-msg-avatar">🧚</div>
        <div class="pretwin-msg-content">
          Chat cleared. Hello! I am your <strong>PreTwin AI Shopping Assistant</strong>. ✨
          <br><br>
          How can I assist your shopping today?
        </div>
      </div>
    `;
  }
}

function addChatProductToCart(id, name, price, imageUrl) {
  if (typeof addToCart === "function") {
    addToCart(id, name, price, imageUrl);
  } else if (typeof window.cartModule !== "undefined" && window.cartModule.addItem) {
    window.cartModule.addItem(id, 1);
  } else {
    let cart = [];
    try {
      cart = JSON.parse(localStorage.getItem("pretwin_cart") || "[]");
    } catch (e) { cart = []; }
    const existing = cart.find(x => x.product_id === id);
    if (existing) {
      existing.quantity += 1;
    } else {
      cart.push({ product_id: id, id: id, name: name, price: price, image_url: imageUrl, quantity: 1 });
    }
    localStorage.setItem("pretwin_cart", JSON.stringify(cart));
    if (typeof showToast === "function") {
      showToast(`Added ${name} to cart!`, "success");
    } else {
      alert(`Added ${name} to cart!`);
    }
  }
}

// ---------------------------------------------------------------------------
// Speech Recognition & Voice Shopping Assistant (Web Speech API)
// ---------------------------------------------------------------------------
let speechRecognizer = null;
let isVoiceListening = false;
let currentUtterance = null;

function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return null;

  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = "en-IN";

  recognition.onstart = () => {
    isVoiceListening = true;
    updateVoiceUI(true, "Listening... Speak your shopping request");
  };

  recognition.onresult = (event) => {
    let interimTranscript = "";
    let finalTranscript = "";

    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        finalTranscript += event.results[i][0].transcript;
      } else {
        interimTranscript += event.results[i][0].transcript;
      }
    }

    const input = document.getElementById("pretwinChatInput");
    if (input) {
      input.value = finalTranscript || interimTranscript;
    }
  };

  recognition.onerror = (event) => {
    console.warn("Speech recognition error:", event.error);
    isVoiceListening = false;
    let errHint = "Microphone error. You can type your request.";
    if (event.error === "not-allowed" || event.error === "permission-denied") {
      errHint = "Microphone access was denied. Please allow microphone permission in your browser.";
    } else if (event.error === "no-speech") {
      errHint = "No speech detected. Click the mic button to speak again.";
    }
    updateVoiceUI(false, errHint);
    if (typeof showToast === "function") {
      showToast(errHint, "info");
    }
  };

  recognition.onend = () => {
    isVoiceListening = false;
    updateVoiceUI(false);
    const input = document.getElementById("pretwinChatInput");
    if (input && input.value.trim().length > 0) {
      setTimeout(() => {
        handleChatSubmit(new Event("submit"));
      }, 350);
    }
  };

  return recognition;
}

function toggleVoiceInput() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert("Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari, or type your query in the chat box.");
    return;
  }

  if (isVoiceListening) {
    stopVoiceRecognition();
    return;
  }

  // Ensure chatbot panel is visible
  const panel = document.getElementById("pretwinChatPanel");
  if (panel && (panel.style.display === "none" || !panel.style.display)) {
    toggleChatbot();
  }

  if (!speechRecognizer) {
    speechRecognizer = initSpeechRecognition();
  }

  if (speechRecognizer) {
    try {
      speechRecognizer.start();
    } catch (e) {
      console.warn("Speech start retry:", e);
      speechRecognizer = initSpeechRecognition();
      speechRecognizer.start();
    }
  }
}

function stopVoiceRecognition() {
  if (speechRecognizer && isVoiceListening) {
    try {
      speechRecognizer.stop();
    } catch (e) {}
  }
  isVoiceListening = false;
  updateVoiceUI(false);
}

function updateVoiceUI(listening, statusText = "") {
  const bar = document.getElementById("pretwinVoiceStatusBar");
  const micBtn = document.getElementById("pretwinChatMicBtn");
  const textEl = document.getElementById("pretwinVoiceStatusText");

  if (listening) {
    if (bar) bar.style.display = "flex";
    if (micBtn) micBtn.classList.add("listening");
    if (textEl && statusText) textEl.textContent = statusText;
  } else {
    if (bar) bar.style.display = "none";
    if (micBtn) micBtn.classList.remove("listening");
  }
}

// ---------------------------------------------------------------------------
// Text-to-Speech (Read Aloud Assistant Responses)
// ---------------------------------------------------------------------------
function toggleSpeakAssistantMessage(btn, text) {
  if (!('speechSynthesis' in window)) {
    alert("Speech synthesis is not supported on this browser.");
    return;
  }

  if (window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
    resetAllTtsButtons();
    return;
  }

  // Clean formatted Markdown & HTML tags
  const cleanText = text
    .replace(/<[^>]*>/g, "")
    .replace(/[*_#`~[\]()]/g, "")
    .replace(/₹/g, " rupees ");

  currentUtterance = new SpeechSynthesisUtterance(cleanText);
  currentUtterance.rate = 1.0;
  currentUtterance.pitch = 1.05;

  currentUtterance.onstart = () => {
    btn.innerHTML = `<span>⏹</span><span>Stop</span>`;
    btn.style.color = "#ef4444";
    btn.style.borderColor = "#fca5a5";
  };

  currentUtterance.onend = () => {
    resetAllTtsButtons();
  };

  currentUtterance.onerror = () => {
    resetAllTtsButtons();
  };

  window.speechSynthesis.speak(currentUtterance);
}

function resetAllTtsButtons() {
  document.querySelectorAll(".pretwin-chat-tts-btn").forEach(b => {
    b.innerHTML = `<span>🔊</span><span>Read Aloud</span>`;
    b.style.color = "#7c3aed";
    b.style.borderColor = "#e9d5ff";
  });
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