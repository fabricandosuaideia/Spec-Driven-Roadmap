import { useState } from "react";

export default function ItemForm({ agendaId, onCreated }) {
  const [title, setTitle] = useState("");
  const [minutes, setMinutes] = useState(10);
  async function submit(e) {
    e.preventDefault();
    await fetch("/items/", { method: "POST", body: JSON.stringify({ agendaId, title, minutes }) });
    onCreated();
  }
  return (
    <form onSubmit={submit}>
      <input value={title} onChange={e => setTitle(e.target.value)} />
      <input type="number" value={minutes} onChange={e => setMinutes(+e.target.value)} />
      <button>Propor</button>
    </form>
  );
}
