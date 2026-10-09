"use client";
import { useState } from "react";

export const shortcuts = ["Get me the Keychron B40", "Buy the black PowerBug 25W, under $60", "Show me today's deal"];
export type Message = { role: "Ana" | "Agent"; text: string };

export function ChatPanel({ messages, busy, enabled, onSend }: { messages: Message[]; busy: boolean; enabled: boolean; onSend: (message: string) => Promise<void> }) {
  const [text, setText] = useState("");
  return <section className="chat-block" aria-labelledby="chat-heading"><h3 id="chat-heading">Ask your agent</h3>
    <div className="shortcuts">{shortcuts.map((prompt, i) => <button className="secondary small" key={prompt} disabled={!enabled || busy} onClick={() => void onSend(prompt)}>{["Buy Keychron", "Buy black PowerBug", "Today’s deal"][i]}</button>)}</div>
    <div className="messages" role="log" aria-label="Chat messages">
      {!messages.length && <p className="muted small">Choose a shortcut or ask for an item. You review every request before submitting it.</p>}
      {messages.map((message, i) => <div className={`message ${message.role === "Ana" ? "from-ana" : ""}`} key={i}><strong>{message.role}</strong><p>{message.text}</p></div>)}
      {busy && <p className="small muted" role="status">Preparing your request…</p>}
    </div>
    <form className="chat-input" onSubmit={e => { e.preventDefault(); if (text.trim()) { void onSend(text.trim()); setText(""); } }}>
      <label className="grow">Message<input value={text} maxLength={2000} onChange={e => setText(e.target.value)} placeholder="What would you like to buy?" required /></label>
      <button disabled={!enabled || busy || !text.trim()}>Send</button>
    </form>
  </section>;
}
