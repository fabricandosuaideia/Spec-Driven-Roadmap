import { useEffect, useState } from "react";

export default function AgendaList({ teamId }) {
  const [agendas, setAgendas] = useState([]);
  useEffect(() => {
    fetch(`/agendas/${teamId}`).then(r => r.json()).then(setAgendas);
  }, [teamId]);
  return <ul>{agendas.map(a => <li key={a.id}>{a.title}</li>)}</ul>;
}
