let previousProduct = null;

// ========================================
// GET ELEMENTS
// ========================================

const chatBox = document.getElementById("chat-box");
const userInput = document.getElementById("user-input");
const sendButton = document.getElementById("send-button");
const typing = document.getElementById("typing");

// ========================================
// ADD MESSAGE
// ========================================

function addMessage(message, sender, intent = null) {
  const messageDiv = document.createElement("div");

  if (sender === "user") {
    messageDiv.className = "message user-message";

    messageDiv.innerHTML = `
            <div class="message-content">
                <div class="sender">You</div>

                <div class="text">
                    ${formatMessage(message)}
                </div>
            </div>

            <div class="avatar">◉</div>
        `;
  } else {
    messageDiv.className = "message bot-message";

    let intentHTML = "";

    if (intent) {
      intentHTML = `
                <div class="intent">
                    ${intent}
                </div>
            `;
    }

    messageDiv.innerHTML = `
            <div class="avatar">✦</div>

            <div class="message-content">

                <div class="sender">
                    ShopIQ
                </div>

                ${intentHTML}

                <div class="text">
                    ${formatMessage(message)}
                </div>

            </div>
        `;
  }

  chatBox.appendChild(messageDiv);

  chatBox.scrollTop = chatBox.scrollHeight;
}

// ========================================
// FORMAT MESSAGE
// ========================================

function formatMessage(message) {
  if (!message) {
    return "";
  }

  return message
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/###\s?(.*?)(?=\n|$)/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

// ========================================
// QUICK SUGGESTION
// ========================================

function useSuggestion(message) {
  userInput.value = message;

  sendMessage();
}

// ========================================
// SEND MESSAGE
// ========================================

async function sendMessage() {
  const message = userInput.value.trim();

  if (!message) {
    return;
  }

  // Show user message
  addMessage(message, "user");

  // Clear input
  userInput.value = "";

  // Reset textarea height
  userInput.style.height = "auto";

  // Disable send button
  sendButton.disabled = true;

  // Show typing indicator
  typing.classList.remove("hidden");

  try {
    const response = await fetch("/chat", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        message: message,

        previous_product: previousProduct,
      }),
    });

    const data = await response.json();

    // Hide typing
    typing.classList.add("hidden");

    // Enable button
    sendButton.disabled = false;

    if (data.success) {
      // Remember product for follow-up questions
      if (data.previous_product) {
        previousProduct = data.previous_product;
      }

      // Display assistant response
      addMessage(data.response, "bot", data.intent);
    } else {
      addMessage(data.message || "Something went wrong.", "bot");
    }
  } catch (error) {
    typing.classList.add("hidden");

    sendButton.disabled = false;

    addMessage(
      "I couldn't connect to the server. Please make sure the ShopIQ server is running.",
      "bot",
    );

    console.error("Chat error:", error);
  }
}

// ========================================
// SEND BUTTON
// ========================================

sendButton.addEventListener("click", sendMessage);

// ========================================
// ENTER KEY
// ========================================

userInput.addEventListener("keydown", function (event) {
  // Enter sends message
  // Shift + Enter creates a new line

  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();

    sendMessage();
  }
});

// ========================================
// AUTO RESIZE TEXTAREA
// ========================================

userInput.addEventListener("input", function () {
  this.style.height = "auto";

  this.style.height = Math.min(this.scrollHeight, 100) + "px";
});

// ========================================
// INITIAL FOCUS
// ========================================

window.addEventListener("load", function () {
  userInput.focus();
});
