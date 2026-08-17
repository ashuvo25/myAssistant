# Portfolio Chatbot API Integration Guide

This guide explains how to connect your **AI Portfolio Assistant API** (FastAPI) to your portfolio website (React, Next.js, or plain HTML/JS).

---

## 1. API Endpoint Overview

### **Base URL**
- **Local Development**: `http://localhost:8000`
- **Render Production**: `https://your-app-name.onrender.com` (replace with your Render URL)

### **Chat Endpoint**
- **URL**: `POST /chat`
- **Headers**: `Content-Type: application/json`

---

## 2. Request & Response Payload

### **Request Body**
```json
{
  "message": "What research papers has Shuvo published?"
}
```

### **Response Body**
```json
{
  "answer": "Shuvo has published 2 papers and has 3 papers under review...",
  "route": "hybrid",
  "sources": ["chroma", "google"],
  "reason": "Query requires information from multiple portfolio/live data sources."
}
```

---

## 3. Quick Local Testing (cURL & JavaScript)

### **cURL Test**
```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Tell me about Shuvo"}'
```

### **JavaScript Fetch Example**
```javascript
async function askChatbot(question) {
  const response = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ message: question })
  });

  const data = await response.json();
  console.log("Chatbot Answer:", data.answer);
  return data.answer;
}

// Example usage:
askChatbot("What projects has Shuvo built?");
```

---

## 4. Copy-Paste Floating Chatbot Widget for HTML/JS Website

Add this snippet before the `</body>` tag of your portfolio website `index.html`:

```html
<!-- Floating AI Chatbot Widget -->
<style>
  #ai-chat-button {
    position: fixed;
    bottom: 25px;
    right: 25px;
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 50px;
    padding: 14px 22px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
    z-index: 9999;
    transition: transform 0.2s ease;
  }
  #ai-chat-button:hover { transform: scale(1.05); }

  #ai-chat-box {
    position: fixed;
    bottom: 90px;
    right: 25px;
    width: 360px;
    height: 480px;
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.15);
    display: none;
    flex-direction: column;
    z-index: 9999;
    overflow: hidden;
    font-family: system-ui, -apple-system, sans-serif;
  }

  .chat-header {
    background: #2563eb;
    color: white;
    padding: 16px;
    font-weight: bold;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .chat-messages {
    flex: 1;
    padding: 16px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
    background: #f8fafc;
  }

  .message {
    padding: 10px 14px;
    border-radius: 12px;
    max-width: 80%;
    font-size: 14px;
    line-height: 1.4;
  }
  .message.user { background: #2563eb; color: white; align-self: flex-end; }
  .message.bot { background: #e2e8f0; color: #1e293b; align-self: flex-start; }

  .chat-input-area {
    display: flex;
    padding: 12px;
    border-top: 1px solid #e2e8f0;
    background: white;
  }
  .chat-input-area input {
    flex: 1;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    outline: none;
  }
  .chat-input-area button {
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 8px;
    margin-left: 8px;
    padding: 8px 14px;
    cursor: pointer;
  }
</style>

<button id="ai-chat-button" onclick="toggleChat()">💬 Ask Shuvo AI</button>

<div id="ai-chat-box">
  <div class="chat-header">
    <span>Shuvo Portfolio AI</span>
    <button onclick="toggleChat()" style="background:none;border:none;color:white;cursor:pointer;font-size:18px;">✕</button>
  </div>
  <div class="chat-messages" id="chat-messages">
    <div class="message bot">Hello! I'm Shuvo's AI Assistant. Ask me about his projects, papers, skills, or updates!</div>
  </div>
  <div class="chat-input-area">
    <input type="text" id="chat-input" placeholder="Type a question..." onkeydown="if(event.key==='Enter') sendMessage()" />
    <button onclick="sendMessage()">Send</button>
  </div>
</div>

<script>
  const API_URL = "http://localhost:8000/chat"; // Change to your Render URL after deployment

  function toggleChat() {
    const box = document.getElementById("ai-chat-box");
    box.style.display = box.style.display === "flex" ? "none" : "flex";
  }

  async function sendMessage() {
    const input = document.getElementById("chat-input");
    const messages = document.getElementById("chat-messages");
    const text = input.value.trim();
    if (!text) return;

    // Append User Message
    messages.innerHTML += `<div class="message user">${text}</div>`;
    input.value = "";
    messages.scrollTop = messages.scrollHeight;

    // Append Loading Indicator
    const loadingId = "loading-" + Date.now();
    messages.innerHTML += `<div class="message bot" id="${loadingId}">Thinking...</div>`;
    messages.scrollTop = messages.scrollHeight;

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
      });
      const data = await response.json();
      document.getElementById(loadingId).innerText = data.answer;
    } catch (err) {
      document.getElementById(loadingId).innerText = "Sorry, failed to connect to AI server.";
    }
    messages.scrollTop = messages.scrollHeight;
  }
</script>
```

---

## 5. React / Next.js Hook Integration

If your portfolio is built in **React** or **Next.js**:

```tsx
import { useState } from "react";

const API_URL = "https://your-app-name.onrender.com/chat"; // Replace with your backend URL

export function usePortfolioChat() {
  const [messages, setMessages] = useState<Array<{ sender: "user" | "bot"; text: string }>>([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async (question: string) => {
    if (!question.trim()) return;

    setMessages((prev) => [...prev, { sender: "user", text: question }]);
    setLoading(true);

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { sender: "bot", text: data.answer }]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "Unable to connect to assistant." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return { messages, sendMessage, loading };
}
```

---

## 6. Configuring CORS for Your Domain

In `app/main.py`, update `ALLOWED_ORIGINS` in your `.env` file to allow your website domain:

```env
ALLOWED_ORIGINS=http://localhost:3000,https://ashuvo25.github.io,https://your-custom-domain.com
```

This ensures your frontend website can securely make fetch requests to your FastAPI backend.
