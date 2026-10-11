"use client";

import { useEffect, useState } from "react";

type Conversation = {
  id: string;
  participant_label: string;
  unread_count: number;
  last_message_preview: string | null;
};

type Detail = Conversation & {
  messages: Array<{
    id: string;
    sender_is_current: boolean;
    body: string;
    created_at: string;
  }>;
  contacts: Array<{
    id: string;
    is_current: boolean;
    contact_type: string;
    contact_value: string;
  }>;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function InternalChat({ token }: { token: string }) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [draft, setDraft] = useState("");
  const [contact, setContact] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadConversations() {
    try {
      const response = await fetch(`${apiUrl}/api/v1/chat/conversations`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("chat_unavailable");
      const value = (await response.json()) as Conversation[];
      setConversations(value);
      setSelectedId((current) => current && value.some((item) => item.id === current) ? current : value[0]?.id ?? null);
      setState("ready");
    } catch {
      setState("error");
    }
  }

  async function loadDetail(id: string) {
    const response = await fetch(`${apiUrl}/api/v1/chat/conversations/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error("chat_history_unavailable");
    const value = (await response.json()) as Detail;
    setDetail(value);
    if (value.unread_count > 0) {
      await fetch(`${apiUrl}/api/v1/chat/conversations/${id}/read`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      setConversations((items) => items.map((item) => item.id === id ? { ...item, unread_count: 0 } : item));
    }
  }

  useEffect(() => {
    void loadConversations();
  }, [token]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    void loadDetail(selectedId).catch(() => setMessage("Не удалось загрузить историю разговора."));
  }, [selectedId, token]);

  async function sendMessage() {
    if (!selectedId || !draft.trim()) return;
    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/chat/conversations/${selectedId}/messages`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ body: draft }),
      });
      if (!response.ok) throw new Error("message_failed");
      setDraft("");
      await loadDetail(selectedId);
      await loadConversations();
    } catch {
      setMessage("Сообщение не отправлено. Попробуй ещё раз.");
    } finally {
      setBusy(false);
    }
  }

  async function shareContact() {
    if (!selectedId || !contact.trim()) return;
    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/chat/conversations/${selectedId}/contacts`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ contact_type: "other", contact_value: contact }),
      });
      if (!response.ok) throw new Error("contact_failed");
      setContact("");
      await loadDetail(selectedId);
      setMessage("Контакт доступен участникам этого match.");
    } catch {
      setMessage("Не удалось обменяться контактом.");
    } finally {
      setBusy(false);
    }
  }

  async function report() {
    if (!selectedId) return;
    setBusy(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/chat/conversations/${selectedId}/reports`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "other" }),
      });
      if (!response.ok) throw new Error("report_failed");
      setMessage("Жалоба зарегистрирована для проверки.");
    } catch {
      setMessage("Не удалось зарегистрировать жалобу.");
    } finally {
      setBusy(false);
    }
  }

  if (state === "loading") return <section className="chatPanel muted">Проверяем доступ к внутренним разговорам…</section>;
  if (state === "error") return <section className="chatPanel error">Не удалось загрузить внутренние разговоры.</section>;

  return (
    <section className="chatPanel" aria-labelledby="internal-chat-title">
      <div className="chatHeading">
        <div><span className="authLabel">ОБЩЕНИЕ ПОСЛЕ СОГЛАСИЯ</span><h2 id="internal-chat-title">Чат и контакты</h2><p>Общение и обмен контактами открываются после принятия предложения.</p></div>
        <span className="profileStatus">{conversations.reduce((total, item) => total + item.unread_count, 0)} UNREAD</span>
      </div>
      {message && <p className="chatMessage" aria-live="polite">{message}</p>}
      {conversations.length === 0 ? (
        <div className="chatEmpty"><strong>Активных match пока нет</strong><span>После принятия приглашения здесь появится защищённый разговор с участником.</span></div>
      ) : (
        <div className="chatLayout">
          <div className="chatConversations">
            {conversations.map((item) => <button className={`chatConversation ${item.id === selectedId ? "selected" : ""}`} key={item.id} onClick={() => setSelectedId(item.id)}><strong>{item.participant_label}</strong><small>{item.last_message_preview ?? "Новый разговор"}</small>{item.unread_count > 0 && <b>{item.unread_count}</b>}</button>)}
          </div>
          {detail && <div className="chatThread">
            <div className="chatThreadTop"><strong>{detail.participant_label}</strong><button className="textButton" disabled={busy} onClick={() => void report()}>Пожаловаться</button></div>
            <div className="chatMessages" aria-live="polite">{detail.messages.length === 0 ? <span className="chatNoMessages">Начните разговор после match.</span> : detail.messages.map((item) => <div className={`chatBubble ${item.sender_is_current ? "mine" : "theirs"}`} key={item.id}>{item.body}</div>)}</div>
            {detail.contacts.length > 0 && <div className="chatContacts"><span>ОБМЕН КОНТАКТАМИ</span>{detail.contacts.map((item) => <small key={item.id}>{item.contact_value}</small>)}</div>}
            <div className="chatComposer"><textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Написать сообщение…" maxLength={4000} /><button className="authButton primaryButton" disabled={busy || !draft.trim()} onClick={() => void sendMessage()}>Отправить</button></div>
            <div className="chatContactForm"><input value={contact} onChange={(event) => setContact(event.target.value)} placeholder="Контакт для обмена" maxLength={160} /><button className="authButton secondaryButton" disabled={busy || !contact.trim()} onClick={() => void shareContact()}>Поделиться контактом</button></div>
          </div>}
        </div>
      )}
    </section>
  );
}
