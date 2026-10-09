let total = 0;
let busy = false;

function el(id) {
  return document.getElementById(id);
}

async function refresh() {
  const data = await (await fetch("/status")).json();
  const added = data.counts.added || 0;
  const notFound = data.counts.not_found || 0;
  const pending = (data.counts.pending || 0) + (data.counts.matched || 0);
  total = added + notFound + pending;

  let percent = 0;
  if (total > 0) {
    percent = Math.floor(((added + notFound) / total) * 100);
  }

  el("added").textContent = added;
  el("not_found").textContent = notFound;
  el("pending").textContent = pending;
  el("bar").style.width = percent + "%";
  el("bar").classList.toggle("moving", data.running);
  el("percent").textContent = percent + "% of " + total + " tracks";
  el("error").textContent = data.error ? "Error: " + data.error : "";

  if (!busy) {
    if (!data.logged_in) {
      el("state").textContent = "Not logged in to Spotify";
    } else if (data.running) {
      el("state").textContent = "Copying tracks...";
    } else if (total > 0 && pending === 0) {
      el("state").textContent = "Done";
    } else {
      el("state").textContent = "Ready";
    }
  }

  const locked = busy || data.running || !data.logged_in;
  el("start").disabled = locked;
  el("resume").disabled = locked;
  el("sync").disabled = locked;
}

async function post(url, message) {
  busy = true;
  el("state").textContent = message;
  el("start").disabled = true;
  el("resume").disabled = true;
  el("sync").disabled = true;
  try {
    await fetch(url, { method: "POST" });
  } finally {
    busy = false;
    refresh();
  }
}

el("start").onclick = () => {
  if (total === 0) {
    post("/sync", "Fetching liked songs from Spotify...");
  } else {
    post("/start", "Starting...");
  }
};
el("resume").onclick = () => post("/start", "Resuming...");
el("sync").onclick = () => post("/sync", "Fetching liked songs from Spotify...");

setInterval(refresh, 2000);
refresh();
