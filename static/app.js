const MUSIC_VIDEO_ID = "b12dBv7EDjU";

let total = 0;
let busy = false;
let wasRunning = false;
let muted = localStorage.getItem("muted") === "1";
let player = null;
let playerReady = false;
let clicked = false;
let audioContext = null;

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

  if (wasRunning && !data.running && data.error) {
    playErrorSound();
  }
  wasRunning = data.running;

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

function playPop() {
  if (muted) {
    return;
  }
  if (!audioContext) {
    audioContext = new AudioContext();
  }
  const now = audioContext.currentTime;
  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();
  oscillator.frequency.setValueAtTime(300, now);
  oscillator.frequency.exponentialRampToValueAtTime(1500, now + 0.07);
  gain.gain.setValueAtTime(0.35, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.11);
  oscillator.connect(gain);
  gain.connect(audioContext.destination);
  oscillator.start(now);
  oscillator.stop(now + 0.12);
}

function playErrorSound() {
  if (muted) {
    return;
  }
  new Audio("/sounds/error").play().catch(() => {});
}

function updateMusic() {
  el("mute").textContent = muted ? "Sound: off" : "Sound: on";
  if (!playerReady || !clicked) {
    return;
  }
  if (muted) {
    player.pauseVideo();
  } else {
    player.playVideo();
  }
}

function onYouTubeIframeAPIReady() {
  player = new YT.Player("music", {
    width: 200,
    height: 200,
    videoId: MUSIC_VIDEO_ID,
    playerVars: { loop: 1, playlist: MUSIC_VIDEO_ID, controls: 0 },
    events: {
      onReady: () => {
        playerReady = true;
        player.setVolume(40);
        updateMusic();
      },
    },
  });
}

document.addEventListener("click", () => {
  clicked = true;
  updateMusic();
});

for (const button of document.querySelectorAll(".button")) {
  button.addEventListener("click", playPop);
}

el("mute").onclick = () => {
  muted = !muted;
  localStorage.setItem("muted", muted ? "1" : "0");
  updateMusic();
};

el("start").onclick = () => {
  if (total === 0) {
    post("/sync", "Fetching liked songs from Spotify...");
  } else {
    post("/start", "Starting...");
  }
};
el("resume").onclick = () => post("/start", "Resuming...");
el("sync").onclick = () => post("/sync", "Fetching liked songs from Spotify...");

const youtubeScript = document.createElement("script");
youtubeScript.src = "https://www.youtube.com/iframe_api";
document.head.appendChild(youtubeScript);

updateMusic();
setInterval(refresh, 2000);
refresh();
